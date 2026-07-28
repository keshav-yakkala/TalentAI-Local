# AI Recruitment Partner - Comprehensive Project Explanation

This document provides an exhaustive, granular breakdown of the "Euron Recruitment Agent" project. It covers the architecture, technical logic, design systems, and a line-by-line analysis of the core files.

---

## 🏗️ Project Architecture

The application follows a modern **RAG (Retrieval-Augmented Generation)** architecture pattern, localized for privacy and performance.

### Logic Flow:
1.  **Ingestion**: The user uploads a PDF resume.
2.  **Extraction**: The system extracts raw text from the PDF.
3.  **Vectorization**: The text is split into chunks and converted into numeric embeddings.
4.  **Retrieval**: When a query (such as a skill analysis) is made, the system identifies the most relevant chunks using Cosine Similarity.
5.  **Generation**: The relevant chunks and the user prompt are sent to **Llama 3 (via Ollama)** to generate a final, fact-based response.
6.  **Interview Loop**: Uses **OpenAI Whisper** to transcribe voice input from the student, which is then evaluated by Llama 3.

---

## 👩‍💻 File-by-File & Deep Dive Logic

### 1. `app.py` (The Orchestrator)
This file serves as the main controller, connecting the UI with the AI Agents.

| Lines | Description |
| :--- | :--- |
| **1-12** | **Imports & Config**: Standard Streamlit setup. The `atexit` module ensures that temporary files created during analysis are deleted when the application is closed. |
| **14-38** | **Knowledge Base**: `ROLE_REQUIREMENTS` defines the benchmarks for different job roles. This serves as the "Ground Truth" when comparing a resume to a specific position. |
| **41-48** | **State Management**: Since Streamlit reruns the script on every interaction, `st.session_state` is used to persist the AI Agent and analysis results in memory. |
| **50-54** | **`setup_agent()`**: Implements lazy-loading for the `ResumeAnalysisAgent`, initializing the object only if it does not already exist. |
| **57-73** | **`analyze_resume()`**: Executes the analysis process within a loading spinner. It passes the uploaded file and role requirements to the agent, handling errors gracefully with `st.error`. |
| **76-83** | **`ask_question()`**: Manages the logic for the Q&A tab. It processes text input through the agent's RAG system. |
| **86-94** | **`generate_interview_questions()`**: Retrieves personalized questions based on user-defined parameters such as type, difficulty, and count. |
| **127-194** | **`main()`**: The primary UI loop. It configures the sidebar (`ui.setup_sidebar()`) and initializes five interactive tabs, each containing logic to trigger the functions described above. |

---

### 2. `agents.py` (The AI Logic Engine)
This file contains the core data processing and AI interaction logic.

#### Key Class: `ResumeAnalysisAgent`

*   **`__init__` (Lines 12-22)**: Establishes a connection to the local Ollama instance, defaulting to the `llama3` model.
*   **Text Extraction (Lines 24-62)**: 
    *   Utilizes `PyPDF2.PdfReader` for processing PDF documents.
    *   Handles Streamlit's `UploadedFile` objects by converting them into `BytesIO` streams using `getvalue()`.
*   **The Embedding Algorithm (Lines 64-86)**:
    *   `embed_text`: A mathematical function that transforms a string into a 300-dimensional vector.
    *   `create_resume_embeddings`: Implements a "Chunking" strategy. It iterates through the text with a sliding window (Size: 1000, Overlap: 200) to ensure contextual continuity across chunks.
*   **Semantic Search (Lines 88-92)**:
    *   Calculates the Dot Product between query vectors and chunk vectors to determine mathematical similarity.
    *   Returns the `top_k` most relevant segments of the resume.
*   **Skill Analysis (Lines 94-105)**:
    *   Employs "Single-Shot Prompting" to ask the AI for a numeric proficiency rating (0-10) for a given skill.
    *   Uses a Regex pattern (`r"(\d{1,2})"`) to reliably extract the score from the AI's natural language response.
*   **Weakness Analysis (Lines 107-137)**:
    *   Uses "Structured Output Prompting" to request analysis in a strict **JSON format**, ensuring the UI can display formatted action items consistently.

---

### 3. `ui.py` (The Design System)
This file manages the visual presentation and complex UI components, such as the voice recorder.

#### **The CSS System (Lines 17-310)**:
*   **Glassmorphism**: Utilizes `backdrop-filter: blur(16px)` and semi-transparent `rgba` backgrounds to achieve a premium, modern aesthetic.
*   **Animations**: Implements `@keyframes fadeIn` and `@keyframes pulse-glow` to create a dynamic, engaging user experience.
*   **Sidebar Theme (Lines 344-367)**: Enables real-time customization of the "Accent Color" via `st.color_picker`.

#### **Voice Interview Logic (Lines 640-696)**:
*   Enables users to record their responses via the `audiorecorder` component.
*   Saves the audio as a `.wav` file for processing.
*   **Whisper Transcription**: Invokes `whisper.load_model("base")` to convert the audio recording into text.
*   **Automated Evaluation**: Processes the transcribed text through Llama 3 to determine if the response is relevant and correct based on the specific interview question.

---

### 4. `check_imports.py`
A diagnostic utility that verifies the presence of all required dependencies, providing clear feedback if any components are missing.

---

## 🛠️ Commands & Setup

### 1. Environment Setup
```powershell
# Create a virtual environment (Optional but Recommended)
python -m venv venv
.\venv\Scripts\activate

# Install all necessary dependencies
pip install -r requirements.txt
```

### 2. Local AI Engine (Ollama)
The project utilizes Ollama for localized, private AI processing.
1. Download and install Ollama from [ollama.com](https://ollama.com).
2. Open your terminal and run the following command:
   ```bash
   ollama pull llama3
   ```

### 3. Running the Application
```bash
streamlit run app.py
```

---

## 🚀 Performance Optimizations (Latest Updates)

Based on user feedback regarding execution time, several critical optimizations were implemented:

1.  **Batched LLM Analysis**: Replaced sequential calls for each skill with **Batched JSON Prompting**. Instead of 20 separate calls, the agent now sends one comprehensive request, reducing analysis time by ~80%.
2.  **Whisper Model Caching**: Used `@st.cache_resource` to keep the OpenAI Whisper model in memory. Previously, the model was reloaded for every audio transcription, which was the primary cause of slowness in the Interview Prep section.
3.  **UI State Persistence**: Optimized session state handling to prevent redundant re-renders of heavy components.
