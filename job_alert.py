#!/usr/bin/env python3
"""
Daily job alert script for GitHub Actions.

- Workflow runs hourly.
- Script only sends email when local time in America/Chicago equals TARGET_HOUR.
- Fetches RemoteOK and filters by KEYWORDS.
"""

import os, sys, requests, smtplib
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

# ---- CONFIG from env ----
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL", SENDER_EMAIL)
TIMEZONE = os.environ.get("TIMEZONE", "America/Chicago")
TARGET_HOUR = int(os.environ.get("TARGET_HOUR", "12"))
REMOTEOK_API = os.environ.get("REMOTEOK_API", "https://remoteok.io/api")
KEYWORDS = [k.strip().lower() for k in os.environ.get(
    "KEYWORDS",
    "program analyst,software developer,data warehouse,data management,intern,entry level,junior,data engineer"
).split(",") if k.strip()]

def local_now():
    if ZoneInfo:
        return datetime.now(ZoneInfo(TIMEZONE))
    return datetime.utcnow()

def is_target_time():
    now = local_now()
    print(f"[INFO] Local time ({TIMEZONE}): {now.isoformat()}")
    return now.hour == TARGET_HOUR

def fetch_jobs():
    try:
        resp = requests.get(REMOTEOK_API, headers={"User-Agent":"Mozilla/5.0"}, timeout=15)
        resp.raise_for_status()
        jobs = resp.json()
    except Exception as e:
        print("[ERROR] Fetch failed:", e)
        return []

    results = []
    for j in jobs[1:]:
        title = (j.get("position") or j.get("title") or "").strip()
        company = j.get("company","").strip()
        link = j.get("url") or j.get("apply_url") or ""
        if any(kw in title.lower() for kw in KEYWORDS):
            results.append({"title": title, "company": company, "link": link})
    return results

def send_email(jobs):
    subject = f"Daily Remote Jobs — {local_now().date().isoformat()}"
    if not jobs:
        body = "No matching jobs found today."
    else:
        parts = []
        for j in jobs:
            parts.append(f"{j['title']} at {j['company']}\nApply: {j['link']}\n")
        body = "\n".join(parts)
    msg = f"Subject: {subject}\n\n{body}"
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=20)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.encode("utf-8"))
        server.quit()
        print(f"[INFO] Email sent to {RECEIVER_EMAIL} ({len(jobs)} job(s))")
    except Exception as e:
        print("[ERROR] Sending email failed:", e)

def main():
    if not (SENDER_EMAIL and SENDER_PASSWORD):
        print("[ERROR] SENDER_EMAIL and SENDER_PASSWORD must be set.")
        sys.exit(1)
    if not is_target_time():
        print("[INFO] Not the target hour — exiting.")
        return
    jobs = fetch_jobs()
    send_email(jobs)

if __name__ == "__main__":
    main()
