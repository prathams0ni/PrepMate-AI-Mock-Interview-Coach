const messages = document.querySelector("#messages");
const chatForm = document.querySelector("#chatForm");
const textInput = document.querySelector("#textInput");
const uploadForm = document.querySelector("#uploadForm");
const fileInput = document.querySelector("#fileInput");
const jdText = document.querySelector("#jdText");
const uploadLabel = document.querySelector("#uploadLabel");
const sessionTitle = document.querySelector("#sessionTitle");
const apiStatus = document.querySelector("#apiStatus");
const resetBtn = document.querySelector("#resetBtn");
const voiceToggleBtn = document.querySelector("#voiceToggleBtn");
const replayBtn = document.querySelector("#replayBtn");
const micBtn = document.querySelector("#micBtn");
const progressItems = [...document.querySelectorAll("#progressList li")];

const onboardingQuestions = [
  ["experience_level", "What is your experience level?"],
  ["domain", "What is your domain?"],
  ["education", "What is your education background?"],
  ["target_role", "Which role are you targeting?"],
  ["target_companies", "Which companies or job type are you preparing for?"],
  ["question_count", "How many interview questions do you want? Example: 5, 10, 15, 20"],
  ["interview_type", "What interview type do you want? HR, Technical, Behavioral, Managerial, or Mixed"],
];

let phase = "onboarding";
let onboardingIndex = 0;
let onboarding = {};
let currentQuestion = null;
let llmStatus = null;
let voiceEnabled = true;
let latestSpeakableText = "";
let recognition = null;
let isListening = false;

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const speechSupported = "speechSynthesis" in window;
const recognitionSupported = Boolean(SpeechRecognition);

function addMessage(text, type = "bot") {
  const el = document.createElement("div");
  el.className = `message ${type}`;
  el.textContent = text;
  messages.appendChild(el);
  messages.scrollTop = messages.scrollHeight;
}

function addBotMessage(text, shouldSpeak = false) {
  addMessage(text, "bot");
  if (shouldSpeak) speakText(text);
}

function addHtml(html, type = "bot") {
  const el = document.createElement("div");
  el.className = `message ${type}`;
  el.innerHTML = html;
  messages.appendChild(el);
  messages.scrollTop = messages.scrollHeight;
}

function setBusy(isBusy, label = "Thinking") {
  apiStatus.textContent = isBusy ? label : statusLabel();
  textInput.disabled = isBusy;
  chatForm.querySelector("button").disabled = isBusy;
  uploadForm.querySelector("button").disabled = isBusy;
}

function statusLabel() {
  if (!llmStatus) return "Checking AI";
  return llmStatus.connected ? `Groq connected: ${llmStatus.model}` : "Fallback mode";
}

function renderLlmStatus() {
  apiStatus.textContent = statusLabel();
  apiStatus.classList.toggle("connected", Boolean(llmStatus?.connected));
  apiStatus.classList.toggle("fallback", !llmStatus?.connected);
}

async function loadLlmStatus() {
  try {
    const response = await fetch("/api/llm-status");
    llmStatus = await response.json();
    renderLlmStatus();
    if (llmStatus.connected) {
      addMessage(`AI source: Groq is connected using ${llmStatus.model}.`, "system");
    } else {
      addMessage(`AI source: Local fallback. ${llmStatus.message}`, "system");
    }
  } catch (error) {
    llmStatus = { connected: false, model: "", message: "Could not check Groq status." };
    renderLlmStatus();
    addMessage("AI source: Local fallback. Could not check Groq status.", "system");
  }
}

function speakText(text) {
  if (!voiceEnabled || !speechSupported || !text) return;
  window.speechSynthesis.cancel();
  latestSpeakableText = text;
  const utterance = new SpeechSynthesisUtterance(cleanSpeechText(text));
  utterance.lang = "en-US";
  utterance.rate = 0.92;
  utterance.pitch = 1;
  window.speechSynthesis.speak(utterance);
}

function cleanSpeechText(text) {
  return text
    .replace(/Question\s+\d+\/\d+:/gi, "Question.")
    .replace(/\n+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function configureVoiceControls() {
  voiceToggleBtn.classList.toggle("active", voiceEnabled);
  voiceToggleBtn.textContent = voiceEnabled ? "Voice on" : "Voice off";
  voiceToggleBtn.disabled = !speechSupported;
  replayBtn.disabled = !speechSupported;
  micBtn.disabled = !recognitionSupported;

  if (!speechSupported || !recognitionSupported) {
    const missing = [
      !speechSupported ? "text-to-speech" : "",
      !recognitionSupported ? "speech-to-text" : "",
    ]
      .filter(Boolean)
      .join(" and ");
    addMessage(`Voice notice: Your browser does not fully support ${missing}. Chrome or Edge usually works best.`, "system");
  }
}

function setupRecognition() {
  if (!recognitionSupported) return;
  recognition = new SpeechRecognition();
  recognition.lang = "en-US";
  recognition.interimResults = true;
  recognition.continuous = false;

  recognition.onstart = () => {
    isListening = true;
    micBtn.classList.add("listening");
    micBtn.textContent = "Listening";
    textInput.placeholder = "Listening...";
  };

  recognition.onresult = (event) => {
    let transcript = "";
    for (let index = event.resultIndex; index < event.results.length; index += 1) {
      transcript += event.results[index][0].transcript;
    }
    textInput.value = transcript.trim();
  };

  recognition.onerror = (event) => {
    addMessage(`Speech-to-text error: ${event.error}. You can still type your answer.`, "system");
  };

  recognition.onend = () => {
    isListening = false;
    micBtn.classList.remove("listening");
    micBtn.textContent = "Mic";
    textInput.placeholder = phase === "interview" ? "Answer the interview question..." : "Type your answer...";
  };
}

function toggleListening() {
  if (!recognition) return;
  if (isListening) {
    recognition.stop();
    return;
  }
  window.speechSynthesis?.cancel();
  recognition.start();
}

function setProgress(index) {
  progressItems.forEach((item, itemIndex) => {
    item.classList.toggle("active", itemIndex === index);
    item.classList.toggle("done", itemIndex < index);
  });
}

function askCurrentOnboardingQuestion() {
  const [, question] = onboardingQuestions[onboardingIndex];
  addBotMessage(question, true);
}

async function postJson(url, body = {}) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed");
  return data;
}

async function handleOnboardingAnswer(answer) {
  const [key] = onboardingQuestions[onboardingIndex];
  onboarding[key] = answer;
  onboardingIndex += 1;

  if (onboardingIndex < onboardingQuestions.length) {
    askCurrentOnboardingQuestion();
    return;
  }

  setBusy(true, "Saving");
  await postJson("/api/onboarding", onboarding);
  setBusy(false);
  phase = "resume";
  setProgress(1);
  sessionTitle.textContent = "Resume Upload";
  chatForm.classList.add("hidden");
  uploadForm.classList.remove("hidden");
  jdText.classList.add("hidden");
  fileInput.classList.remove("hidden");
  fileInput.required = true;
  uploadLabel.textContent = "Upload your resume as PDF, DOCX, or TXT";
  addBotMessage("Great. Now upload your resume so I can extract skills, projects, education, experience, tools, achievements, weak areas, and role fit.", true);
}

async function uploadResume() {
  if (!fileInput.files.length) {
    addMessage("Please choose your resume file first.", "system");
    return;
  }
  const formData = new FormData();
  formData.append("resume", fileInput.files[0]);
  setBusy(true, "Analyzing");
  const response = await fetch("/api/upload-resume", { method: "POST", body: formData });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Resume upload failed");
  setBusy(false);
  const skills = (data.analysis.skills || []).join(", ") || "not clearly detected";
  addBotMessage(`Resume analyzed.\nDetected skills: ${skills}\nRole fit: ${data.analysis.role_fit || data.analysis.summary || "Captured."}`, false);

  phase = "jd";
  setProgress(2);
  sessionTitle.textContent = "Job Description";
  fileInput.value = "";
  fileInput.required = false;
  jdText.classList.remove("hidden");
  uploadLabel.textContent = "Optionally upload a JD file";
  addBotMessage("Paste a job description, upload one, or do both. This helps me compare your resume against the role and generate better questions.", true);
}

async function uploadJobDescription() {
  const formData = new FormData();
  if (fileInput.files.length) formData.append("jd_file", fileInput.files[0]);
  formData.append("jd_text", jdText.value.trim());

  if (!fileInput.files.length && !jdText.value.trim()) {
    addMessage("Please paste or upload a job description.", "system");
    return;
  }

  setBusy(true, "Analyzing");
  const response = await fetch("/api/job-description", { method: "POST", body: formData });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Job description analysis failed");

  const required = (data.analysis.required_skills || []).join(", ") || "not clearly detected";
  const missing = (data.comparison.missing_skills || []).join(", ") || "none obvious";
  addBotMessage(`Job description analyzed.\nRequired skills: ${required}\nMissing or focus skills: ${missing}`, false);
  await designInterview();
}

async function designInterview() {
  setBusy(true, "Designing");
  const interview = await postJson("/api/design-interview");
  setBusy(false);

  phase = "interview";
  setProgress(3);
  sessionTitle.textContent = "Interview Started";
  uploadForm.classList.add("hidden");
  chatForm.classList.remove("hidden");
  textInput.placeholder = "Answer the interview question...";

  const distribution = (interview.plan.question_distribution || []).join("\n- ");
  addBotMessage(`Interview plan ready.\n- ${distribution}\n\nI will ask one question at a time and save your answers. Full feedback comes at the end.`, true);
  currentQuestion = interview.questions[0];
  addBotMessage(`Question 1/${interview.questions.length}:\n${currentQuestion.question}`, true);
}

async function submitInterviewAnswer(answer) {
  setBusy(true, "Saving");
  const data = await postJson("/api/answer", { answer });
  setBusy(false);

  if (data.completed) {
    phase = "report";
    setProgress(4);
    sessionTitle.textContent = "Final Report";
    textInput.placeholder = "Type report to generate final feedback";
    addBotMessage("Interview complete. Type report to generate your final feedback.", true);
    return;
  }

  currentQuestion = data;
  addBotMessage(`Question ${data.question_number}/${data.total_questions}:\n${data.question}`, true);
}

async function showReport() {
  setBusy(true, "Scoring");
  const data = await postJson("/api/report");
  setBusy(false);
  const report = data.report;
  const scores = report.category_scores || {};
  const scoreHtml = Object.entries(scores)
    .map(([label, score]) => `<div class="score-card"><strong>${label}</strong><br>${score}/10</div>`)
    .join("");
  const answerReviews = (report.answer_reviews || [])
    .map(
      (item) => `
        <div class="score-card">
          <strong>Q${item.question_number}: ${escapeHtml(item.category || "Mixed")}</strong><br>
          Score: ${item.score}/10<br>
          ${escapeHtml(item.feedback || "")}
        </div>
      `
    )
    .join("");
  addHtml(`
    <strong>Final Interview Feedback</strong><br>
    Overall Score: <strong>${report.overall_score}/10</strong>
    <div class="report-grid">${scoreHtml}</div>
    <strong>Strengths</strong><br>${formatList(report.strengths)}
    <br><strong>Weaknesses</strong><br>${formatList(report.weaknesses)}
    <br><strong>Improvement Tips</strong><br>${formatList(report.improvement_tips)}
    ${answerReviews ? `<br><strong>Answer Review</strong><div class="report-grid">${answerReviews}</div>` : ""}
    <br><strong>Summary</strong><br>${escapeHtml(report.final_feedback || "")}
  `);
}

function formatList(items = []) {
  return items.map((item) => `- ${escapeHtml(String(item))}`).join("<br>");
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const answer = textInput.value.trim();
  if (!answer) return;
  textInput.value = "";
  addMessage(answer, "user");

  try {
    if (phase === "onboarding") await handleOnboardingAnswer(answer);
    else if (phase === "interview") await submitInterviewAnswer(answer);
    else if (phase === "report") await showReport();
  } catch (error) {
    setBusy(false);
    addMessage(error.message, "system");
  }
});

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    if (phase === "resume") await uploadResume();
    else if (phase === "jd") await uploadJobDescription();
  } catch (error) {
    setBusy(false);
    addMessage(error.message, "system");
  }
});

resetBtn.addEventListener("click", async () => {
  window.speechSynthesis?.cancel();
  await postJson("/api/reset");
  window.location.reload();
});

voiceToggleBtn.addEventListener("click", () => {
  voiceEnabled = !voiceEnabled;
  if (!voiceEnabled) window.speechSynthesis?.cancel();
  configureVoiceControls();
});

replayBtn.addEventListener("click", () => {
  speakText(latestSpeakableText);
});

micBtn.addEventListener("click", () => {
  toggleListening();
});

setProgress(0);
setupRecognition();
configureVoiceControls();
loadLlmStatus().finally(() => {
  addBotMessage("Hi. I’ll create a custom mock interview for you. Let’s start with your profile.", true);
  askCurrentOnboardingQuestion();
});
