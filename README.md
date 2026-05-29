<div align="center">

# 🎯 PrepMate — AI Mock Interview Coach

**Practice. Get Feedback. Get Hired.**  
A conversational AI interview simulator that builds a fully personalized mock interview from your resume and job description — then scores your answers and delivers detailed feedback using Groq's Llama 3.3 70B.

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=flat-square&logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-black?style=flat-square&logo=flask)](https://flask.palletsprojects.com/)
[![Groq](https://img.shields.io/badge/Groq-Llama%203.3%2070B-orange?style=flat-square)](https://groq.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

</div>

---

<img width="1918" height="911" alt="image" src="https://github.com/user-attachments/assets/20b2dff1-938f-44d5-96c8-176203565136" />

---

## ✨ What is PrepMate?

PrepMate is a full-stack AI web application that simulates a real job interview — personalized to **your resume** and **your target role**.

Unlike generic question lists, PrepMate:

- Reads your actual resume and the job description
- Identifies your skill gaps before the interview starts
- Generates role-specific questions (not templates)
- Listens to or reads your answers one by one
- Scores every answer and explains exactly what was weak
- Delivers a final report with category scores, strengths, weaknesses, and improvement tips

It works **with or without a Groq API key** — a smart local fallback handles everything offline.

---

## 🖥️ How It Works — The 5 Phases

```
Phase 1: Onboarding     → Tell PrepMate your experience, domain, target role, company
Phase 2: Resume Upload  → Upload PDF / DOCX / TXT → AI extracts skills, projects, gaps
Phase 3: Job Description → Paste or upload JD → AI compares it against your resume
Phase 4: Live Interview  → Answer questions one by one (type or speak)
Phase 5: Final Report    → Scores across 5 categories + per-answer feedback
```

---

## 🚀 Features

- 🤖 **AI-Powered Analysis** — Resume and JD analyzed by Llama 3.3 70B via Groq
- 🎯 **Role-Aware Questions** — Separate question banks for ML Engineers, Data Analysts, Web Developers, and more
- 🎙️ **Voice Support** — Text-to-speech reads questions aloud; mic input lets you answer by speaking
- 📊 **Smart Scoring** — Answers scored on depth, evidence, technical relevance, and clarity
- 🔌 **Offline Fallback** — Runs fully without an API key using local keyword extraction and question banks
- 🔐 **Session Isolation** — Every user gets a unique UUID session; no data mixing
- 📄 **Multi-format Resume** — Supports PDF, DOCX, and TXT uploads

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| **Web Framework** | Flask 3.0 |
| **AI Model** | Llama 3.3 70B via Groq API |
| **Resume Parsing** | PyPDF2 (PDF), python-docx (DOCX) |
| **Frontend** | Vanilla JS, Web Speech API |
| **Session Management** | Flask sessions + UUID |
| **Config** | python-dotenv |

---

## 📁 Project Structure

```
PrepMate/
│
├── app.py                      # Flask app — all API routes and session logic
│
├── services/
│   ├── llm.py                  # Groq API wrapper — sends prompts, parses JSON responses
│   ├── resume_parser.py        # Extracts text from PDF / DOCX / TXT
│   └── interview_engine.py     # Core logic — analysis, question generation, scoring
│
├── static/
│   ├── css/styles.css          # UI styling
│   └── js/app.js               # Frontend — phases, voice, API calls, report rendering
│
├── templates/
│   └── index.html              # Single-page Jinja2 template
│
├── requirements.txt
├── .env.example                # Template for environment variables
├── .gitignore
└── README.md
```

---

## ⚙️ Setup & Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/prepmate.git
cd prepmate
```

### 2. Create a Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and add your Groq API key:

```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxx
GROQ_MODEL=llama-3.3-70b-versatile
FLASK_SECRET_KEY=your-secret-key-here
```

> 🆓 Groq is **free** — get your key at [console.groq.com](https://console.groq.com)  
> The app also runs without a key using the built-in local fallback.

### 5. Run the App

```bash
python app.py
```

Visit `http://localhost:5000` in your browser.

---

## 🔬 How the Scoring Works

Every answer is evaluated **locally** (no API needed for scoring):

| Signal | Score Effect |
|---|---|
| Answer ≥ 80 words | +0.8 |
| Contains evidence (metrics, %, numbers, examples) | +1.2 |
| Directly addresses the question terms | +0.8 |
| Vague phrases ("multiple projects", "basic experience") | −1.0 |
| "I don't know" / "no idea" | −1.6 |
| Answer under 12 words | −1.2 |

**5 category scores** are reported at the end:

- Communication
- Technical Knowledge
- Confidence
- Role Fit
- Resume Explanation

---

## 🤖 AI Models & API

| Component | Model / Service |
|---|---|
| Resume Analysis | Llama 3.3 70B via Groq |
| JD Analysis & Comparison | Llama 3.3 70B via Groq |
| Interview Question Generation | Llama 3.3 70B via Groq |
| Final Feedback Report | Llama 3.3 70B via Groq |
| Answer Scoring | Local algorithm (no API) |

All Groq calls use `response_format: json_object` — the model is instructed to return structured JSON directly, which is then parsed and used to drive the UI.

---

## 🎙️ Voice Features

PrepMate uses the browser's built-in **Web Speech API** — no external library needed:

- **Text-to-Speech** — every question is read aloud automatically
- **Speech-to-Text** — click the mic button and answer by speaking
- **Replay** — replay the last spoken question anytime
- **Toggle** — turn voice on/off with one click

> Works best in Chrome or Edge.

---

## 🔐 Security Notes

- `.env` is never committed — already in `.gitignore`
- Uploaded resume/JD files are saved with UUID-prefixed names to avoid conflicts
- Flask `MAX_CONTENT_LENGTH` is set to 8MB to prevent oversized uploads
- `secure_filename()` sanitizes all uploaded filenames

---

## 🗺️ Roadmap

- [ ] Export final report as PDF
- [ ] Add follow-up questions based on weak answers
- [ ] Support multiple interview rounds in one session
- [ ] Deploy to Render / Railway with Docker
- [ ] Add RAG pipeline for deeper resume-JD matching

---

## 📄 License

This project is licensed under the **MIT License** — free to use, modify, and distribute.

---

## 🙋 Author

Built to make interview prep smarter, not harder.  
Feel free to open issues, fork the repo, or reach out!

> ⭐ If PrepMate helped you prepare, consider giving it a star!
