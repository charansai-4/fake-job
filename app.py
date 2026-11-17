
import os
import sqlite3
import joblib

from datetime import datetime
from urllib.parse import urlparse

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

# ==================================================
# 1. FLASK CONFIGURATION
# ==================================================

app = Flask(__name__)
app.secret_key = "jobshield-secret-key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(
    BASE_DIR, "model", "fake_job_model.pkl"
)

DATABASE = os.path.join(BASE_DIR, "reports.db")


# ==================================================
# 2. LOAD MACHINE LEARNING MODEL
# ==================================================

ml_model = None
vectorizer = None


def load_model():

    global ml_model, vectorizer

    try:

        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(MODEL_PATH)

        saved_data = joblib.load(MODEL_PATH)

        ml_model = saved_data["model"]
        vectorizer = saved_data["vectorizer"]

        print("JOBSHIELD MODEL LOADED SUCCESSFULLY")
        print("Model:", type(ml_model).__name__)
        print("Vectorizer:", type(vectorizer).__name__)

        return True

    except Exception as error:

        print("MODEL LOADING ERROR:", repr(error))

        ml_model = None
        vectorizer = None

        return False


load_model()


# ==================================================
# 3. DATABASE CONFIGURATION
# ==================================================

def init_db():

    connection = sqlite3.connect(DATABASE)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            job_title TEXT,
            recruiter_email TEXT,
            website TEXT,
            job_url TEXT,
            description TEXT,
            prediction TEXT,
            confidence REAL,
            created_at TEXT
        )
    """)
    columns = [
        row[1] for row in connection.execute(
            "PRAGMA table_info(reports)"
        ).fetchall()
    ]

    if "risk_score" not in columns:
        connection.execute(
            "ALTER TABLE reports ADD COLUMN risk_score INTEGER"
        )

    if "classification" not in columns:
        connection.execute(
            "ALTER TABLE reports ADD COLUMN classification TEXT"
        )

    connection.commit()
    connection.close()


init_db()


# ==================================================
# 4. PREDICTION LABEL
# ==================================================

def get_prediction_label(prediction):

    label = str(prediction).strip().lower()

    if label in ["1", "fake", "fraud", "fraudulent", "scam"]:
        return "Fake Job"

    if label in ["0", "real", "genuine", "legitimate", "safe"]:
        return "Genuine Job"

    return str(prediction)


# ==================================================
# 5. DOMAIN EXTRACTION
# ==================================================

def get_domain(url):

    if not url:
        return ""

    try:

        parsed = urlparse(
            url if "://" in url else "https://" + url
        )

        return (parsed.hostname or "").lower().removeprefix("www.")

    except Exception:

        return ""


# ==================================================
# 6. RISK CALCULATION
# ==================================================

def calculate_risk(
    company_name,
    recruiter_email,
    website,
    job_url,
    fake_probability
):

    risk = float(fake_probability)

    warnings = []

    # Company name check

    if len(company_name.strip()) < 3:

        risk += 15

        warnings.append(
            "Company name is unusually short."
        )

    # Recruiter email check

    email_domain = (
        recruiter_email.split("@")[-1].lower()
        if "@" in recruiter_email
        else ""
    )

    personal_domains = [
        "gmail.com",
        "yahoo.com",
        "outlook.com",
        "hotmail.com",
        "rediffmail.com"
    ]

    if email_domain in personal_domains:

        risk += 15

        warnings.append(
            "Recruiter uses a personal email address."
        )

    # Company website check

    website_domain = get_domain(website)

    job_domain = get_domain(job_url)

    if not website_domain:

        risk += 10

        warnings.append(
            "Company website is missing or invalid."
        )

    # Job advertisement URL check

    if not job_domain:

        risk += 10

        warnings.append(
            "Job advertisement URL is missing or invalid."
        )

    # Compare domains

    if (
        website_domain
        and job_domain
        and website_domain != job_domain
    ):

        risk += 15

        warnings.append(
            "Job advertisement domain differs from company website."
        )

    # Keep score between 0 and 100

    risk = min(round(risk), 100)

    if risk >= 70:

        classification = "High Risk"

    elif risk >= 40:

        classification = "Medium Risk"

    else:

        classification = "Low Risk"

    return risk, classification, warnings


# ==================================================
# 7. MACHINE LEARNING ANALYSIS
# ==================================================

def analyze_job(
    company_name,
    job_title,
    recruiter_email,
    website,
    job_url,
    description
):

    if ml_model is None or vectorizer is None:

        raise RuntimeError(
            "ML model is not loaded. Check model/fake_job_model.pkl."
        )

    job_text = f"""
    Company Name: {company_name}
    Job Title: {job_title}
    Recruiter Email: {recruiter_email}
    Company Website: {website}
    Job Advertisement URL: {job_url}
    Job Description: {description}
    """

    # TF-IDF transformation

    transformed_text = vectorizer.transform(
        [job_text]
    )

    # Model prediction

    raw_prediction = ml_model.predict(
        transformed_text
    )[0]

    prediction = get_prediction_label(
        raw_prediction
    )

    # Probability calculation

    probabilities = ml_model.predict_proba(
        transformed_text
    )[0]

    classes = list(ml_model.classes_)

    if 0 not in classes or 1 not in classes:

        raise ValueError(
            "Model must contain class 0 (Genuine) and class 1 (Fake)."
        )

    fake_index = classes.index(1)

    genuine_index = classes.index(0)

    fake_probability = round(
        float(probabilities[fake_index]) * 100, 2
    )

    genuine_probability = round(
        float(probabilities[genuine_index]) * 100, 2
    )

    confidence = max(
        fake_probability,
        genuine_probability
    )

    # Risk analysis

    risk_score, classification, warnings = calculate_risk(
        company_name,
        recruiter_email,
        website,
        job_url,
        fake_probability
    )

    # Recommendation

    if risk_score >= 70:

        recommendation = (
            "High risk. Do not share personal information "
            "or make payments. Verify the company independently."
        )

    elif risk_score >= 40:

        recommendation = (
            "Medium risk. Verify the recruiter email, company "
            "website and job advertisement before proceeding."
        )

    else:

        recommendation = (
            "Lower risk according to the available checks. "
            "Independently verify the employer."
        )

    # ==================================================
    # INFLUENTIAL WORD ANALYSIS
    # ==================================================

    influential_words = []

    feature_names = vectorizer.get_feature_names_out()

    feature_values = transformed_text.toarray()[0]

    coefficients = ml_model.coef_[0]

    # Positive coefficients represent class 1 (Fake)

    if int(raw_prediction) == 1:

        contributions = feature_values * coefficients

    else:

        contributions = -(feature_values * coefficients)

    top_indices = contributions.argsort()[::-1]

    for index in top_indices:

        if contributions[index] <= 0:
            break

        influential_words.append({

            "word": feature_names[index],

            "weight": round(
                float(contributions[index]), 4
            )

        })

        if len(influential_words) >= 5:
            break

    # ==================================================
    # FINAL RESULT
    # ==================================================

    return {

        "prediction": prediction,

        "fake_probability": fake_probability,

        "genuine_probability": genuine_probability,

        "confidence": confidence,

        "risk_score": risk_score,

        "classification": classification,

        "recommendation": recommendation,

        "warnings": warnings,

        "influential_words": influential_words,

        "company_name": company_name,

        "job_title": job_title,

        "recruiter_email": recruiter_email,

        "website": website,

        "job_url": job_url,

        "description": description

    }


# ==================================================
# 8. SAVE REPORT
# ==================================================


def save_report(ml_result):

    connection = sqlite3.connect(DATABASE)

    connection.execute("""
        INSERT INTO reports (
            company_name,
            job_title,
            recruiter_email,
            website,
            job_url,
            description,
            prediction,
            confidence,
            risk_score,
            classification,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ml_result["company_name"],
        ml_result["job_title"],
        ml_result["recruiter_email"],
        ml_result["website"],
        ml_result["job_url"],
        ml_result["description"],
        ml_result["prediction"],
        ml_result["confidence"],
        ml_result["risk_score"],
        ml_result["classification"],
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    connection.commit()
    connection.close()

    print("REPORT SAVED SUCCESSFULLY")
    print("Risk:", ml_result["risk_score"])
    print("Classification:", ml_result["classification"])

# ==================================================
# 9. HOME PAGE
# ==================================================

@app.route("/")
def index():

    return render_template("home.html")


# ==================================================
# 10. ANALYZE JOB ROUTE
# ==================================================


@app.route("/analyze", methods=["POST"])
def analyze():

    company_name = request.form.get("company_name", "").strip()
    job_title = request.form.get("job_title", "").strip()
    recruiter_email = request.form.get("recruiter_email", "").strip()
    website = request.form.get("website", "").strip()
    job_url = request.form.get("job_url", "").strip()
    description = request.form.get("description", "").strip()

    if not company_name or not job_title or not description:
        flash("Please complete all required fields.", "error")
        return redirect(url_for("index"))

    try:

        ml_result = analyze_job(
            company_name,
            job_title,
            recruiter_email,
            website,
            job_url,
            description
        )

        print("===== DEBUG ANALYSIS =====")
        print("Prediction:", ml_result.get("prediction"))
        print("Confidence:", ml_result.get("confidence"))
        print("Risk Score:", ml_result.get("risk_score"))
        print("Classification:", ml_result.get("classification"))

        save_report(ml_result)

        print("===== REPORT SAVED =====")

        return render_template(
            "analytics.html",
            ml_result=ml_result
        )

    except Exception as error:

        print("ANALYSIS ERROR:", repr(error))

        flash(
            "Unable to analyze job advertisement: " + str(error),
            "error"
        )

        return redirect(url_for("index"))



# ==================================================
# 11. PREVIOUS REPORTS
# ==================================================

@app.route("/reports")
def reports():

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    reports_data = connection.execute("""
        SELECT *
        FROM reports
        ORDER BY id DESC
    """).fetchall()

    connection.close()

    return render_template(
        "report.html",
        reports=reports_data
    )


# ==================================================
# 12. DASHBOARD
# ==================================================

@app.route("/dashboard")
def dashboard():

    connection = sqlite3.connect(DATABASE)

    total = connection.execute("""
        SELECT COUNT(*) FROM reports
    """).fetchone()[0]

    fake = connection.execute("""
        SELECT COUNT(*)
        FROM reports
        WHERE prediction = ?
    """, ("Fake Job",)).fetchone()[0]

    genuine = connection.execute("""
        SELECT COUNT(*)
        FROM reports
        WHERE prediction = ?
    """, ("Genuine Job",)).fetchone()[0]

    connection.close()

    return render_template(
        "report.html",
        total=total,
        fake=fake,
        genuine=genuine
    )



@app.route("/view_report/<int:report_id>")
def view_report(report_id):

    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    report = connection.execute(
        "SELECT * FROM reports WHERE id = ?",
        (report_id,)
    ).fetchone()

    connection.close()

    if report is None:
        flash("Report not found.", "error")
        return redirect(url_for("reports"))

    return render_template(
        "report_detail.html",
        report=report
    )

@app.route("/delete_report/<int:report_id>", methods=["POST"])
def delete_report(report_id):

    connection = sqlite3.connect(DATABASE)

    connection.execute(
        "DELETE FROM reports WHERE id = ?",
        (report_id,)
    )

    connection.commit()
    connection.close()

    flash("Report deleted successfully.", "success")

    return redirect(url_for("reports"))

# ==================================================
# 13. RUN APPLICATION
# ==================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )
