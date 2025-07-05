# PDF to Audiobook Converter

A simple web application that converts uploaded PDF files into audiobooks (MP3 format) using Google's Gemini API for Text-to-Speech (TTS) conversion.

## Features

*   **PDF Upload**: Users can upload PDF files through a web interface.
*   **Text Extraction**: Extracts text content from the uploaded PDFs.
*   **Text-to-Speech**: Converts the extracted text into a WAV audio file using Google Gemini API (Gemini 2.5 Pro TTS).
*   **Audio Download**: Users can download the generated WAV audio file.
*   **Conversion History**: Displays a list of past conversions with their status (Uploaded, Processing, Completed, Failed).
*   **Simple UI**: A clean and straightforward user interface.

## Technologies Used

*   **Backend**: Python, Flask
*   **Database**: SQLite (via Flask-SQLAlchemy)
*   **PDF Processing**: `pdfplumber`
*   **Text-to-Speech**: Google Gemini API (`google-generativeai` Python SDK, specifically `gemini-2.5-pro-preview-tts` model)
*   **Frontend**: Basic HTML, CSS, and minimal JavaScript.

## Project Structure

```
.
├── app.py                  # Main Flask application, routes, DB models
├── templates/
│   └── index.html          # Main HTML template
├── static/
│   ├── style.css           # CSS styles
│   └── audio/              # Stores generated MP3 files (created automatically)
├── uploads/                # Stores uploaded PDF files (created automatically)
├── db.sqlite3              # SQLite database file (created automatically)
├── AGENTS.md               # Instructions for AI agents working on this project
├── README.md               # This file
└── requirements.txt        # (To be generated - lists Python dependencies)
```

## Setup and Installation

1.  **Clone the Repository (if applicable)**
    ```bash
    # git clone <repository-url>
    # cd <repository-directory>
    ```

2.  **Create and Activate a Virtual Environment** (Recommended)
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies**
    Create a `requirements.txt` file with the following content:
    ```
    Flask
    Flask-SQLAlchemy
    google-generativeai
    pdfplumber
    werkzeug
    ```
    Then install them:
    ```bash
    pip install -r requirements.txt
    ```
    *Alternatively, you can install them directly if you haven't created a `requirements.txt` yet: `pip install Flask Flask-SQLAlchemy google-generativeai pdfplumber werkzeug`*

4.  **Set up Google Gemini API Key**
    *   You need a Google Cloud Project with the Gemini API enabled.
    *   Obtain an API key. See: [Google AI Gemini API Documentation](https://ai.google.dev/gemini-api/docs/api-key)
    *   In `app.py`, locate the line `GOOGLE_API_KEY = "YOUR_API_KEY_HERE"` and replace `"YOUR_API_KEY_HERE"` with your actual API key.
        ```python
        # app.py
        GOOGLE_API_KEY = "AIzaSy..." # Replace with your key
        ```
    *   **Security Note**: For production, it is strongly recommended to use environment variables or a secrets manager for your API key instead of hardcoding it. The key provided in the initial request (`AIzaSyA5Nj2NC-q3yBoNHHnQ1WsoYOxQc-8Yq8s`) is used in the current `app.py`.

5.  **Run the Application**
    ```bash
    python app.py
    ```
    The application will start in debug mode by default and should be accessible at `http://127.0.0.1:5000/`.
    The necessary directories (`uploads/`, `static/audio/`) and the database file (`db.sqlite3`) will be created automatically if they don't exist.

## How to Use

1.  Open your web browser and navigate to `http://127.0.0.1:5000/`.
2.  Click "Choose PDF file", select a PDF, and click "Upload PDF".
3.  Once uploaded, the file will appear in the "Conversion History" table with the status "Uploaded".
4.  Click the "Convert to Audio" button next to the uploaded file.
5.  The status will change to "Processing". Wait for the conversion to complete. This may take some time depending on the PDF size and API response time.
    *   *Note: The conversion is synchronous in this version, so the page might appear to hang during processing.*
6.  Once completed, the status will change to "Completed", and a "Download Audio" button will appear.
7.  Click "Download Audio" to save the WAV file.
8.  If an error occurs, the status will change to "Failed", and an error message will be displayed.

## Limitations & Future Improvements

*   **Synchronous Conversion**: TTS conversion is currently synchronous, which can lead to request timeouts for large PDFs. This should be converted to an asynchronous process (e.g., using Celery) for a better user experience.
*   **Basic Progress Indication**: Upload progress is simulated. Conversion progress is not dynamically updated.
*   **Error Handling**: While basic error handling is in place, it could be made more granular.
*   **Text Extraction Quality**: `pdfplumber` is used, which works well for many PDFs, but complex layouts or scanned (image-based) PDFs will not be processed correctly (OCR would be needed for the latter).
*   **API Limits**: Large texts might exceed API limits. The current implementation does a simple truncation. A more robust solution would involve chunking the text.
*   **No User Accounts**: The application is currently single-user (all uploads and conversions are global).
*   **Styling**: The UI is intentionally simple. It could be enhanced with more advanced CSS or UI frameworks.

## Contributing

Feel free to fork this project, make improvements, and submit pull requests. If you encounter issues or have suggestions, please open an issue.

---

This `README.md` provides a good overview for users and developers. I've also included the content for a `requirements.txt` file within the README, which is good practice. I'll create that file next as it's a common and useful artifact.
