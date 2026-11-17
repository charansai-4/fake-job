
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import sqlite3
import re
from urllib.parse import urlparse

app = FastAPI(title="JobShield AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

def initialize_db():
    conn = sqlite3.connect("jobshield.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT,
            job_title TEXT,
            job_risk INTEGER,
            company_risk INTEGER,
            result TEXT
        )
    """)
    conn.commit()
    conn.close()

initialize_db()


class JobRequest(BaseModel):
    company_name: str
    job_title: str
    description: str
    salary: str = ""
    recruiter_email: str = ""
    website: str = ""
    registration_verified: bool = False
    official_job_verified: bool = False
    recruitment_fee: bool = False


def analyze_job(data):
    risk = 0
    findings = []

    description = data.description.lower()

    suspicious_patterns = {
        "registration fee": 30,
        "security deposit": 30,
        "pay to get job": 30,
        "guaranteed job": 15,
        "no interview required": 15,
        "urgent hiring": 5,
        "processing fee": 30
    }

    for phrase, score in suspicious_patterns.items():
        if phrase in description:
            risk += score
            findings.append(
                f"Suspicious phrase detected: {phrase}"
            )

    if data.recruitment_fee:
        risk += 35
        findings.append(
            "Recruitment fee or payment requested"
        )

    if not data.official_job_verified:
        risk += 10
        findings.append(
            "Vacancy not independently verified on official careers page"
        )

    return min(risk, 100), findings


def analyze_company(data):
    risk = 0
    findings = []

    if not data.website:
        risk += 20
        findings.append("Official website not provided")

    if not data.registration_verified:
        risk += 35
        findings.append(
            "Company registration has not been independently verified"
        )

    if data.website:
        try:
            domain = urlparse(data.website).hostname
            if not domain:
                risk += 15
                findings.append("Website address is invalid")
        except Exception:
            risk += 15
            findings.append("Website could not be parsed")

    if data.recruiter_email and data.website:
        email_domain = data.recruiter_email.split("@")[-1].lower()
        website_domain = (urlparse(data.website).hostname or "").lower()

        if email_domain not in website_domain and \
           website_domain not in email_domain:
            risk += 15
            findings.append(
                "Recruiter email domain does not match company website"
            )

    return min(risk, 100), findings


def classify(job_risk, company_risk):
    total = round((job_risk * 0.6) + (company_risk * 0.4))

    if total < 30:
        label = "Low Risk"
    elif total < 60:
        label = "Medium Risk"
    elif total < 80:
        label = "High Risk"
    else:
        label = "Critical Risk"

    return total, label


@app.get("/")
def home():
    return {
        "message": "JobShield AI API is running",
        "version": "1.0"
    }


@app.post("/analyze")
def analyze(data: JobRequest):

    job_risk, job_findings = analyze_job(data)

    company_risk, company_findings = analyze_company(data)

    total, result = classify(job_risk, company_risk)

    findings = job_findings + company_findings

    conn = sqlite3.connect("jobshield.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO reports
        (company, job_title, job_risk, company_risk, result)
        VALUES (?, ?, ?, ?, ?)
    """, (
        data.company_name,
        data.job_title,
        job_risk,
        company_risk,
        result
    ))

    report_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "report_id": report_id,
        "company": data.company_name,
        "job_title": data.job_title,
        "job_risk_score": job_risk,
        "company_risk_score": company_risk,
        "overall_risk_score": total,
        "classification": result,
        "job_findings": job_findings,
        "company_findings": company_findings,
        "recommendation": (
            "Verify independently before proceeding"
            if total >= 30 else
            "No major risk indicators found in the submitted information"
        )
    }


@app.get("/reports")
def get_reports():
    conn = sqlite3.connect("jobshield.db")
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM reports ORDER BY id DESC"
    ).fetchall()
    conn.close()

    return [dict(row) for row in rows]
