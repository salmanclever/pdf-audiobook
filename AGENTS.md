## Agent Instructions for PDF to Audiobook Converter

This document provides guidance for AI agents working on the "PDF to Audiobook Converter" project.

### Project Overview

The application is a Flask-based web tool that allows users to:
1. Upload PDF files.
2. Convert the text content of these PDFs into audio (MP3) using Google's Gemini API (specifically, the text-to-speech capabilities).
3. Download the generated audio files.
4. View a history of their conversions.

The project uses Python, Flask, Flask-SQLAlchemy (with SQLite), and the `google-generativeai` library. `pdfplumber` is used for PDF text extraction.

### Key Files and Structure

- `app.py`: Main Flask application file. Contains routes, database models, business logic for PDF processing, and Gemini API interaction.
- `templates/index.html`: Main HTML template for the user interface.
- `static/style.css`: CSS styles for the application.
- `static/audio/`: Directory where generated MP3 audio files are stored.
- `uploads/`: Directory where uploaded PDF files are stored.
- `db.sqlite3`: The SQLite database file (created automatically).
- `venv/`: Python virtual environment (if used locally).

### Development Guidelines

1.  **API Key Management**:
    *   The Google API Key for Gemini is currently hardcoded in `app.py` (`GOOGLE_API_KEY`).
    *   **IMPORTANT**: For any production or shared environment, this key MUST be moved to an environment variable or a secure secrets management system. Do not commit the actual key if this were a public repository. The current key is a placeholder/example.
    *   If you need to test TTS functionality, ensure you have a valid Gemini API key with TTS capabilities enabled.

2.  **Dependencies**:
    *   Key Python libraries: `Flask`, `Flask-SQLAlchemy`, `google-generativeai`, `pdfplumber`.
    *   These are installed via `pip install -r requirements.txt` (if a `requirements.txt` file were generated, which is good practice). For now, they were installed directly.

3.  **Running the Application**:
    *   Ensure all dependencies are installed.
    *   Run `python app.py`. The application will start in debug mode by default.
    *   The database (`db.sqlite3`) and necessary directories (`uploads/`, `static/audio/`) are created automatically if they don't exist when `app.py` is run.

4.  **Code Style and Conventions**:
    *   Follow standard Python (PEP 8) and Flask conventions.
    *   Keep code modular and readable. Add comments where necessary.
    *   User-facing messages should be clear and helpful. Use Flask's `flash()` mechanism.

5.  **Error Handling**:
    *   Implement robust error handling, especially for file operations, API calls, and database interactions.
    *   Update the `status` field in the `Conversion` model appropriately (`Uploaded`, `Processing`, `Completed`, `Failed`).
    *   Provide informative feedback to the user via flashed messages. Log detailed errors on the server.

6.  **Gemini API Usage**:
    *   The application uses the `models/text-to-speech` model via the `google-generativeai` library.
    *   Refer to the official Google AI Gemini API documentation for details on TTS capabilities, supported voices, limits, and best practices:
        *   Gemini models: [https://ai.google.dev/gemini-api/docs/models](https://ai.google.dev/gemini-api/docs/models) (especially the section on Gemini 2.5 Pro TTS)
        *   Speech Generation guide: [https://ai.google.dev/gemini-api/docs/speech-generation](https://ai.google.dev/gemini-api/docs/speech-generation)
    *   Be mindful of API quotas and potential costs.
    *   The current implementation has a basic text truncation for very long texts. For production, a more sophisticated chunking mechanism for large PDFs would be necessary to handle API limits for input text length.

7.  **UI/UX**:
    *   The UI aims to be "modern and beautiful" but also "as simple as it can be."
    *   Changes should maintain this balance.
    *   Progress bars are included in the HTML. The upload progress bar is simulated. The conversion progress bar is currently static. Implementing true, dynamic progress for conversions would require changing the synchronous conversion process to an asynchronous one (e.g., using Celery or background threads and polling/WebSockets).

8.  **Database**:
    *   The `Conversion` model in `app.py` defines the schema.
    *   Migrations are not currently set up. For schema changes in a development lifecycle, you might need to delete and recreate `db.sqlite3` or implement a migration tool like Alembic.

### Future Enhancements Considerations (If Tasked)

*   **Asynchronous Processing**: Convert the TTS process to be asynchronous to prevent HTTP timeouts and allow for real-time progress updates.
*   **Real Progress Bars**: Implement actual progress reporting for both upload and conversion.
*   **Advanced PDF Parsing**: Handle more complex PDF layouts, images, or scanned documents (OCR might be needed, which is outside current scope).
*   **Voice Selection**: Allow users to choose different TTS voices.
*   **User Accounts**: If multiple users are expected.
*   **Deployment**: Containerization (Docker), proper web server (Gunicorn/Nginx).

Remember to always test changes thoroughly. Good luck!
