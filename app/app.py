from pathlib import Path
import os, re, sqlite3, subprocess, json
from flask import Flask, render_template, request, redirect, url_for, flash

BASE=Path(__file__).resolve().parents[1]
DB=BASE/"database"/"consultbae.db"
UPLOADS=BASE/"uploads"
UPLOADS.mkdir(exist_ok=True)
app=Flask(__name__)
app.secret_key=os.getenv("FLASK_SECRET","dev-secret")

def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def normalize_phone(v):
    s=re.sub(r"\D","",v or "")
    if len(s)==12 and s.startswith("91"): s=s[2:]
    return s

def find_or_create_person(name, phone):
    phone_n=normalize_phone(phone)
    c=db()
    row=c.execute("SELECT * FROM people WHERE phone=?",(phone_n,)).fetchone() if phone_n else None
    if row: c.close(); return row["person_id"]
    cur=c.execute("INSERT INTO people(name,name_norm,phone) VALUES(?,?,?)",
                  (name.strip()," ".join(name.lower().split()),phone_n))
    c.commit(); pid=cur.lastrowid; c.close(); return pid

def ffprobe(path):
    cmd=["ffprobe","-v","error","-show_entries",
         "format=duration:format_tags=encoder",
         "-show_entries","stream=sample_rate,bit_rate,codec_name",
         "-of","json",str(path)]
    data=json.loads(subprocess.check_output(cmd,stderr=subprocess.STDOUT))
    stream=(data.get("streams") or [{}])[0]
    duration=float((data.get("format") or {}).get("duration") or 0)
    sample_rate=int(stream.get("sample_rate") or 0)
    bitrate=stream.get("bit_rate")
    bitrate_kbps=float(bitrate)/1000 if bitrate else None
    return duration,sample_rate,bitrate_kbps

def loudness(path):
    cmd=["ffmpeg","-hide_banner","-i",str(path),"-af","loudnorm=print_format=json",
         "-f","null","-"]
    p=subprocess.run(cmd,text=True,capture_output=True)
    text=p.stderr
    start=text.rfind("{"); end=text.rfind("}")
    if start!=-1 and end>start:
        try: return float(json.loads(text[start:end+1]).get("input_i"))
        except Exception: pass
    return None

@app.route("/",methods=["GET","POST"])
def index():
    if request.method=="POST":
        name=request.form.get("name","").strip()
        phone=request.form.get("phone","").strip()
        file=request.files.get("audio")
        if not name or not phone or not file or not file.filename:
            flash("Name, phone and an audio file are required.")
            return redirect(url_for("index"))
        safe=re.sub(r"[^A-Za-z0-9_.-]","_",file.filename)
        path=UPLOADS/safe
        file.save(path)
        try:
            duration,sample_rate,bitrate=ffprobe(path)
            loud=loudness(path)
            # Rough heuristic only: loudness near typical speech range is better than extreme levels.
            quality="Good" if loud is not None and -25 <= loud <= -12 else ("Fair" if loud is not None else "Unknown")
            pid=find_or_create_person(name,phone)
            c=db()
            c.execute("""INSERT INTO audio_submissions
                (person_id,name,phone,file_path,duration_seconds,sample_rate_hz,bitrate_kbps,loudness_db,noise_estimate)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (pid,name,normalize_phone(phone),str(path.relative_to(BASE)),duration,sample_rate,bitrate,loud,quality))
            c.commit(); c.close()
            flash("Audio submitted successfully.")
        except Exception as e:
            flash(f"Audio processing failed: {e}")
        return redirect(url_for("submissions"))
    return render_template("index.html")

@app.route("/api/check-person", methods=["POST"])
def api_check_person():
    p=request.get_json(force=True)
    email=str(p.get("email","")).strip().lower()
    phone=normalize_phone(str(p.get("phone","")))
    c=db()
    row=None; reason=None
    if email:
        row=c.execute("SELECT person_id,name FROM people WHERE lower(email)=?",(email,)).fetchone()
        if row: reason="email"
    if not row and phone:
        row=c.execute("SELECT person_id,name FROM people WHERE phone=?",(phone,)).fetchone()
        if row: reason="phone"
    c.close()
    return {"duplicate": bool(row), "match_reason": reason,
            "person_id": row["person_id"] if row else None,
            "matched_name": row["name"] if row else None}

@app.route("/submissions")
def submissions():
    c=db()
    rows=c.execute("""SELECT a.*, p.name AS person_name
                      FROM audio_submissions a JOIN people p ON p.person_id=a.person_id
                      ORDER BY a.submission_id DESC""").fetchall()
    c.close()
    return render_template("submissions.html",rows=rows)

@app.route("/audio/<int:submission_id>")
def audio(submission_id):
    from flask import send_file
    c=db(); row=c.execute("SELECT file_path FROM audio_submissions WHERE submission_id=?",(submission_id,)).fetchone(); c.close()
    if not row: return "Not found",404
    return send_file(BASE/row["file_path"])

if __name__=="__main__":
    app.run(debug=True,host="0.0.0.0",port=5000)
