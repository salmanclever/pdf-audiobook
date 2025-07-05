from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import datetime
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['GENERATED_AUDIO_FOLDER'] = os.path.join('static', 'audio') # Store generated audio in static for easy download
from flask import render_template, request, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename
import os
import pdfplumber
import google.generativeai as genai

app.secret_key = 'supersecretkey' # Needed for flash messages

# IMPORTANT: Replace with your actual API key. Consider environment variables for production.
GOOGLE_API_KEY = "AIzaSyA5Nj2NC-q3yBoNHHnQ1WsoYOxQc-8Yq8s"
if GOOGLE_API_KEY == "YOUR_API_KEY_HERE" or not GOOGLE_API_KEY:
    print("WARNING: Google API Key not set. TTS functionality will not work.")
    # Potentially raise an error or disable TTS features if key is missing
else:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        print("Google Generative AI configured successfully.")
    except Exception as e:
        print(f"Error configuring Google Generative AI: {e}")


db = SQLAlchemy(app)

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    except Exception as e:
        print(f"Error extracting text from PDF {pdf_path}: {e}")
        return None

class Conversion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pdf_filename = db.Column(db.String(100), nullable=False)
    audio_filename = db.Column(db.String(100), nullable=True)
    upload_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    status = db.Column(db.String(50), default='Uploaded') # e.g., Uploaded, Processing, Completed, Failed
    pdf_path = db.Column(db.String(200), nullable=False)
    audio_path = db.Column(db.String(200), nullable=True)

    def __repr__(self):
        return f'<Conversion {self.id} - {self.pdf_filename}>'

# Create static/audio directory if it doesn't exist
if not os.path.exists(app.config['GENERATED_AUDIO_FOLDER']):
    os.makedirs(app.config['GENERATED_AUDIO_FOLDER'])
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            # Check if a file with the same name already exists in uploads
            if os.path.exists(pdf_path):
                flash(f'File {filename} already uploaded. Choose a different file or rename.', 'warning')
                return redirect(request.url)

            file.save(pdf_path)

            new_conversion = Conversion(
                pdf_filename=filename,
                pdf_path=pdf_path,
                status='Uploaded'
            )
            db.session.add(new_conversion)
            db.session.commit()
            flash(f'File {filename} uploaded successfully! Ready to convert.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid file type. Please upload a PDF.', 'error')
            return redirect(request.url)

    conversions = Conversion.query.order_by(Conversion.upload_date.desc()).all()
    return render_template('index.html', conversions=conversions)

@app.route('/convert/<int:conversion_id>', methods=['POST'])
def start_conversion(conversion_id):
    conversion = Conversion.query.get_or_404(conversion_id)
    if not conversion:
        flash('Conversion record not found.', 'error')
        return redirect(url_for('index'))

    if conversion.status == 'Processing':
        flash('This file is already being processed.', 'info')
        return redirect(url_for('index'))

    if conversion.status == 'Completed':
        flash('This file has already been converted.', 'info')
        return redirect(url_for('index'))

    conversion.status = 'Processing'
    db.session.commit()
    flash(f'Starting conversion for {conversion.pdf_filename}...', 'info')
    # Redirect to allow the flash message to show and avoid POST issues on refresh
    # The actual processing will happen "in the background" for this simple version
    # For long tasks, a task queue (Celery) would be better.
    # Here we will do it synchronously for simplicity, but it might time out for large PDFs.

    try:
        pdf_text = extract_text_from_pdf(conversion.pdf_path)
        if not pdf_text:
            conversion.status = 'Failed'
            db.session.commit()
            flash(f'Failed to extract text from {conversion.pdf_filename}.', 'error')
            return redirect(url_for('index'))

        # Truncate text if too long for a single API call (Gemini might have limits)
        # This is a simple truncation, more sophisticated chunking might be needed.
        max_text_length = 48000 # Example limit, check Gemini docs for actual limits
        if len(pdf_text) > max_text_length:
            pdf_text = pdf_text[:max_text_length]
            flash(f'Text was truncated due to length for {conversion.pdf_filename}.', 'warning')

        if not GOOGLE_API_KEY or GOOGLE_API_KEY == "YOUR_API_KEY_HERE":
             raise Exception("Google API Key not configured.")

        # Check if model is available (example, might need specific model listing)
        # For now, directly try to use the model
        # tts_model_name = "models/tts-001" # Example from some docs, might need to be gemini-2.5-pro specific if it has TTS
        # The documentation https://ai.google.dev/gemini-api/docs/speech-generation uses 'models/text-to-speech'
        tts_model_name = 'models/text-to-speech'

        print(f"Using TTS model: {tts_model_name}")
        model = genai.GenerativeModel(model_name=tts_model_name)

        # Synthesize speech
        # Voices can be listed using genai.list_models() and filtering for TTS, then checking supported voices.
        # For simplicity, not selecting a specific voice, letting API use default or a common one.
        response = model.generate_content(
            pdf_text,
            generation_config=genai.types.GenerationConfig(
                candidate_count=1 # For TTS, usually 1 candidate
            ),
            # The speech generation specific parameters are typically passed differently
            # Based on https://ai.google.dev/gemini-api/docs/speech-generation
            # it seems the `generate_content` might not be the one for direct TTS.
            # Let's try to find the correct method or assume `generate_content` can handle it
            # if the model is a TTS model.
            # The documentation shows: `audio_bytes = model.synthesize_speech(text=text, voice="VoiceName", audio_format="MP3")`
            # This implies `synthesize_speech` is a method on the model object.
        )

        # The new Speech Generation guide (June 2024) for Gemini API suggests the following:
        # client = TextToSpeechClient() -> this is from google.cloud.texttospeech
        # The `google-generativeai` library might have a different approach for Gemini 2.5 Pro's own TTS.
        # The link provided (https://ai.google.dev/gemini-api/docs/models#gemini-2.5-pro-preview-tts)
        # implies Gemini 2.5 Pro has TTS capabilities.
        # The other link (https://ai.google.dev/gemini-api/docs/speech-generation) is more general for Google AI Speech.

        # Let's assume `gemini-2.5-pro` with TTS is accessed via a specific model name
        # and the `generate_content` call structure might need adjustment or a different method.
        # The documentation for `google-generativeai` library for speech is:
        # https://ai.google.dev/gemini-api/docs/speech-generation
        # It shows:
        # model = genai.GenerativeModel('models/text-to-speech')
        # response = model.synthesize_speech(text=TEXT, voice='aura-asteria-en', audio_format='MP3') # Example voice
        # audio_data = response.audio_data

        # Re-checking the provided link: https://ai.google.dev/gemini-api/docs/models#gemini-2.5-pro-preview-tts
        # "Gemini 2.5 Pro also offers state-of-the-art Text-to-Speech (TTS) and Audio Understanding capabilities,
        # currently in Preview. See the Speech guide to learn more." This links to the general speech guide.

        # Using gemini-2.5-pro-preview-tts as per user feedback and example
        tts_model_name = 'gemini-2.5-pro-preview-tts'
        print(f"Using TTS model: {tts_model_name}")

        # Ensure genai.types is available if not already imported at top level
        # from google.generativeai import types as genai_types (if needed for clarity)
        # For now, assuming genai.types is accessible

        model = genai.GenerativeModel(model_name=tts_model_name)

        # Constructing the request based on the user-provided example
        # For single speaker, we don't need multi_speaker_voice_config
        # We'll try with a basic voice config or a single prebuilt voice.
        # The API might require a specific voice to be named. Let's try 'aura-asteria-en' or a generic one.
        # The example showed specific named voices like 'Kore'.
        # Let's try a simpler config first. If it fails, we'll use a specific prebuilt voice.

        # Attempt 1: Minimal config (might use API default voice)
        # speech_config = genai.types.SpeechConfig(
        #     # Potentially add voice_config here if needed
        # )

        # Attempt 2: Using a prebuilt voice (e.g., 'aura-echo-en' or 'Kore' from example if generic doesn't work)
        # The example uses `types.PrebuiltVoiceConfig(voice_name='Kore')`
        # Let's use a single speaker config with one of these.
        # The Gemini API docs for speech generation mention voices like 'aura-asteria-en', 'aura-luna-en' etc.
        # Let's try 'aura-asteria-en' as it's often listed.

        # According to the Gemini API documentation for speech generation:
        # https://ai.google.dev/gemini-api/docs/speech-generation#supported_voices
        # Voices are like 'aura-asteria-en'.
        # The structure from the user's example:
        # speech_config=types.SpeechConfig(
        #  multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
        #    speaker_voice_configs=[ types.SpeakerVoiceConfig( speaker='Joe', voice_config=types.VoiceConfig( prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name='Kore'))) ]
        #  )
        # )
        # This is for multi-speaker. For single text, it might be simpler.
        # The `generate_content` method with `response_modalities=["AUDIO"]` might infer single speaker.
        # Let's try without detailed speech_config first, then add a simple one if needed.

        generation_config_payload = genai.types.GenerationConfig(
            response_modalities=["AUDIO"],
            # speech_config could be added here if needed:
            # speech_config=genai.types.SpeechConfig(
            #    voice_config=genai.types.VoiceConfig(
            #        prebuilt_voice_config=genai.types.PrebuiltVoiceConfig(
            #            voice_name='aura-asteria-en' # Example voice
            #        )
            #    )
            # )
        )

        # If the above doesn't work, try a more explicit voice from example like 'Kore' or 'Puck'
        # speech_config=genai.types.SpeechConfig(
        #     voice_config=genai.types.VoiceConfig(
        #         prebuilt_voice_config=genai.types.PrebuiltVoiceConfig(voice_name='Kore')
        #     )
        # )

        print(f"Attempting TTS for text: {pdf_text[:100]}...") # Log first 100 chars

        tts_response = model.generate_content(
            contents=pdf_text, # The prompt/text to convert
            generation_config=generation_config_payload
        )

        # Extract audio data - example: response.candidates[0].content.parts[0].inline_data.data
        if not tts_response.candidates or not tts_response.candidates[0].content.parts:
            raise Exception("TTS API response structure unexpected or missing audio data.")

        audio_part = None
        for part in tts_response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("audio/"):
                audio_part = part
                break

        if not audio_part:
            raise Exception("No audio data found in TTS response parts.")

        audio_data = audio_part.inline_data.data
        # The example saves as WAV. Let's assume WAV output.
        # Mime type from part.inline_data.mime_type will likely be 'audio/wav'
        print(f"Received audio data, mime_type: {audio_part.inline_data.mime_type}")


        if not audio_data:
            raise Exception("TTS API returned no audio data.")

        # Output is WAV based on example and likely from gemini-2.5-pro-preview-tts
        audio_filename = os.path.splitext(conversion.pdf_filename)[0] + ".wav"
        audio_path = os.path.join(app.config['GENERATED_AUDIO_FOLDER'], audio_filename)

        with open(audio_path, 'wb') as audio_file:
            audio_file.write(audio_data)
        print(f"Audio file saved to: {audio_path}")

        conversion.audio_filename = audio_filename
        conversion.audio_path = audio_path
        conversion.status = 'Completed'
        db.session.commit()
        flash(f'Successfully converted {conversion.pdf_filename} to audio!', 'success')

    except Exception as e:
        conversion.status = 'Failed'
        db.session.commit()
        # Log the full error for debugging
        app.logger.error(f"Error during conversion of {conversion.pdf_filename}: {e}", exc_info=True)
        flash(f'Error converting {conversion.pdf_filename}: {str(e)}', 'error')

    return redirect(url_for('index'))

@app.route('/audio/<path:filename>')
def download_audio(filename):
    # Use send_from_directory for security and proper handling of file serving
    audio_dir = os.path.join(app.root_path, app.config['GENERATED_AUDIO_FOLDER'])
    return send_from_directory(
        audio_dir,
        filename,
        as_attachment=True # This ensures the browser prompts for download
    )

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
