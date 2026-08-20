import argparse, json, re, sqlite3, unicodedata
from pathlib import Path
from datetime import datetime
import pandas as pd

TODAY = datetime(2026, 8, 20).date()

def norm_name(x):
    x = unicodedata.normalize("NFKD", str(x).strip().lower()).encode("ascii","ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", x)).strip()

def norm_email(x):
    x = str(x).strip().lower()
    return x if re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", x) else ""

def norm_phone(x):
    s = re.sub(r"\D", "", str(x))
    if len(s) == 12 and s.startswith("91"): s = s[2:]
    return s if len(s) == 10 else ""

def norm_city(x):
    x = str(x).strip().lower()
    return {"gurgaon":"gurugram","gurugram":"gurugram",
            "new delhi":"delhi","bangalore":"bengaluru",
            "bengaluru":"bengaluru"}.get(x, x)

def parse_date(x):
    for fmt in ("%d-%m-%Y","%d/%m/%Y","%d %b %Y","%Y-%m-%d"):
        try: return datetime.strptime(str(x).strip(), fmt).date().isoformat()
        except ValueError: pass
    return ""

def parse_ctc_lpa(x):
    if str(x).strip()=="": return None
    v=float(x)
    return v if v < 100 else v/100000

def load_records(data_dir):
    # This is intentionally kept readable: each source is mapped into one common record shape.
    records=[]; issues=[]
    s1=pd.read_csv(data_dir/"source1_naukri_applicants.csv").fillna("")
    s2=pd.read_csv(data_dir/"source2_gig_workers.csv").fillna("")
    s3=pd.read_csv(data_dir/"source3_cbnexus_contacts.csv").fillna("")

    for idx,r in s1.iterrows():
        records.append({"source":"naukri","source_row":idx+2,"name":str(r["Full Name"]).strip(),
                        "email":str(r["Email"]).strip(),"phone":str(r["Phone"]).strip(),
                        "city":str(r["City"]).strip(),
                        "experience_years":float(r["Experience (Years)"]) if str(r["Experience (Years)"]).strip() else None,
                        "current_ctc_lpa":parse_ctc_lpa(r["Current CTC"]),
                        "applied_date":parse_date(r["Applied Date"]),
                        "skills":str(r["Skills"]).strip(),"raw":r.to_dict()})

    for idx,r in s2.iterrows():
        if all(str(v).strip()=="" for v in r):
            issues.append(["gig_workers",idx+2,"blank_row","dropped","Completely blank row"]); continue
        if "@" in str(r["worker_name"]) and "@" not in str(r["email_id"]):
            r=pd.Series({"email_id":r["worker_name"],"worker_name":r["rate"],
                         "rate":r["location"],"location":r["status"],
                         "status":r["skill_tags"],"skill_tags":r["email_id"]})
            issues.append(["gig_workers",idx+2,"column_shift","repaired","Reconstructed shifted Isha Chopra row."])
        records.append({"source":"gig_workers","source_row":idx+2,"name":str(r["worker_name"]).strip(),
                        "email":str(r["email_id"]).strip(),"phone":"","city":str(r["location"]).strip(),
                        "experience_years":None,"current_ctc_lpa":None,"applied_date":"",
                        "skills":str(r["skill_tags"]).strip(),"rate":str(r["rate"]).strip(),
                        "status":str(r["status"]).strip().lower(),"raw":r.to_dict()})

    for idx,r in s3.iterrows():
        if norm_name(r["Name"])=="name" and norm_name(r["Phone Number"])=="phone number":
            issues.append(["cbnexus",idx+2,"repeated_header","dropped","Header repeated inside data."]); continue
        records.append({"source":"cbnexus","source_row":idx+2,"name":str(r["Name"]).strip(),
                        "email":"","phone":str(r["Phone Number"]).strip(),"city":str(r["City"]).strip(),
                        "experience_years":None,"current_ctc_lpa":None,"applied_date":"",
                        "skills":"","verified":str(r["Verified"]).strip().lower() in ("y","yes","true","1"),
                        "projects_completed":int(float(r["Projects Completed"])) if str(r["Projects Completed"]).strip().isdigit() else None,
                        "raw":r.to_dict()})

    for r in records:
        r["name_norm"]=norm_name(r["name"]); r["email_norm"]=norm_email(r["email"])
        r["phone_norm"]=norm_phone(r["phone"]); r["city_norm"]=norm_city(r["city"])
        if r["applied_date"] and datetime.fromisoformat(r["applied_date"]).date()>TODAY:
            issues.append([r["source"],r["source_row"],"future_date","flagged",
                           f"Applied Date {r['applied_date']} is after {TODAY}."])
        if r["source"]=="naukri":
            raw=str(r["raw"].get("Current CTC","")).strip()
            if raw:
                unit="LPA" if float(raw)<100 else "annual INR"
                issues.append(["naukri",r["source_row"],"ctc_unit","normalized",
                               f"CTC {raw} interpreted as {unit}; stored in LPA."])

    # Flag same-name records with conflicting identifiers; do not fuzzy-merge them.
    by_name={}
    for i,r in enumerate(records):
        by_name.setdefault(r["name_norm"],[]).append(i)
    for name,members in by_name.items():
        emails={records[i]["email_norm"] for i in members if records[i]["email_norm"]}
        phones={records[i]["phone_norm"] for i in members if records[i]["phone_norm"]}
        if len(members)>1 and (len(emails)>1 or len(phones)>1):
            issues.append(["cross-source","","same_name_conflict","kept_separate",
                           f"{name!r} appears with different identifiers; name alone was not used for merging."])

    return records,issues

def build_db(records, db_path):
    parent=list(range(len(records)))
    def find(a):
        while parent[a]!=a:
            parent[a]=parent[parent[a]]; a=parent[a]
        return a
    def union(a,b):
        a,b=find(a),find(b)
        if a!=b: parent[b]=a

    emails={}; phones={}
    for i,r in enumerate(records):
        if r["email_norm"]:
            if r["email_norm"] in emails: union(i,emails[r["email_norm"]])
            else: emails[r["email_norm"]]=i
        if r["phone_norm"]:
            if r["phone_norm"] in phones: union(i,phones[r["phone_norm"]])
            else: phones[r["phone_norm"]]=i

    groups={}
    for i in range(len(records)): groups.setdefault(find(i),[]).append(i)

    conn=sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    # For repeatable runs, recreate tables by executing the same schema as init_db.sql.
    schema=Path(__file__).with_name("schema.sql").read_text()
    conn.executescript("DROP TABLE IF EXISTS audio_submissions; DROP TABLE IF EXISTS source_records; DROP TABLE IF EXISTS people;"+schema)
    roots={}
    for root,members in groups.items():
        ordered=sorted(members,key=lambda i:(records[i]["source"]!="naukri",i))
        def first(key):
            for i in ordered:
                if records[i].get(key) not in (None,""): return records[i][key]
            return None
        skills=[]
        for i in ordered:
            for s in str(records[i].get("skills","")).split(","):
                s=s.strip()
                if s and s.lower() not in {x.lower() for x in skills}: skills.append(s)
        cur=conn.execute("""INSERT INTO people(name,name_norm,email,phone,city,experience_years,current_ctc_lpa,skills)
                            VALUES(?,?,?,?,?,?,?,?)""",
                         (first("name") or "Unknown",first("name_norm"),first("email_norm") or None,
                          first("phone_norm") or None,norm_city(first("city") or ""),
                          first("experience_years"),first("current_ctc_lpa"),", ".join(skills)))
        pid=cur.lastrowid; roots[root]=pid
        for i in ordered:
            method=[]
            if records[i]["email_norm"]: method.append("normalized_email")
            if records[i]["phone_norm"]: method.append("normalized_phone")
            conn.execute("""INSERT INTO source_records(person_id,source_system,source_row,match_method,match_confidence,raw_json)
                            VALUES(?,?,?,?,?,?)""",
                         (pid,records[i]["source"],records[i]["source_row"],"+".join(method) or "new_record",
                          0.99 if method else 1.0,json.dumps(records[i]["raw"],default=str)))
    conn.commit(); conn.close()
    return roots,groups

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--data-dir",default="data"); p.add_argument("--db",default="database/consultbae.db")
    a=p.parse_args()
    records,issues=load_records(Path(a.data_dir))
    roots,groups=build_db(records,Path(a.db))
    report=Path(a.data_dir)/"data_issues_report.csv"
    pd.DataFrame(issues,columns=["source","row","type","action","details"]).to_csv(report,index=False)
    print(f"Source records loaded: {len(records)}")
    print(f"Unique people: {len(groups)}")
    print(f"Potentially merged records: {len(records)-len(groups)}")
    print(f"Data issues captured: {len(issues)}")
    print(f"Report: {report}")
