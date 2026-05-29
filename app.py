import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, session
from werkzeug.utils import secure_filename

from services.interview_engine import (
    analyze_job_description,
    analyze_resume,
    build_interview,
    compare_resume_to_jd,
    generate_final_report,
)
from services.llm import groq_status
from services.resume_parser import extract_text_from_file


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

INTERVIEW_SESSIONS = {}


def get_session_state():
    interview_id = session.get("interview_id")
    if not interview_id:
        interview_id = str(uuid.uuid4())
        session["interview_id"] = interview_id
    return INTERVIEW_SESSIONS.setdefault(
        interview_id,
        {
            "onboarding": {},
            "resume_text": "",
            "resume_analysis": {},
            "jd_text": "",
            "jd_analysis": {},
            "comparison": {},
            "plan": {},
            "questions": [],
            "answers": [],
            "current_index": 0,
            "report": None,
        },
    )


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return render_template("index.html")


@app.get("/api/llm-status")
def llm_status():
    return jsonify(groq_status())


@app.post("/api/onboarding")
def save_onboarding():
    payload = request.get_json(silent=True) or {}
    required = [
        "experience_level",
        "domain",
        "education",
        "target_role",
        "target_companies",
        "question_count",
        "interview_type",
    ]
    missing = [field for field in required if not str(payload.get(field, "")).strip()]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    state = get_session_state()
    state["onboarding"] = payload
    return jsonify({"message": "Onboarding saved", "onboarding": payload})


@app.post("/api/upload-resume")
def upload_resume():
    if "resume" not in request.files:
        return jsonify({"error": "Please upload a resume file."}), 400

    file = request.files["resume"]
    if not file.filename or not allowed_file(file.filename):
        return jsonify({"error": "Resume must be a PDF, DOCX, or TXT file."}), 400

    filename = secure_filename(file.filename)
    path = UPLOAD_DIR / f"{uuid.uuid4()}_{filename}"
    file.save(path)

    text = extract_text_from_file(path)
    if not text.strip():
        return jsonify({"error": "Could not read text from the resume."}), 400

    state = get_session_state()
    state["resume_text"] = text
    state["resume_analysis"] = analyze_resume(text, state.get("onboarding", {}))
    return jsonify({"analysis": state["resume_analysis"]})


@app.post("/api/job-description")
def save_job_description():
    text = request.form.get("jd_text", "").strip()
    jd_file = request.files.get("jd_file")

    if jd_file and jd_file.filename:
        if not allowed_file(jd_file.filename):
            return jsonify({"error": "Job description file must be PDF, DOCX, or TXT."}), 400
        filename = secure_filename(jd_file.filename)
        path = UPLOAD_DIR / f"{uuid.uuid4()}_{filename}"
        jd_file.save(path)
        text = f"{text}\n\n{extract_text_from_file(path)}".strip()

    if not text:
        return jsonify({"error": "Paste or upload a job description."}), 400

    state = get_session_state()
    state["jd_text"] = text
    state["jd_analysis"] = analyze_job_description(text, state.get("onboarding", {}))
    state["comparison"] = compare_resume_to_jd(
        state.get("resume_analysis", {}),
        state["jd_analysis"],
        state.get("onboarding", {}),
    )
    return jsonify({"analysis": state["jd_analysis"], "comparison": state["comparison"]})


@app.post("/api/design-interview")
def design_interview():
    state = get_session_state()
    if not state.get("onboarding"):
        return jsonify({"error": "Complete onboarding first."}), 400

    interview = build_interview(
        onboarding=state["onboarding"],
        resume_analysis=state.get("resume_analysis", {}),
        jd_analysis=state.get("jd_analysis", {}),
        comparison=state.get("comparison", {}),
    )
    state["plan"] = interview["plan"]
    state["questions"] = interview["questions"]
    state["answers"] = []
    state["current_index"] = 0
    state["report"] = None
    return jsonify(interview)


@app.post("/api/answer")
def submit_answer():
    payload = request.get_json(silent=True) or {}
    answer = str(payload.get("answer", "")).strip()
    if not answer:
        return jsonify({"error": "Answer cannot be empty."}), 400

    state = get_session_state()
    questions = state.get("questions", [])
    index = state.get("current_index", 0)
    if not questions:
        return jsonify({"error": "Design the interview first."}), 400
    if index >= len(questions):
        return jsonify({"completed": True, "message": "Interview is already complete."})

    state["answers"].append(
        {
            "question_number": index + 1,
            "question": questions[index]["question"],
            "category": questions[index].get("category", "Mixed"),
            "answer": answer,
        }
    )
    state["current_index"] = index + 1

    if state["current_index"] >= len(questions):
        return jsonify(
            {
                "completed": True,
                "message": "Interview complete. Generate your final report when ready.",
            }
        )

    next_index = state["current_index"]
    return jsonify(
        {
            "completed": False,
            "question_number": next_index + 1,
            "total_questions": len(questions),
            "question": questions[next_index]["question"],
            "category": questions[next_index].get("category", "Mixed"),
        }
    )


@app.get("/api/state")
def get_state():
    state = get_session_state()
    current_index = state.get("current_index", 0)
    questions = state.get("questions", [])
    current_question = questions[current_index] if current_index < len(questions) else None
    return jsonify(
        {
            "onboarding": state.get("onboarding", {}),
            "has_resume": bool(state.get("resume_text")),
            "has_jd": bool(state.get("jd_text")),
            "plan": state.get("plan", {}),
            "current_question": current_question,
            "current_index": current_index,
            "total_questions": len(questions),
            "completed": bool(questions) and current_index >= len(questions),
            "report": state.get("report"),
        }
    )


@app.post("/api/report")
def final_report():
    state = get_session_state()
    if not state.get("questions") or state.get("current_index", 0) < len(state.get("questions", [])):
        return jsonify({"error": "Complete all interview questions before generating the report."}), 400

    state["report"] = generate_final_report(
        onboarding=state.get("onboarding", {}),
        resume_analysis=state.get("resume_analysis", {}),
        jd_analysis=state.get("jd_analysis", {}),
        plan=state.get("plan", {}),
        answers=state.get("answers", []),
    )
    return jsonify({"report": state["report"]})


@app.post("/api/reset")
def reset():
    interview_id = session.pop("interview_id", None)
    if interview_id:
        INTERVIEW_SESSIONS.pop(interview_id, None)
    return jsonify({"message": "Interview reset"})


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
