# Euron Recruitment Agent: Project Overview

## What is this Project?
Euron Recruitment Agent is a browser-based recruitment assistant that leverages local AI models (Llama 3 via Ollama) and Whisper for audio transcription. It is designed to help job seekers and recruiters analyze resumes, generate personalized interview questions, and evaluate spoken answers—all running locally on your machine, with no external API calls required.

## How is it Useful?
- **For Job Seekers:**
  - Get instant, AI-powered feedback on your resume.
  - Practice answering personalized interview questions and receive feedback on your spoken responses.
  - Identify strengths and areas for improvement in your resume for specific roles.
- **For Recruiters:**
  - Quickly assess candidate resumes for required skills.
  - Generate relevant interview questions based on the candidate’s resume and the job description.
  - Evaluate candidate responses in real time, including voice answers.

## How Does it Work? (Step by Step)
1. **User Uploads Resume:**
   - The user uploads their resume (PDF or TXT) via the web interface.
2. **Role Selection or Custom JD:**
   - The user selects a target job role (e.g., AI/ML Engineer) or provides a custom job description.
3. **Resume Analysis:**
   - The app uses a local LLM (Llama 3 via Ollama) to analyze the resume against the selected role’s requirements or the custom job description.
   - It identifies strengths, missing skills, and provides an overall suitability score.
4. **Resume Q&A:**
   - The user can ask questions about their resume (e.g., "What are my main strengths?") and get AI-generated answers.
5. **Personalized Interview Questions:**
   - The app generates interview questions tailored to the user’s resume and the target role.
6. **Voice Answer Recording & Evaluation:**
   - The user records their spoken answers in the browser.
   - Whisper transcribes the audio, and the LLM evaluates the answer (e.g., yes/no, strengths, improvements).
7. **Resume Improvement Suggestions:**
   - The app suggests specific improvements for the resume, including example bullet points.
8. **Improved Resume Generation:**
   - The app can generate an improved version of the resume, highlighting key skills for the target role.

## Example Scenario
**Amit is applying for an AI/ML Engineer position.**
1. Amit uploads his resume and selects "AI/ML Engineer" as the target role.
2. The app analyzes his resume, scoring his skills (e.g., Python: 9/10, PyTorch: 6/10, MLOps: 4/10), and highlights missing skills.
3. Amit asks, "What are my main weaknesses for this role?" and receives a detailed answer.
4. The app generates 5 personalized interview questions (e.g., "Describe a project where you used deep learning.").
5. Amit records his answer to one question; the app transcribes and evaluates it.
6. The app suggests improvements for his resume, such as adding a bullet point about MLOps experience.
7. Amit downloads the improved resume draft.

## Tech Stack Used
- **Python 3.8+**
- **Streamlit** (web UI)
- **Ollama** (runs Llama 3 locally for LLM tasks)
- **Whisper** (local audio transcription)
- **audiorecorder, pydub** (audio handling)
- **numpy, pandas, matplotlib** (data processing & visualization)
- **PyPDF2** (PDF parsing)

## Local-First, Private by Design
All AI and transcription runs locally—no data is sent to external servers, ensuring privacy and control. 

---

## How Does the Model Extract Keywords/Skills from a Custom Job Description?

When you upload a custom job description (JD), the system uses the local Llama 3 model (via Ollama) to extract relevant skills and keywords. Here’s how it works:

### Step-by-Step Process
1. **Job Description Input:**
   - The user uploads or enters a custom job description.
2. **Prompting the LLM:**
   - The app sends a prompt to the Llama 3 model:
     > Extract a comprehensive list of technical skills, technologies, and competencies required from this job description.\nFormat the output as a Python list of strings. Only include the list, nothing else.\n\nJob Description:\n<your job description here>
3. **LLM Response:**
   - The model returns a Python list of skills (e.g., `["Python", "Machine Learning", "TensorFlow"]`).
   - If the output is not a perfect list, the app tries to extract skills from bullet points or lines starting with `-` or `*`.
4. **Usage:**
   - These extracted skills are then used for resume analysis, interview question generation, and improvement suggestions.

### Example
Suppose you upload this custom JD:
```
We are seeking an AI/ML Engineer with experience in Python, PyTorch, and deploying models to cloud platforms. Familiarity with MLOps, data pipelines, and NLP is a plus.
```
**The LLM will extract:**
```python
["Python", "PyTorch", "Cloud Platforms", "MLOps", "Data Pipelines", "NLP"]
```

### Code Reference
- The function responsible is `extract_skills_from_jd` in `agents.py`.
- It builds the prompt, sends it to the Llama 3 model, and parses the response to get a list of skills.

**In summary:**
The model uses a smart prompt to the local LLM to extract a list of skills/keywords from any job description you provide, making the analysis flexible and tailored to any role. 