import math
import re
from collections import Counter

from services.llm import complete_json


TECH_KEYWORDS = [
    "python",
    "sql",
    "excel",
    "power bi",
    "tableau",
    "machine learning",
    "flask",
    "django",
    "react",
    "javascript",
    "html",
    "css",
    "aws",
    "azure",
    "docker",
    "git",
    "pandas",
    "numpy",
    "api",
    "rest",
    "java",
    "spring",
    "node",
    "mongodb",
    "postgresql",
    "mysql",
    "scikit-learn",
    "tensorflow",
    "pytorch",
    "nlp",
    "deep learning",
    "model deployment",
    "mlops",
    "statistics",
    "feature engineering",
    "data preprocessing",
]

VAGUE_PHRASES = [
    "multiple project",
    "multiple projects",
    "i have used",
    "i have worked",
    "thats why",
    "that's why",
    "very basic",
    "basic experience",
    "i dont know",
    "i don't know",
    "not sure",
    "no idea",
]

EVIDENCE_WORDS = [
    "because",
    "for example",
    "result",
    "impact",
    "accuracy",
    "precision",
    "recall",
    "f1",
    "latency",
    "users",
    "reduced",
    "improved",
    "deployed",
    "tested",
    "validated",
    "compared",
    "tradeoff",
    "metric",
    "%",
]


def analyze_resume(text, onboarding):
    fallback = {
        "skills": find_keywords(text),
        "projects": extract_lines(text, ["project", "built", "developed", "dashboard"]),
        "education": extract_lines(text, ["education", "degree", "university", "college", "b.tech", "bsc", "msc", "mba"]),
        "experience": extract_lines(text, ["experience", "intern", "worked", "company", "responsible"]),
        "tools": find_keywords(text),
        "achievements": extract_lines(text, ["award", "certification", "achieved", "improved", "rank"]),
        "weak_areas": [],
        "role_fit": "Needs more information, but resume keywords are aligned with the target role.",
        "summary": "Resume parsed with local keyword extraction.",
    }
    system = "You are an expert interview coach. Return only valid JSON."
    user = f"""
Analyze this resume for an interview simulator.

Candidate onboarding:
{onboarding}

Resume text:
{text[:9000]}

Return JSON with keys:
skills, projects, education, experience, tools, achievements, weak_areas, role_fit, summary.
Use concise arrays for list fields.
"""
    return complete_json(system, user, fallback)


def analyze_job_description(text, onboarding):
    fallback = {
        "required_skills": find_keywords(text),
        "responsibilities": extract_lines(text, ["responsible", "build", "develop", "manage", "analyze", "design"]),
        "experience_level": onboarding.get("experience_level", "Not specified"),
        "keywords": top_terms(text, 14),
        "missing_skills": [],
        "expected_topics": find_keywords(text) or top_terms(text, 8),
        "summary": "Job description parsed with local keyword extraction.",
    }
    system = "You are an expert recruiter and interview designer. Return only valid JSON."
    user = f"""
Analyze this job description for interview preparation.

Candidate onboarding:
{onboarding}

Job description:
{text[:9000]}

Return JSON with keys:
required_skills, responsibilities, experience_level, keywords, missing_skills, expected_topics, summary.
Use concise arrays for list fields.
"""
    return complete_json(system, user, fallback)


def compare_resume_to_jd(resume_analysis, jd_analysis, onboarding):
    resume_skills = set(normalize_list(resume_analysis.get("skills", [])))
    jd_skills = set(normalize_list(jd_analysis.get("required_skills", [])))
    matched = sorted(resume_skills & jd_skills)
    missing = sorted(jd_skills - resume_skills)
    fallback = {
        "matched_skills": matched,
        "missing_skills": missing,
        "role_alignment": score_alignment(len(matched), len(jd_skills)),
        "recommended_focus": missing[:6] or list(jd_skills)[:6],
        "summary": "Comparison created from extracted resume and JD skills.",
    }
    system = "You compare resumes against job descriptions. Return only valid JSON."
    user = f"""
Compare this candidate to the job target.

Onboarding:
{onboarding}

Resume analysis:
{resume_analysis}

Job description analysis:
{jd_analysis}

Return JSON with keys:
matched_skills, missing_skills, role_alignment, recommended_focus, summary.
"""
    return complete_json(system, user, fallback)


def build_interview(onboarding, resume_analysis, jd_analysis, comparison):
    count = clamp_question_count(onboarding.get("question_count", 10))
    fallback_plan = local_plan(onboarding, resume_analysis, jd_analysis, comparison, count)
    fallback = {"plan": fallback_plan, "questions": local_questions(onboarding, fallback_plan, count)}
    system = "You are a senior interviewer creating realistic screening questions. Return only valid JSON."
    user = f"""
Create a custom interview plan and exactly {count} interview questions.

Rules:
- Ask one question at a time later, but return the complete list now.
- Do not include feedback or answers.
- Match interview type: {onboarding.get("interview_type")}
- Include resume/project/job-description specific questions where possible.
- Questions must sound like a real interviewer, not a template.
- Avoid generic phrasing like "Explain your experience with X and how you would apply it".
- Use scenario, debugging, project deep-dive, tradeoff, system design, and behavioral questions.
- If the candidate targets Machine Learning, include model evaluation, feature engineering, data leakage, deployment, and project tradeoffs where appropriate.

Onboarding:
{onboarding}

Resume analysis:
{resume_analysis}

Job description analysis:
{jd_analysis}

Resume vs JD comparison:
{comparison}

Return JSON:
{{
  "plan": {{
    "candidate": "...",
    "target_role": "...",
    "focus_areas": ["..."],
    "question_distribution": ["3 SQL questions", "..."],
    "strategy": "..."
  }},
  "questions": [
    {{"category": "Technical", "question": "...", "intent": "..."}}
  ]
}}
"""
    result = complete_json(system, user, fallback, max_tokens=2600)
    result["questions"] = normalize_questions(result.get("questions", []), fallback["questions"], count)
    result["plan"] = result.get("plan") or fallback_plan
    return result


def generate_final_report(onboarding, resume_analysis, jd_analysis, plan, answers):
    fallback = local_report(answers, onboarding)
    system = "You are a strict but fair senior interviewer. Return only valid JSON."
    user = f"""
Generate final interview feedback. Be direct, practical, and kind.

Important scoring rules:
- Short, vague, generic, or incomplete answers must score low.
- Do not give average scores just because the candidate completed the interview.
- Penalize answers that lack examples, reasoning, metrics, project details, or direct response to the question.
- If the candidate says they do not know a required skill, reflect that clearly in weaknesses and technical score.
- Reward honesty, but do not treat honesty as technical competence.

Onboarding:
{onboarding}

Resume analysis:
{resume_analysis}

Job description analysis:
{jd_analysis}

Interview plan:
{plan}

Question-answer transcript:
{answers}

Return JSON with:
overall_score, category_scores, strengths, weaknesses, improvement_tips, final_feedback.
category_scores must contain exactly these keys:
Communication, Technical Knowledge, Confidence, Role Fit, Resume Explanation.
Scores must be numeric out of 10.
"""
    result = complete_json(system, user, fallback, max_tokens=2200)
    return normalize_report(result, fallback)


def local_plan(onboarding, resume_analysis, jd_analysis, comparison, count):
    skills = resume_analysis.get("skills") or jd_analysis.get("required_skills") or ["role fundamentals"]
    interview_type = onboarding.get("interview_type", "Mixed")
    tech_count = max(1, math.ceil(count * 0.5)) if interview_type in ["Technical", "Mixed"] else 0
    behavioral_count = max(1, math.ceil(count * 0.25)) if interview_type in ["Behavioral", "HR", "Mixed"] else 0
    remaining = max(0, count - tech_count - behavioral_count)
    distribution = []
    if tech_count:
        distribution.append(f"{tech_count} technical/domain questions")
    if behavioral_count:
        distribution.append(f"{behavioral_count} HR or behavioral questions")
    if remaining:
        distribution.append(f"{remaining} resume, project, or managerial questions")
    return {
        "candidate": onboarding.get("experience_level", "Candidate"),
        "target_role": onboarding.get("target_role", "Target role"),
        "focus_areas": list(dict.fromkeys(skills + comparison.get("recommended_focus", [])))[:8],
        "question_distribution": distribution,
        "strategy": "Start broad, probe role skills, include resume/project depth, and finish with behavioral fit.",
    }


def local_questions(onboarding, plan, count):
    role = onboarding.get("target_role", "this role")
    interview_type = onboarding.get("interview_type", "Mixed")
    domain = onboarding.get("domain", "")
    focus_areas = plan.get("focus_areas", []) or ["core concepts", "projects", "communication"]
    templates = question_bank_for_role(role, domain, focus_areas)
    questions = []
    for index in range(count):
        category, question = templates[index % len(templates)]
        if interview_type != "Mixed":
            category, question = adapt_question_to_type(interview_type, role, focus_areas, index, question)
        questions.append({"category": category, "question": question, "intent": "Assess fit, depth, and clarity."})
    return questions


def local_report(answers, onboarding):
    evaluations = [evaluate_answer(item) for item in answers]
    base_score = sum(item["score"] for item in evaluations) / max(1, len(evaluations))
    technical_scores = [item["score"] for item in evaluations if item["category"].lower() in ["technical", "project"]]
    behavioral_scores = [item["score"] for item in evaluations if item["category"].lower() in ["behavioral", "hr", "managerial"]]
    very_weak = [item for item in evaluations if item["score"] < 5.0]
    vague_count = sum(1 for item in evaluations if item["is_vague"])
    unknown_count = sum(1 for item in evaluations if item["does_not_know"])

    strengths = ["Completed the full interview flow."]
    if any(item["has_evidence"] for item in evaluations):
        strengths.append("Some answers included useful evidence or project context.")
    if unknown_count:
        strengths.append("Was honest about areas where knowledge is limited.")
    if len(strengths) == 1:
        strengths.append("Showed basic willingness to engage with the interview questions.")

    weaknesses = []
    if vague_count:
        weaknesses.append("Several answers were too generic and did not directly answer the interviewer's question.")
    if unknown_count:
        weaknesses.append("Important skill gaps were visible where the answer said the candidate does not know the topic.")
    if very_weak:
        weaknesses.append("Some answers lacked examples, technical reasoning, metrics, or clear project details.")
    if not weaknesses:
        weaknesses.append("Answers can still be improved by adding stronger structure, tradeoffs, and measurable outcomes.")

    return {
        "overall_score": round(base_score, 1),
        "category_scores": {
            "Communication": round(score_communication(evaluations), 1),
            "Technical Knowledge": round(average_or_default(technical_scores, base_score), 1),
            "Confidence": round(max(2.0, base_score - (0.8 if vague_count else 0.2)), 1),
            "Role Fit": round(max(2.0, base_score - (0.9 if unknown_count else 0.1)), 1),
            "Resume Explanation": round(score_resume_explanation(evaluations), 1),
        },
        "strengths": strengths,
        "weaknesses": weaknesses,
        "improvement_tips": [
            "Use the STAR method for HR and behavioral answers.",
            "For technical answers, explain the problem, approach, tradeoffs, validation method, and result.",
            "Add concrete project examples with tools, datasets, metrics, and outcomes.",
            f"Prepare deeper answers for the {onboarding.get('target_role', 'target role')} interview topics.",
            "When you do not know a tool, say how you would learn it and relate it to a similar tool you know.",
        ],
        "final_feedback": final_feedback_text(base_score, vague_count, unknown_count),
        "answer_reviews": evaluations,
    }


def question_bank_for_role(role, domain, focus_areas):
    role_text = f"{role} {domain}".lower()
    first_skill = focus_areas[0] if focus_areas else "your strongest technical skill"
    second_skill = focus_areas[1] if len(focus_areas) > 1 else "a relevant tool"

    if any(term in role_text for term in ["machine learning", "ml engineer", "data scientist", "ai engineer"]):
        return [
            ("HR", f"Give me a 90-second introduction focused on your machine learning background, your strongest project, and why you are targeting the {role} role."),
            ("Technical", "You train a model and get 95% accuracy on validation, but it performs poorly after deployment. Walk me through how you would diagnose the issue."),
            ("Technical", "How would you detect and prevent data leakage in a machine learning pipeline? Give a concrete example."),
            ("Project", "Pick one ML project from your resume. Explain the dataset, target variable, features, model choices, evaluation metric, and final result."),
            ("Technical", "For an imbalanced classification problem, which metrics and techniques would you consider, and why?"),
            ("Technical", "How would you design a feature engineering and preprocessing pipeline that can run consistently in training and production?"),
            ("Technical", "Suppose your model is overfitting. What signals would confirm it, and what steps would you try first?"),
            ("Technical", "How would you deploy a trained model as an API and monitor whether its predictions remain reliable over time?"),
            ("Behavioral", "Tell me about a time a model, experiment, or project did not work as expected. What did you change?"),
            ("Managerial", "If a product manager asks for a more accurate model but engineering asks for lower latency, how would you handle the tradeoff?"),
        ]

    if any(term in role_text for term in ["data analyst", "business analyst", "analytics"]):
        return [
            ("HR", f"Introduce yourself for a {role} interview and highlight one analysis project that proves your fit."),
            ("Technical", "A dashboard metric suddenly drops by 30% overnight. How would you investigate whether it is a real business change or a data issue?"),
            ("Technical", "Write out how you would use SQL to find repeat customers, monthly revenue, and top-performing segments."),
            ("Project", "Walk me through one dashboard or analysis project: business question, data source, transformations, insights, and recommendation."),
            ("Technical", "How do you decide which chart or metric best communicates an insight to non-technical stakeholders?"),
            ("Technical", "How would you handle missing values, duplicates, and inconsistent category names before reporting?"),
            ("Behavioral", "Tell me about a time you had to explain a data finding to someone who disagreed with it."),
            ("Managerial", "If two teams request urgent reports at the same time, how would you prioritize the work?"),
        ]

    if any(term in role_text for term in ["web", "frontend", "backend", "full stack", "software", "developer"]):
        return [
            ("HR", f"Give me a concise introduction and connect your projects to the {role} role."),
            ("Technical", "Design a small API for a chatbot application. What endpoints, data models, and validations would you include?"),
            ("Technical", "A page works locally but fails for users in production. How would you debug it step by step?"),
            ("Project", "Pick one software project and explain architecture, key decisions, bugs you solved, and what you would improve now."),
            ("Technical", "How would you secure file uploads and user input in a web application?"),
            ("Technical", "How do you structure frontend state when a workflow has multiple steps and API calls?"),
            ("Behavioral", "Tell me about a time you had to change your implementation after feedback or testing."),
            ("Managerial", "How do you estimate and communicate progress when a feature is more complex than expected?"),
        ]

    return [
        ("HR", f"Introduce yourself and connect your background to the {role} role."),
        ("Technical", f"Describe a realistic task in this role where {first_skill} would matter. How would you approach it from start to finish?"),
        ("Project", "Choose your strongest project and explain the problem, your exact contribution, tools used, challenges, and measurable result."),
        ("Technical", f"If your first approach using {second_skill} failed, how would you debug and choose an alternative?"),
        ("Behavioral", "Tell me about a time you had to learn a difficult concept quickly for a project or deadline."),
        ("Managerial", "How do you prioritize quality, speed, and communication when several tasks are due together?"),
    ]


def adapt_question_to_type(interview_type, role, focus_areas, index, original_question):
    skill = focus_areas[index % len(focus_areas)] if focus_areas else "a core role skill"
    type_name = interview_type.lower()
    if type_name == "technical":
        technical = [
            f"Here is a practical {role} scenario: the output is wrong but there is no error message. How would you debug it step by step?",
            f"Explain a core concept behind {skill}, then give a real example of where it can fail.",
            f"How would you validate that your {skill}-based solution is correct, reliable, and ready for users?",
            f"What tradeoffs would you consider when choosing between two approaches for a {role} task?",
        ]
        return "Technical", technical[index % len(technical)]
    if type_name == "hr":
        hr = [
            f"Tell me about yourself in a way that is relevant to the {role} role.",
            f"Why are you interested in this {role} position, and what makes you ready for it?",
            "What is one weakness in your preparation right now, and what are you doing to improve it?",
            "Why should we select you for the next round?",
        ]
        return "HR", hr[index % len(hr)]
    if type_name == "behavioral":
        behavioral = [
            "Tell me about a time you solved a difficult problem with limited guidance.",
            "Tell me about a time your first solution failed. What did you learn and change?",
            "Tell me about a time you had to explain technical work to a non-technical person.",
            "Tell me about a time you handled feedback or disagreement during a project.",
        ]
        return "Behavioral", behavioral[index % len(behavioral)]
    if type_name == "managerial":
        managerial = [
            "How would you plan your first two weeks after joining this role?",
            "How do you prioritize when quality, speed, and stakeholder expectations conflict?",
            "How would you communicate a project delay to your manager and team?",
            "How would you mentor a junior teammate who is stuck on a task you understand well?",
        ]
        return "Managerial", managerial[index % len(managerial)]
    return interview_type, original_question


def evaluate_answer(item):
    answer = item.get("answer", "").strip()
    words = re.findall(r"[A-Za-z0-9%+.#-]+", answer.lower())
    word_count = len(words)
    lowered = answer.lower()
    does_not_know = any(phrase in lowered for phrase in ["i dont know", "i don't know", "don't know", "dont know", "no idea"])
    is_vague = any(phrase in lowered for phrase in VAGUE_PHRASES)
    has_evidence = any(marker in lowered for marker in EVIDENCE_WORDS) or bool(re.search(r"\d", answer))

    score = 3.0
    if word_count >= 20:
        score += 1.0
    if word_count >= 45:
        score += 1.0
    if word_count >= 80:
        score += 0.8
    if has_evidence:
        score += 1.2
    if mentions_question_terms(item.get("question", ""), answer):
        score += 0.8
    if is_vague:
        score -= 1.0
    if does_not_know:
        score -= 1.6
    if word_count < 12:
        score -= 1.2
    if word_count < 6:
        score -= 1.0

    score = max(1.0, min(9.0, score))
    return {
        "question_number": item.get("question_number"),
        "category": item.get("category", "Mixed"),
        "question": item.get("question", ""),
        "score": round(score, 1),
        "word_count": word_count,
        "is_vague": is_vague,
        "does_not_know": does_not_know,
        "has_evidence": has_evidence,
        "feedback": answer_feedback(score, is_vague, does_not_know, has_evidence, word_count),
    }


def mentions_question_terms(question, answer):
    question_terms = {
        word
        for word in re.findall(r"[A-Za-z][A-Za-z+#.]{3,}", question.lower())
        if word not in {"would", "your", "that", "this", "with", "from", "role", "tell", "about", "explain"}
    }
    answer_words = set(re.findall(r"[A-Za-z][A-Za-z+#.]{3,}", answer.lower()))
    return bool(question_terms & answer_words)


def answer_feedback(score, is_vague, does_not_know, has_evidence, word_count):
    if does_not_know:
        return "Honest, but it does not demonstrate competence for this topic. Add what you know, related experience, and a learning plan."
    if word_count < 12:
        return "Too short for an interview answer. It needs context, reasoning, and an example."
    if is_vague:
        return "Too generic. Name the project, tools, decisions, result, and what you personally did."
    if not has_evidence:
        return "Needs stronger evidence such as metrics, examples, tradeoffs, or validation details."
    if score >= 7:
        return "Good answer structure. It can become stronger with more specific tradeoffs and measurable impact."
    return "Partially answered, but needs more depth and a clearer connection to the question."


def average_or_default(values, default):
    return sum(values) / len(values) if values else default


def score_communication(evaluations):
    if not evaluations:
        return 1.0
    base = average_or_default([item["score"] for item in evaluations], 1.0)
    short_penalty = sum(1 for item in evaluations if item["word_count"] < 12) * 0.35
    vague_penalty = sum(1 for item in evaluations if item["is_vague"]) * 0.25
    return max(1.0, min(9.0, base - short_penalty - vague_penalty + 0.3))


def score_resume_explanation(evaluations):
    project_scores = [item["score"] for item in evaluations if item["category"].lower() == "project"]
    if project_scores:
        return average_or_default(project_scores, 1.0)
    return max(1.0, average_or_default([item["score"] for item in evaluations], 1.0) - 0.4)


def final_feedback_text(base_score, vague_count, unknown_count):
    if base_score < 4.5:
        return "This interview needs significant improvement. Most answers were too short, vague, or incomplete for a real interview round."
    if vague_count or unknown_count:
        return "You have a base to build on, but the answers need sharper examples, stronger technical reasoning, and clearer proof of role readiness."
    if base_score < 7:
        return "Decent attempt, but move from general statements to structured answers with examples, metrics, and tradeoffs."
    return "Strong attempt overall. Keep improving specificity, depth, and role-focused examples."


def normalize_questions(questions, fallback, count):
    normalized = []
    for item in questions:
        if isinstance(item, str):
            normalized.append({"category": "Mixed", "question": item, "intent": "Assess candidate fit."})
        elif isinstance(item, dict) and item.get("question"):
            normalized.append(
                {
                    "category": item.get("category", "Mixed"),
                    "question": item["question"],
                    "intent": item.get("intent", "Assess candidate fit."),
                }
            )
    if len(normalized) < count:
        normalized.extend(fallback[len(normalized) : count])
    return normalized[:count]


def normalize_report(result, fallback):
    desired_categories = [
        "Communication",
        "Technical Knowledge",
        "Confidence",
        "Role Fit",
        "Resume Explanation",
    ]
    normalized = {
        "overall_score": numeric_score(result.get("overall_score"), fallback["overall_score"]),
        "category_scores": {},
        "strengths": result.get("strengths") or fallback["strengths"],
        "weaknesses": result.get("weaknesses") or fallback["weaknesses"],
        "improvement_tips": result.get("improvement_tips") or fallback["improvement_tips"],
        "final_feedback": result.get("final_feedback") or fallback["final_feedback"],
        "answer_reviews": result.get("answer_reviews") or fallback.get("answer_reviews", []),
    }
    result_categories = result.get("category_scores", {}) if isinstance(result.get("category_scores"), dict) else {}
    for category in desired_categories:
        normalized["category_scores"][category] = numeric_score(
            result_categories.get(category),
            fallback["category_scores"].get(category, normalized["overall_score"]),
        )
    return normalized


def numeric_score(value, default):
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = float(default)
    return round(max(1.0, min(10.0, score)), 1)


def clamp_question_count(value):
    try:
        count = int(value)
    except (TypeError, ValueError):
        count = 10
    return max(3, min(20, count))


def find_keywords(text):
    lowered = text.lower()
    found = [keyword.title() if keyword != "sql" else "SQL" for keyword in TECH_KEYWORDS if keyword in lowered]
    return list(dict.fromkeys(found))


def extract_lines(text, markers):
    lines = []
    for line in text.splitlines():
        clean = re.sub(r"\s+", " ", line).strip(" -•\t")
        if len(clean) < 8:
            continue
        lowered = clean.lower()
        if any(marker in lowered for marker in markers):
            lines.append(clean[:220])
    return lines[:8]


def top_terms(text, limit):
    words = re.findall(r"[A-Za-z][A-Za-z+#.]{2,}", text.lower())
    stop_words = {
        "and",
        "the",
        "for",
        "with",
        "you",
        "our",
        "are",
        "will",
        "this",
        "that",
        "from",
        "job",
        "role",
        "work",
        "team",
        "have",
    }
    counts = Counter(word for word in words if word not in stop_words)
    return [word for word, _ in counts.most_common(limit)]


def normalize_list(values):
    return [str(value).strip().lower() for value in values if str(value).strip()]


def score_alignment(matched_count, required_count):
    if required_count == 0:
        return "Not enough JD data to score alignment."
    percent = round((matched_count / required_count) * 100)
    if percent >= 75:
        return f"Strong alignment ({percent}%)."
    if percent >= 45:
        return f"Moderate alignment ({percent}%)."
    return f"Needs preparation ({percent}%)."
