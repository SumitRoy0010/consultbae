CREATE TABLE people (
    person_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    name_norm TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    city TEXT,
    experience_years REAL,
    current_ctc_lpa REAL,
    skills TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE source_records (
    source_record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL,
    source_system TEXT NOT NULL,
    source_row INTEGER NOT NULL,
    match_method TEXT NOT NULL,
    match_confidence REAL NOT NULL,
    raw_json TEXT NOT NULL,
    FOREIGN KEY(person_id) REFERENCES people(person_id)
);
CREATE TABLE audio_submissions (
    submission_id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    file_path TEXT NOT NULL,
    duration_seconds REAL,
    sample_rate_hz INTEGER,
    bitrate_kbps REAL,
    loudness_db REAL,
    noise_estimate TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(person_id) REFERENCES people(person_id)
);
CREATE INDEX idx_people_email ON people(email);
CREATE INDEX idx_people_phone ON people(phone);
CREATE INDEX idx_people_name_norm ON people(name_norm);
CREATE INDEX idx_source_person ON source_records(person_id);
