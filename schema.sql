DROP TABLE IF EXISTS conversions;

CREATE TABLE conversions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_filename TEXT NOT NULL,
    pdf_filepath TEXT NOT NULL,
    audio_filename TEXT, -- Name of the audio file
    audio_filepath TEXT, -- Full path to the audio file
    status TEXT NOT NULL, -- e.g., pending, processing, completed, error
    progress INTEGER DEFAULT 0, -- For more granular progress if implemented later
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
