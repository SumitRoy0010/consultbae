# ConsultBae Data Merge + Automation + Audio Collection

## Overview

This project implements the five-part ConsultBae assignment:

- **Task 1:** merge three messy CSV systems into one auditable SQLite database
- **Task 2:** n8n duplicate-alert automation
- **Task 3:** Flask audio collection app with automatic metadata extraction
- **Task 4:** concrete data-quality report
- **Task 5:** production scaling notes for 5,000 workers

## Results on the supplied data

- Raw CSV rows: **105**
- Source records after structural cleanup: **103**
- Unique people after entity resolution: **60**
- Source records merged into existing people: **43**
- Data-quality findings: **79**

## Entity-resolution strategy

I deliberately did **not** merge people based on name alone.

1. Normalize email to lowercase and trim whitespace.
2. Normalize Indian phone numbers to a 10-digit local number.
3. Merge records when normalized email or normalized phone is an exact match.
4. Keep ambiguous same-name records separate.
5. Store every source row in `source_records` with its source, row number, raw JSON, match method and confidence.

This is intentionally conservative. For example, the files contain multiple people named **Arjun Mehta** with different identifiers. A name-only fuzzy match could create a false positive.

## Data issues found

The full machine-readable report is `data/data_issues_report.csv`.

Important findings include:

- A completely blank row in the gig-worker CSV.
- A column-shifted Isha Chopra row in the gig-worker CSV. The pipeline detects that an email is sitting in `worker_name` and reconstructs the six fields.
- The repaired Isha Chopra row duplicates another Isha Chopra record; normalized email merges those records.
- A repeated header row appears inside the CBNexus CSV and is dropped.
- Duplicate people exist inside the Naukri source, including repeated Rohit Verma and two Nikhil Chopra rows sharing the same phone.
- Phone formatting varies between local 10-digit, `91...`, and `+91-...` forms.
- Email casing varies between systems.
- City spelling varies (`Gurgaon/Gurugram`, `Bangalore/Bengaluru`, `New Delhi/Delhi`).
- Naukri CTC is mixed between LPA-like values (`4.2`) and annual-INR-looking values (`417964`). The pipeline standardizes to LPA using an explicit threshold while retaining the raw source JSON.
- Some Naukri application dates are in the future relative to the assignment date, 2026-08-20. They are flagged rather than silently rewritten.
- CBNexus verification values vary (`Y/Yes/N`); these are normalized when represented as booleans.
- Same-name/different-identifier records are kept separate instead of guessing.

## Database schema

### `people`

Canonical person record:

- person_id
- name
- normalized name
- email
- phone
- city
- experience
- current CTC in LPA
- combined skills

### `source_records`

Audit/provenance table:

- source record ID
- canonical person ID
- source system
- source row
- match method
- match confidence
- original raw JSON

### `audio_submissions`

Audio record:

- submission ID
- person ID
- name
- phone
- file path
- duration
- sample rate
- bitrate
- loudness
- rough quality estimate

## Run

Requirements:

- Python 3.10+
- FFmpeg and ffprobe on PATH

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python pipeline/ingest.py
```

Then:

```bash
python app/app.py
```

Open:

```text
http://localhost:5000
```

## Audio processing

`ffprobe` extracts:

- duration
- sample rate
- bitrate

FFmpeg's `loudnorm` filter is used to obtain a rough loudness value.

The quality/noise field is intentionally a **rough heuristic**, not a professional audio-quality metric. It is based on the loudness result and is labeled accordingly.

For the assignment, local file storage is sufficient. In production, audio should be stored in object storage rather than on the Flask server.

## n8n automation

Import:

```text
n8n/duplicate_alert_workflow.json
```

Flow:

```text
Webhook
   ↓
Normalize Person
   ↓
Check SQLite through Flask API
   ↓
Duplicate?
   ├── YES → Email alert
   └── NO  → Return response
```

The workflow is intentionally no-code/low-code: n8n owns the trigger, normalization step, branching and alert; the Flask API exposes the existing SQLite data.

For Docker n8n, the exported workflow uses:

```text
http://host.docker.internal:5000/api/check-person
```

Change the email recipient before the demo.

Test the Flask API directly:

```bash
curl -X POST http://localhost:5000/api/check-person \
  -H "Content-Type: application/json" \
  -d '{"name":"Tanvi Gupta","email":"tanvi.gupta31@example.com","phone":"919000000254"}'
```

An existing person returns `duplicate: true`.

## 5,000-worker production design

The assignment SQLite/local-upload version is deliberately small. Before a 5,000-worker weekend I would change:

- SQLite → PostgreSQL
- local disk → S3/R2/object storage
- synchronous FFmpeg → queue + worker processes
- add upload size/type validation
- add retryable/resumable uploads
- use idempotency keys and file hashes
- add database indexes and connection pooling
- add rate limiting
- add monitoring for upload failures, queue depth, processing latency and storage
- add lifecycle rules for object-storage cost control

Target architecture:

```text
Worker
  ↓
Object Storage
  ↓
Queue
  ↓
Audio Processing Workers
  ↓
PostgreSQL
```

This prevents slow audio processing from blocking web requests.

## Stuck log

Keep this section honest and update it with your actual experience while developing. Do not claim an issue happened if it did not.

### Entity matching

Hard decision: whether to use fuzzy name matching.

Decision: do not automatically merge on name alone. Exact normalized email/phone is safer because the files contain same-name people with different identifiers.

### Malformed CSV

Hard decision: whether to drop a structurally broken row.

Decision: inspect the row structure. The Isha Chopra row clearly had its fields shifted. It was reconstructed instead of discarded, then deduplicated using normalized email.

### Audio metadata

Hard decision: how to obtain metadata reliably across uploaded audio formats.

Decision: use ffprobe/FFmpeg on the server. This is more reliable for arbitrary files than depending only on browser-side metadata.

## Suggested Git history

Commit as you build rather than making one final commit:

```text
Initial project structure
Add CSV profiling
Add normalization
Implement entity matching
Add SQLite schema
Add data-quality report
Build audio upload page
Add FFmpeg metadata extraction
Add submissions view
Add n8n duplicate workflow
Add README and setup
```

## Six-minute demo plan

1. Show the three CSVs and architecture.
2. Run the merge pipeline and show counts.
3. Show 1–2 non-obvious matching decisions.
4. Trigger the n8n duplicate workflow and show the alert.
5. Upload an audio file.
6. Show duration, sample rate, bitrate and loudness.
7. Play the recording from the submissions list.
8. Explain the hardest matching decision and the 5,000-worker scaling design.
