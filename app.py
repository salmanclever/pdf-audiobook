from flask import Flask, render_template, request, redirect, url_for, send_from_directory, g, jsonify, flash
import os
import sqlite3
from PyPDF2 import PdfReader
from gtts import gTTS
import datetime # Added for timestamping

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
AUDIO_FOLDER = 'audio'
DATABASE = 'database.db'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['AUDIO_FOLDER'] = AUDIO_FOLDER

# Ensure upload and audio directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True)

def get_db():
    # Using Flask's g to store the database connection
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row # Allows accessing columns by name
    return g.db

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db_command():
    """Initializes the database."""
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()
    print("Initialized the database.")

# Command to initialize DB: flask init-db
@app.cli.command('init-db')
def init_db_cli_command():
    init_db_command()

@app.route('/')
def index():
    if not os.path.exists(DATABASE):
        with app.app_context(): # Ensure app context for init_db_command
            init_db_command()
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_pdf():
    if 'pdfFile' not in request.files:
        flash("No file part in the request.", "error")
        return redirect(url_for('index'))

    file = request.files['pdfFile']
    if file.filename == '':
        flash("No file selected for upload.", "warning")
        return redirect(url_for('index'))

    if file and file.filename.lower().endswith('.pdf'):
        # Sanitize filename to prevent directory traversal or other issues
        # For simplicity, Werkzeug's secure_filename is good.
        from werkzeug.utils import secure_filename
        original_filename = file.filename
        safe_filename = secure_filename(original_filename)
        if not safe_filename: # if filename was, e.g., ../../foo.pdf or just ".pdf"
            safe_filename = f"upload_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"

        pdf_filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)

        # Avoid overwriting existing files by appending a number if necessary
        counter = 1
        temp_filepath = pdf_filepath
        while os.path.exists(temp_filepath):
            name, ext = os.path.splitext(pdf_filepath)
            temp_filepath = f"{name}_{counter}{ext}"
            counter += 1
        pdf_filepath = temp_filepath
        # Update safe_filename if it was changed
        safe_filename = os.path.basename(pdf_filepath)

        file.save(pdf_filepath)

        # Attempt to extract text immediately to see if PDF is valid before DB insert
        extracted_text, error_message = extract_text_from_pdf(pdf_filepath)

        if error_message:
            flash(f"Error processing PDF '{original_filename}': {error_message}", "error")
            print(f"Error extracting text from {original_filename}: {error_message}")
            if os.path.exists(pdf_filepath): # Clean up uploaded file if text extraction failed
                os.remove(pdf_filepath)
            return redirect(url_for('index'))

        db = get_db()
        cursor = db.cursor()
        try:
            # Update status to 'processing_text' or similar if text extraction is lengthy
            # For now, we assume it's quick enough to go to 'pending_audio'
            cursor.execute(
                "INSERT INTO conversions (original_filename, pdf_filepath, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (original_filename, pdf_filepath, 'processing', datetime.datetime.now(), datetime.datetime.now()) # Status 'processing'
            )
            db.commit()
            conversion_id = cursor.lastrowid

            # Simulate further processing or pass text to TTS (next step)
            print(f"File {original_filename} (saved as {safe_filename}) uploaded. DB ID: {conversion_id}. Text extracted ({len(extracted_text)} chars).")
            flash(f"'{original_filename}' uploaded and text extracted. Ready for audio conversion.", "success")

            # Store extracted text or pass it directly to next step
            # For simplicity, we'll re-extract or pass ID for now.
            # In a more robust app, you might save text to a temp file or DB if large.

            # This is where we will trigger the TTS conversion in the next step
            audio_filename, tts_error = process_tts_conversion(conversion_id, extracted_text, original_filename)

            if tts_error:
                flash(f"TTS conversion failed for '{original_filename}': {tts_error}", "error")
                # Update DB status to error
                cursor.execute("UPDATE conversions SET status = ?, updated_at = ? WHERE id = ?",
                               ('error', datetime.datetime.now(), conversion_id))
            else:
                flash(f"Audiobook for '{original_filename}' created successfully!", "success")
                # Update DB with audio file info and status 'completed'
                cursor.execute("UPDATE conversions SET status = ?, audio_filename = ?, audio_filepath = ?, updated_at = ? WHERE id = ?",
                               ('completed', audio_filename, os.path.join(app.config['AUDIO_FOLDER'], audio_filename), datetime.datetime.now(), conversion_id))
            db.commit()

        except sqlite3.Error as e:
            db.rollback()
            flash(f"Database error: {e}", "error")
            print(f"Database error on upload: {e}")
            # Potentially delete the orphaned uploaded file if DB insert fails
            if os.path.exists(pdf_filepath):
                os.remove(pdf_filepath)
            return redirect(url_for('index'))

        return redirect(url_for('index', conversion_id=conversion_id)) # Pass ID for potential immediate feedback
    else:
        flash("Invalid file type. Please upload a PDF file.", "error")
        return redirect(url_for('index'))

def extract_text_from_pdf(pdf_path):
    """
    Extracts text from a given PDF file.
    Returns a tuple (extracted_text, error_message).
    error_message is None if successful, otherwise contains an error description.
    """
    try:
        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)
            text = []
            if reader.is_encrypted:
                # Attempt to decrypt with an empty password, common for some PDFs.
                # PyPDF2 might require specific handling for password-protected PDFs.
                try:
                    reader.decrypt('')
                except Exception as decrypt_err:
                    print(f"Could not decrypt PDF {pdf_path}: {decrypt_err}")
                    return "", f"PDF is encrypted and could not be decrypted with a default password. ({decrypt_err})"

            if not reader.pages:
                 return "", "PDF has no pages."

            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)

            full_text = "\n".join(text)
            if not full_text.strip():
                return "", "No text could be extracted from the PDF (it might be an image-based PDF)."
            return full_text, None
    except FileNotFoundError:
        return "", f"PDF file not found at {pdf_path}."
    except Exception as e:
        # Broad exception to catch various PyPDF2 issues (e.g., malformed PDFs)
        print(f"Error reading PDF {pdf_path}: {e}")
        return "", f"Could not read or parse PDF file. It might be corrupted or an unsupported format. ({e})"

def process_tts_conversion(conversion_id, text_content, original_pdf_filename):
    """
    Converts text content to an audio file using gTTS.
    Updates the database entry for the conversion.
    Returns (audio_filename, error_message). error_message is None on success.
    """
    if not text_content.strip():
        print(f"Conversion ID {conversion_id}: No text content provided for TTS.")
        return None, "No text content found in the PDF to convert."

    try:
        # Sanitize original_pdf_filename to create a base for the audio filename
        base_filename = os.path.splitext(original_pdf_filename)[0]
        from werkzeug.utils import secure_filename
        safe_base_filename = secure_filename(base_filename)
        if not safe_base_filename: # Handle cases where secure_filename returns empty
            safe_base_filename = f"audio_{conversion_id}"

        audio_filename = f"{safe_base_filename}.mp3"
        audio_filepath = os.path.join(app.config['AUDIO_FOLDER'], audio_filename)

        # Ensure audio filename is unique
        counter = 1
        temp_audio_filepath = audio_filepath
        temp_audio_filename = audio_filename
        while os.path.exists(temp_audio_filepath):
            temp_audio_filename = f"{safe_base_filename}_{counter}.mp3"
            temp_audio_filepath = os.path.join(app.config['AUDIO_FOLDER'], temp_audio_filename)
            counter += 1
        audio_filename = temp_audio_filename
        audio_filepath = temp_audio_filepath

        print(f"Conversion ID {conversion_id}: Starting TTS conversion for '{original_pdf_filename}' to '{audio_filename}'. Text length: {len(text_content)}")

        # Perform TTS conversion
        # Consider chunking for very long texts if gTTS has limitations or for progress
        tts = gTTS(text=text_content, lang='en', slow=False)
        tts.save(audio_filepath)

        print(f"Conversion ID {conversion_id}: TTS conversion successful. Audio saved to '{audio_filepath}'")
        return audio_filename, None

    except Exception as e:
        print(f"Conversion ID {conversion_id}: Error during TTS conversion for '{original_pdf_filename}': {e}")
        # Attempt to clean up partially created audio file if error occurs
        if 'audio_filepath' in locals() and os.path.exists(audio_filepath):
            try:
                os.remove(audio_filepath)
            except Exception as e_remove:
                print(f"Conversion ID {conversion_id}: Could not remove partial audio file '{audio_filepath}': {e_remove}")
        return None, f"Failed to convert text to speech. ({e})"

@app.route('/download_audio/<path:filename>')
def download_audio(filename):
    # Sanitize filename again, although it should be safe from DB
    from werkzeug.utils import secure_filename
    safe_filename = secure_filename(filename)
    if not safe_filename or safe_filename != filename: # Basic check
        flash("Invalid filename for download.", "error")
        return redirect(url_for('index'))

    try:
        return send_from_directory(app.config['AUDIO_FOLDER'], safe_filename, as_attachment=True)
    except FileNotFoundError:
        flash("Audio file not found. It might have been deleted or an error occurred.", "error")
        return redirect(url_for('index'))

# Endpoint to get history data for the frontend
@app.route('/history')
def get_history():
    db = get_db()
    cursor = db.execute("SELECT id, original_filename, status, audio_filename, created_at FROM conversions ORDER BY created_at DESC")
    history_items = cursor.fetchall()
    return jsonify([dict(row) for row in history_items])


if __name__ == '__main__':
    app.run(debug=True)
