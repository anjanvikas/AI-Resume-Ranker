"""Smoke test — creates sample resumes and hits the API."""
import requests
import tempfile
import os
import time
import zipfile
import io

BASE = "http://localhost:8000"

# ── Sample data ─────────────────────────────────────────────
JD = """
Senior Python Backend Engineer

We are looking for a Senior Python Backend Engineer with 5+ years of experience.

Requirements:
- Strong Python skills (FastAPI, Django, or Flask)
- Experience with PostgreSQL, Redis
- Understanding of microservices architecture
- Experience with Docker and Kubernetes
- Strong problem-solving skills
- Good communication skills
- BS/MS in Computer Science

Nice to have:
- Experience with machine learning pipelines
- AWS/GCP cloud experience
"""

RESUMES = {
    "alice_python_senior.txt": """
Alice Johnson
Senior Software Engineer | Python Specialist
alice@example.com | San Francisco, CA

EXPERIENCE:
Senior Python Engineer, TechCorp (2019 - Present)
- Built and maintained FastAPI microservices serving 10M requests/day
- Designed PostgreSQL schemas and optimized queries, reducing p99 latency by 40%
- Led migration from monolith to microservices on Kubernetes
- Mentored 4 junior engineers

Software Engineer, StartupXYZ (2016 - 2019)
- Developed Django REST APIs for e-commerce platform
- Implemented Redis caching layer, improving response times by 60%
- Deployed services on AWS using Docker

EDUCATION:
MS Computer Science, Stanford University (2016)
BS Computer Science, UC Berkeley (2014)

SKILLS: Python, FastAPI, Django, PostgreSQL, Redis, Docker, Kubernetes, AWS, CI/CD
""",
    "bob_frontend_dev.txt": """
Bob Smith
Frontend Developer
bob@example.com | New York, NY

EXPERIENCE:
Senior Frontend Engineer, WebAgency (2020 - Present)
- Built React applications for enterprise clients
- Implemented responsive designs using TailwindCSS
- Set up CI/CD pipelines with GitHub Actions

Junior Frontend Developer, SmallCo (2018 - 2020)
- Developed landing pages using HTML/CSS/JavaScript
- Worked with REST APIs for data fetching

EDUCATION:
BA in Graphic Design, NYU (2018)

SKILLS: React, JavaScript, TypeScript, HTML, CSS, TailwindCSS, Figma
""",
    "carol_ml_python.txt": """
Carol Davis
Machine Learning Engineer
carol@example.com | Seattle, WA

EXPERIENCE:
ML Engineer, AICompany (2020 - Present)
- Built ML pipelines using Python, scikit-learn, and TensorFlow
- Deployed models as FastAPI services on GCP with Docker
- Managed PostgreSQL databases for feature storage
- Reduced model inference time by 50% through optimization

Data Scientist, DataFirm (2017 - 2020)
- Developed predictive models using Python and pandas
- Built Flask APIs for model serving
- Used Redis for real-time feature caching

EDUCATION:
MS Machine Learning, Carnegie Mellon University (2017)
BS Computer Science, MIT (2015)

SKILLS: Python, FastAPI, Flask, scikit-learn, TensorFlow, PostgreSQL, Redis, Docker, GCP, Kubernetes
"""
}

# ── Create a ZIP file ───────────────────────────────────────
zip_buffer = io.BytesIO()
with zipfile.ZipFile(zip_buffer, 'w') as zf:
    for name, content in RESUMES.items():
        zf.writestr(name, content)
zip_buffer.seek(0)

# ── Submit to API ───────────────────────────────────────────
print("📤 Submitting JD + 3 resumes (as ZIP)...")
files = [("files", ("resumes.zip", zip_buffer.read(), "application/zip"))]
resp = requests.post(f"{BASE}/api/analyze", data={"job_description": JD}, files=files)

if resp.status_code != 200:
    print(f"❌ Upload failed: {resp.status_code} {resp.text}")
    exit(1)

job_id = resp.json()["job_id"]
print(f"✅ Job created: {job_id}")

# ── Poll for completion ─────────────────────────────────────
print("⏳ Waiting for pipeline...")
for i in range(60):
    status = requests.get(f"{BASE}/api/status/{job_id}").json()
    s = status["status"]
    print(f"   [{i+1}] Status: {s}", end="")
    if s == "evaluating":
        print(f" — {status.get('progress', '?')}/{status.get('total_eval', '?')}")
    else:
        print()
    
    if s == "complete":
        break
    elif s == "error":
        print(f"❌ Pipeline error: {status.get('error')}")
        exit(1)
    time.sleep(3)

# ── Fetch results ───────────────────────────────────────────
results = requests.get(f"{BASE}/api/results/{job_id}").json()

print("\n" + "="*60)
print("🏆 RANKING RESULTS")
print("="*60)

for r in results["results"]:
    print(f"\n#{r['rank']} — {r['filename']}  (Score: {r['composite_score']})")
    print(f"   Skills: {r.get('skills_match', 'N/A')} | Experience: {r.get('experience_relevance', 'N/A')} | Education: {r.get('education_fit', 'N/A')}")
    print(f"   Summary: {r.get('summary', 'N/A')}")
    if r.get('key_strengths'):
        print(f"   Strengths: {', '.join(r['key_strengths'])}")
    if r.get('gaps'):
        print(f"   Gaps: {', '.join(r['gaps'])}")

print(f"\n✅ Smoke test passed! {len(results['results'])} candidates ranked.")
