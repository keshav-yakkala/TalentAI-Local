# Euron Recruitment Agent

A browser-based recruitment assistant powered by local LLMs (Ollama + Llama 3) and Whisper for audio transcription. Features include resume analysis, Q&A, personalized interview questions, and voice answer evaluation.

## Features
- Resume analysis and improvement suggestions
- Resume Q&A with LLM
- Personalized interview question generation
- Voice answer recording, transcription, and LLM evaluation (yes/no)
- All LLM and transcription runs locally (no external API required)

## Requirements
- Python 3.8+
- [Ollama](https://ollama.com/download) (for Llama 3)
- [Whisper](https://github.com/openai/whisper) (for audio transcription)
- [Streamlit](https://streamlit.io/)
- Other Python dependencies (see `requirements.txt`)

## Setup

1. **Clone the repository**
   ```sh
   git clone <your-repo-url>
   cd recruitment _agent
   ```

2. **Create and activate a virtual environment (optional but recommended)**
   ```sh
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Mac/Linux:
   source venv/bin/activate
   ```

3. **Install Python dependencies**
   ```sh
   pip install -r requirements.txt
   ```

4. **Install and run Ollama**
   - Download and install from [ollama.com/download](https://ollama.com/download)
   - Pull the Llama 3 model:
     ```sh
     ollama pull llama3
     ```
   - Start the Ollama server (in a separate terminal):
     ```sh
     ollama serve
     # or, to run the model directly:
     ollama run llama3
     ```

5. **Install Whisper (if not already installed)**
   ```sh
   pip install openai-whisper
   ```

6. **Run the Streamlit app**
   ```sh
   streamlit run app.py
   ```

7. **Open your browser**
   - Go to [http://localhost:8501](http://localhost:8501)

## Notes
- Make sure Ollama is running before using the app.
- For audio recording, the browser will request microphone access.
- All processing is local; no data is sent to external APIs.

## Troubleshooting
- If you see errors about Ollama connection, ensure the server is running and the model is pulled.
- If audio recording or transcription fails, check your microphone permissions and Whisper installation.

## License
MIT 