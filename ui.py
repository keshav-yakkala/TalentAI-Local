import streamlit as st
import pandas as pd
import base64
import io
import matplotlib.pyplot as plt
from audiorecorder import audiorecorder
import tempfile
import os
import numpy as np
import ollama
import whisper

@st.cache_resource
def load_whisper_model():
    """Load and cache the Whisper model to avoid repeated loading."""
    return whisper.load_model("base")

def setup_page():
    """Apply custom CSS and setup page (without setting page config)"""
    apply_custom_css()

def apply_custom_css(accent_color="#d32f2f"):
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

        :root {{
            --primary: {accent_color};
            --primary-glow: {accent_color}33;
            --bg-deep: #020617;
            --glass-bg: rgba(15, 23, 42, 0.6);
            --glass-border: rgba(255, 255, 255, 0.08);
            --text-main: #f8fafc;
            --text-dim: #94a3b8;
        }}

        * {{
            font-family: 'Plus Jakarta Sans', -apple-system, sans-serif !important;
        }}

        .stApp {{
            background-color: var(--bg-deep) !important;
            background-image: 
                radial-gradient(circle at 0% 0%, {accent_color}15 0%, transparent 50%),
                radial-gradient(circle at 100% 100%, {accent_color}10 0%, transparent 50%),
                radial-gradient(circle at 50% 50%, #000000 0%, transparent 100%) !important;
        }}

        /* Glassmorphism card */
        .card {{
            background: var(--glass-bg);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--glass-border);
            border-radius: 24px;
            padding: 32px;
            margin-bottom: 24px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }}

        .card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(
                90deg,
                transparent,
                rgba(255, 255, 255, 0.03),
                transparent
            );
            transition: 0.5s;
        }}

        .card:hover::before {{
            left: 100%;
        }}

        .card:hover {{
            border-color: {accent_color}4d;
            transform: translateY(-4px);
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.5), 0 0 20px {accent_color}1a;
        }}

        /* Buttons */
        .stButton > button {{
            background: linear-gradient(135deg, {accent_color} 0%, {accent_color}dd 100%) !important;
            color: #fff !important;
            border-radius: 14px !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            padding: 0.75rem 2.5rem !important;
            font-weight: 700 !important;
            font-size: 1rem !important;
            letter-spacing: 0.5px !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: 0 8px 16px {accent_color}22 !important;
            text-transform: uppercase !important;
        }}

        .stButton > button:hover {{
            transform: translateY(-2px) scale(1.02) !important;
            box-shadow: 0 12px 24px {accent_color}44 !important;
            filter: brightness(1.1);
        }}

        .stButton > button:active {{
            transform: translateY(0) scale(0.98) !important;
        }}

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 12px;
            background-color: transparent !important;
            padding: 10px 0 !important;
        }}

        .stTabs [data-baseweb="tab"] {{
            height: auto !important;
            background-color: rgba(255, 255, 255, 0.03) !important;
            border-radius: 12px !important;
            color: var(--text-dim) !important;
            border: 1px solid var(--glass-border) !important;
            padding: 12px 24px !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
        }}

        .stTabs [aria-selected="true"] {{
            background: {accent_color}22 !important;
            color: {accent_color} !important;
            border: 1px solid {accent_color} !important;
            box-shadow: 0 0 15px {accent_color}22 !important;
        }}

        /* Inputs */
        .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {{
            background-color: rgba(15, 23, 42, 0.8) !important;
            border: 1px solid var(--glass-border) !important;
            border-radius: 14px !important;
            color: white !important;
            padding: 12px !important;
            transition: all 0.3s ease !important;
        }}

        .stTextInput input:focus, .stTextArea textarea:focus {{
            border-color: {accent_color} !important;
            box-shadow: 0 0 0 2px {accent_color}33 !important;
            background-color: rgba(15, 23, 42, 1) !important;
        }}

        /* Skill tags */
        .skill-tag {{
            display: inline-flex;
            align-items: center;
            background: rgba(255, 255, 255, 0.05);
            color: {accent_color};
            padding: 8px 18px;
            border-radius: 12px;
            margin: 6px;
            font-size: 0.9rem;
            font-weight: 700;
            border: 1px solid {accent_color}44;
            transition: all 0.3s ease;
        }}

        .skill-tag:hover {{
            background: {accent_color};
            color: white;
            transform: scale(1.05);
            box-shadow: 0 0 15px {accent_color}44;
        }}

        .skill-tag.missing {{
            background: rgba(255, 255, 255, 0.02);
            color: #64748b;
            border-color: var(--glass-border);
        }}

        /* Header styling */
        .main-header {{
            padding: 4rem 0 3rem 0;
            background: radial-gradient(circle at center, {accent_color}08 0%, transparent 70%);
        }}

        h1 {{
            font-weight: 800 !important;
            letter-spacing: -2px !important;
            background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem !important;
        }}

        /* Metrics */
        [data-testid="stMetricValue"] {{
            font-weight: 800 !important;
            color: {accent_color} !important;
            font-size: 2.5rem !important;
        }}

        /* Expander */
        .streamlit-expanderHeader {{
            background-color: rgba(255, 255, 255, 0.03) !important;
            border-radius: 14px !important;
            border: 1px solid var(--glass-border) !important;
            padding: 1rem !important;
            font-weight: 600 !important;
        }}

        /* Horizontal Rule */
        hr {{
            border: none;
            height: 1px;
            background: linear-gradient(to right, transparent, {accent_color}44, transparent);
            margin: 3rem 0;
        }}
        
        .weakness-detail {{
            background: rgba(239, 68, 68, 0.05);
            border-left: 4px solid #ef4444;
            padding: 1.5rem;
            border-radius: 14px;
            margin: 1rem 0;
            color: #fca5a5;
        }}
        
        .solution-detail {{
            background: rgba(34, 197, 94, 0.05);
            border-left: 4px solid #22c55e;
            padding: 1.5rem;
            border-radius: 14px;
            margin: 1rem 0;
            color: #86efac;
        }}
        
        .download-btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: rgba(255, 255, 255, 0.05);
            color: white !important;
            padding: 14px 28px;
            border-radius: 14px;
            text-decoration: none !important;
            margin: 15px 0;
            font-weight: 700;
            border: 1px solid var(--glass-border);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            gap: 12px;
            width: 100%;
        }}

        .download-btn:hover {{
            background: {accent_color}1a;
            border-color: {accent_color};
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
        }}
        
        .stMetric {{
            background: rgba(255, 255, 255, 0.02);
            padding: 24px;
            border-radius: 20px;
            border: 1px solid var(--glass-border);
        }}

        /* Animations */
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        @keyframes pulse-glow {{
            0% {{ box-shadow: 0 0 5px {accent_color}22; }}
            50% {{ box-shadow: 0 0 20px {accent_color}44; }}
            100% {{ box-shadow: 0 0 5px {accent_color}22; }}
        }}

        .card {{
            animation: fadeIn 0.8s cubic-bezier(0.4, 0, 0.2, 1) both;
        }}

        .main-header {{
            animation: fadeIn 1s cubic-bezier(0.4, 0, 0.2, 1) both;
        }}

        .stButton > button {{
            animation: fadeIn 1s cubic-bezier(0.4, 0, 0.2, 1) 0.2s both;
        }}

        /* Custom Scrollbar */
        ::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
        }}
        ::-webkit-scrollbar-track {{
            background: var(--bg-deep);
        }}
        ::-webkit-scrollbar-thumb {{
            background: {accent_color}33;
            border-radius: 10px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: {accent_color}66;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

def display_header():
    try:
        # Try multiple potential logo paths
        logo_path = None
        for path in ["euron.png", "euron.jpg", "logo.png"]:
            if os.path.exists(path):
                logo_path = path
                break
        
        if logo_path:
            with open(logo_path, "rb") as img_file:
                logo_base64 = base64.b64encode(img_file.read()).decode()
            logo_html = f'<img src="data:image/png;base64,{logo_base64}" alt="Euron Logo" style="max-height: 120px; filter: drop-shadow(0 0 10px rgba(211, 47, 47, 0.4));">'
        else:
            logo_html = '<h1 style="font-size: 3rem; margin: 0;">EURON</h1>'
    except Exception as e:
        logo_html = '<div style="font-size: 50px; text-align: center;">EURON</div>'
        
    st.markdown(f"""
    <div class="main-header">
        <div style="display: flex; flex-direction: column; align-items: center; text-align: center;">
            <div class="logo-container" style="margin-bottom: 1.5rem; animation: pulse-glow 3s infinite ease-in-out; border-radius: 50%;">
                {logo_html}
            </div>
            <div class="title-container">
                <h1 style="margin-bottom: 0.5rem;">Euron Recruitment Agent</h1>
                <p style="font-size: 1.2rem; color: #888; font-weight: 500;">AI-Powered Resume Insight & Professional Interview Prep</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def setup_sidebar():
    with st.sidebar:
        st.header("Configuration")
        st.subheader("Theme")
        theme_color = st.color_picker("Accent Color", "#7C3AED")
        st.markdown(f"""
        <style>
        .stButton button, .main-header, .stTabs [aria-selected="true"] {{
            background-color: {theme_color}22 !important;
            color: {theme_color} !important;
            border-color: {theme_color} !important;
        }}
        </style>
        """, unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; margin-top: 20px;">
            <p>Euron Recruitment Agent</p>
            <p style="font-size: 0.8rem; color: #666;">v1.0.0</p>
        </div>
        """, unsafe_allow_html=True)
    return {
        "theme_color": theme_color
    }

def role_selection_section(role_requirements):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    col1, col2 = st.columns([2, 1])
    with col1:
        role = st.selectbox("Select the role you're applying for:", list(role_requirements.keys()))
    with col2:
        upload_jd = st.checkbox("Upload custom job description instead")
        custom_jd = None
        if upload_jd:
            custom_jd_file = st.file_uploader("Upload job description (PDF or TXT)", type=["pdf", "txt"])
            if custom_jd_file:
                st.success("Custom job description uploaded!")
                custom_jd = custom_jd_file
    if not upload_jd:
        st.info(f"Required skills: {', '.join(role_requirements[role])}")
        st.markdown(f"<p>Cutoff Score for selection: <b>75/100</b></p>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    return role, custom_jd

def resume_upload_section():
    st.markdown("""
    <div class="card">
        <h3>Upload Your Resume</h3>
        <p>Supported format: PDF</p>
    </div>
    """, unsafe_allow_html=True)
    uploaded_resume = st.file_uploader("Upload Your Resume", type=["pdf"], label_visibility="collapsed")
    return uploaded_resume

def create_score_pie_chart(score, primary_color="#7C3AED"):
    """Create a professional pie chart for the score visualization"""
    fig, ax = plt.subplots(figsize=(4, 4), facecolor='none')
    # Data
    sizes = [score, 100 - score]
    colors = [primary_color, "rgba(255, 255, 255, 0.05)"]
    
    # Plot
    wedges, texts = ax.pie(
        sizes,
        colors=colors,
        startangle=90,
        wedgeprops={'width': 0.25, 'edgecolor': 'none', 'antialiased': True}
    )
    
    # Equal aspect ratio ensures that pie is drawn as a circle
    ax.set_aspect('equal')
    ax.text(0, 0, f"{score}%", ha='center', va='center', fontsize=32, fontweight='800', color='white')
    
    # Add pass/fail indicator
    status = "QUALIFIED" if score >= 75 else "NOT QUALIFIED"
    status_color = "#22c55e" if score >= 75 else "#ef4444"
    ax.text(0, -0.3, status, ha='center', va='center', fontsize=12, fontweight='700', color=status_color, alpha=0.9)
    return fig


def display_analysis_results(analysis_result, theme_color="#7C3AED"):
    if not analysis_result:
        return

    overall_score = analysis_result.get('overall_score', 0)
    selected = analysis_result.get("selected", False)
    skill_scores = analysis_result.get("skill_scores", {})
    detailed_weaknesses = analysis_result.get("detailed_weaknesses", [])

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div style="text-align: right; font-size: 0.8rem; color: #64748b; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">Analysis Engine v1.0</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1.5])
    with col1:
        fig = create_score_pie_chart(overall_score, theme_color)
        st.pyplot(fig)

    with col2:
        if selected:
            st.markdown(f"<h2 style='color: #22c55e; margin-top: 0;'>🎉 Shortlisted for Interview</h2>", unsafe_allow_html=True)
        else:
            st.markdown(f"<h2 style='color: #ef4444; margin-top: 0;'>❌ Profile Not Shortlisted</h2>", unsafe_allow_html=True)
        
        st.markdown(f"<p style='font-size: 1.1rem; line-height: 1.6; color: #cbd5e1;'>{analysis_result.get('reasoning', '')}</p>", unsafe_allow_html=True)

    st.markdown('<hr>', unsafe_allow_html=True)
    st.markdown('<div class="strengths-improvements">', unsafe_allow_html=True)

    # Strengths
    st.markdown('<div>', unsafe_allow_html=True)
    st.subheader("✅ Strengths")
    strengths = analysis_result.get("strengths", [])
    if strengths:
        for skill in strengths:
            st.markdown(f'<div class="skill-tag">{skill} ({skill_scores.get(skill, "N/A")}/10)</div>', unsafe_allow_html=True)
    else:
        st.write("No notable strengths identified.")
    st.markdown('</div>', unsafe_allow_html=True)

    # Areas for Improvement
    st.markdown('<div>', unsafe_allow_html=True)
    st.subheader("⚠️ Areas for Improvement")
    missing_skills = analysis_result.get("missing_skills", [])
    if missing_skills:
        for skill in missing_skills:
            st.markdown(f'<div class="skill-tag missing">{skill} ({skill_scores.get(skill, "N/A")}/10)</div>', unsafe_allow_html=True)
    else:
        st.write("No significant areas for improvement.")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # Detailed weaknesses section
    if detailed_weaknesses:
        st.markdown('<hr>', unsafe_allow_html=True)
        st.subheader("🧐 Detailed Weakness Analysis")
        for weakness in detailed_weaknesses:
            skill_name = weakness.get('skill', '')
            score = weakness.get('score', 0)
            with st.expander(f"{skill_name} (Score: {score}/10)"):
                detail = weakness.get('detail', 'No specific details provided.')
                if detail.startswith('```json') or '{' in detail:
                    detail = "The resume lacks examples of this skill."
                st.markdown(f'<div class="weakness-detail"><strong>Issue:</strong> {detail}</div>', unsafe_allow_html=True)

                if 'suggestions' in weakness and weakness['suggestions']:
                    st.markdown("<strong>How to improve:</strong>", unsafe_allow_html=True)
                    for i, suggestion in enumerate(weakness['suggestions']):
                        st.markdown(f'<div class="solution-detail">{i + 1}. {suggestion}</div>', unsafe_allow_html=True)

                if 'example' in weakness and weakness['example']:
                    st.markdown("<strong>Example addition:</strong>", unsafe_allow_html=True)
                    st.markdown(f'<div class="example-detail">{weakness["example"]}</div>', unsafe_allow_html=True)
                st.markdown("-")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        strengths = analysis_result.get("strengths", [])
        missing_skills = analysis_result.get("missing_skills", [])

        report_content = f"""
# Euron Recruitment Resume Analysis Report

## Overall Score: {overall_score}/100
Status: {"✓ Shortlisted" if selected else "Not Selected"}

## Analysis Reasoning
{analysis_result.get('reasoning', 'No reasoning provided.')}

## Strengths
{", ".join(strengths if strengths else ["None identified"])}

## Areas for Improvement
{", ".join(missing_skills if missing_skills else ["None identified"])}

## Detailed Weakness Analysis
"""

        for weakness in detailed_weaknesses:
            skill_name = weakness.get('skill', '')
            score = weakness.get('score', 0)
            detail = weakness.get('detail', 'No specific details provided.')
            if detail.startswith('```json') or '{' in detail:
                detail = "The resume lacks examples of this skill."
            report_content += f"\n### {skill_name} (Score: {score}/10)\n"
            report_content += f"Issue: {detail}\n"

            if 'suggestions' in weakness and weakness['suggestions']:
                report_content += "\nImprovement suggestions:\n"
                for i, sugg in enumerate(weakness['suggestions']):
                    report_content += f"{i + 1}. {sugg}\n"

            if 'example' in weakness and weakness['example']:
                report_content += f"\nExample: {weakness['example']}\n"

        report_content += "\n--\nAnalysis provided by Euron Recruitment Agent"

        report_b64 = base64.b64encode(report_content.encode()).decode()
        href = f'<a class="download-btn" href="data:text/plain;base64,{report_b64}" download="euron_resume_analysis.txt">⬇️ Download Analysis Report</a>'
        st.markdown(href, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def resume_qa_section(has_resume, ask_question_func=None):
    if not has_resume:
        st.warning("Please upload and analyze a resume first.")
        return
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Ask Questions About the Resume")

    user_question = st.text_input("Enter your question about the resume:", placeholder="What is the candidate's most recent experience?")

    if user_question and ask_question_func:
        with st.spinner("Searching resume and generating response..."):
            response = ask_question_func(user_question)
        st.markdown(
            '<div style="background-color: #111122; padding: 15px; border-radius: 5px; border-left: 5px solid #d32f2f;">',
            unsafe_allow_html=True,
        )
        st.write(response)
        st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("Example Questions"):
        example_questions = [
            "What is the candidate's most recent role?",
            "How many years of experience does the candidate have with Python?",
            "What educational qualifications does the candidate have?",
            "What are the candidate's key achievements?",
            "Has the candidate managed teams before?",
            "What projects has the candidate worked on?",
            "Does the candidate have experience with cloud technologies?"
        ]
        for question in example_questions:
            if st.button(question, key=f"q_{question}"):
                st.session_state.current_question = question
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


def interview_questions_section(has_resume, generate_questions_func=None):
    if not has_resume:
        st.warning("Please upload and analyze a resume first.")
        return
    st.markdown('<div class="card">', unsafe_allow_html=True)

    # Initialize session state for questions and results
    if 'interview_questions' not in st.session_state:
        st.session_state['interview_questions'] = []
    if 'interview_results' not in st.session_state:
        st.session_state['interview_results'] = {}
    if 'question_params' not in st.session_state:
        st.session_state['question_params'] = {}

    col1, col2 = st.columns(2)

    with col1:
        question_types = st.multiselect(
            "Select question types:",
            ["Basic", "Technical", "Experience", "Scenario", "Coding", "Behavioral"],
            default=["Basic", "Technical"]
        )
    with col2:
        difficulty = st.select_slider(
            "Question difficulty:",
            options=["Easy", "Medium", "Hard"],
            value="Medium"
        )

    num_questions = st.slider("Number of questions:", 3, 15, 5)

    # Store current parameters
    current_params = {
        'types': question_types,
        'difficulty': difficulty,
        'num_questions': num_questions
    }

    # Generate questions if button is clicked
    generate_button = st.button("Generate Interview Questions")
    if generate_button:
        if generate_questions_func:
            with st.spinner("Generating personalized interview questions..."):
                questions = generate_questions_func(question_types, difficulty, num_questions)
                if questions:
                    st.session_state['interview_questions'] = questions
                    st.session_state['question_params'] = current_params
                    st.session_state['interview_results'] = {}  # Reset results for new questions
                else:
                    st.error("Failed to generate interview questions. Please ensure you have uploaded and analyzed a resume first.")

    # Display questions if we have them
    if st.session_state['interview_questions']:
        questions = st.session_state['interview_questions']
        params = st.session_state.get('question_params', current_params)
        
        st.success(f"Generated {len(questions)} interview questions ({params.get('difficulty', difficulty)} level).")
        
        download_content = f"# Euron Recruitment Interview Questions\n\n"
        download_content += f"Difficulty: {params.get('difficulty', difficulty)}\n"
        download_content += f"Types: {', '.join(params.get('types', question_types))}\n\n"

        for i, (q_type, question) in enumerate(questions):
            with st.expander(f"Question {i+1} [{q_type}]: {question[:60]}...", expanded=True):
                st.markdown(f"**Type:** `{q_type}`")
                st.markdown(f"**Question {i+1}:** {question}")
                
                if q_type == "Coding":
                    st.code("# Write your code solution here", language="python")

                col_voice, col_text = st.columns(2)
                
                with col_voice:
                    st.markdown("**Option 1: Voice Answer**")
                    audio_key = f"audio_recorder_{i}"
                    audio = audiorecorder("Click to record", "Click to stop recording", key=audio_key)
                    if audio is not None and len(audio) > 0:
                        audio_bytes = io.BytesIO()
                        audio.export(audio_bytes, format="wav")
                        st.audio(audio_bytes.getvalue(), format='audio/wav')
                                        
                        audio_path = f"answer_q{i+1}.wav"
                        audio.export(audio_path, format="wav")
                        st.success(f"Audio recorded for Q{i+1}.")
                        
                        try:
                            with st.spinner("Transcribing audio answer..."):
                                whisper_model = load_whisper_model()
                                transcription = whisper_model.transcribe(audio_path)
                                transcript = transcription['text']
                                st.markdown(f"**Transcript:** {transcript}")
                                st.session_state['interview_results'][f'transcript_{i}'] = transcript
                        except Exception as e:
                            st.error(f"Transcription error: {e}")
                            transcript = None
                        
                        if transcript:
                            try:
                                with st.spinner("Evaluating answer with AI..."):
                                    prompt = f"Evaluate this candidate's answer for the question: '{question}'\nCandidate Answer: '{transcript}'.\nProvide a rating (Correct/Partially Correct/Incorrect) and a brief 1-2 sentence feedback explanation."
                                    response = ollama.chat(model='llama3', messages=[{"role": "user", "content": prompt}])
                                    eval_text = response['message']['content'].strip()
                                    
                                    st.session_state['interview_results'][f'result_{i}'] = eval_text
                            except Exception as e:
                                st.error(f"LLM evaluation error: {e}")

                with col_text:
                    st.markdown("**Option 2: Written Answer**")
                    text_answer = st.text_area(f"Type your answer for Q{i+1}:", key=f"text_input_{i}", placeholder="Type your answer here...", height=100)
                    submit_text = st.button(f"Evaluate Written Answer Q{i+1}", key=f"submit_text_{i}")

                    if submit_text and text_answer.strip():
                        transcript = text_answer.strip()
                        st.session_state['interview_results'][f'transcript_{i}'] = transcript
                        try:
                            with st.spinner("Evaluating written answer with AI..."):
                                prompt = f"Evaluate this candidate's answer for the question: '{question}'\nCandidate Answer: '{transcript}'.\nProvide a rating (Correct/Partially Correct/Incorrect) and a brief 1-2 sentence feedback explanation."
                                response = ollama.chat(model='llama3', messages=[{"role": "user", "content": prompt}])
                                eval_text = response['message']['content'].strip()
                                st.session_state['interview_results'][f'result_{i}'] = eval_text
                                st.success(f"Answer submitted & evaluated!")
                        except Exception as e:
                            st.error(f"LLM evaluation error: {e}")

                # Show current evaluation results if available
                if f'result_{i}' in st.session_state['interview_results']:
                    st.markdown("---")
                    if f'transcript_{i}' in st.session_state['interview_results']:
                        st.markdown(f"**Submitted Answer:** {st.session_state['interview_results'][f'transcript_{i}']}")
                    st.markdown(f"**AI Evaluation & Feedback:**\n\n{st.session_state['interview_results'][f'result_{i}']}")

            download_content += f"## {i + 1}. [{q_type}] Question\n\n"
            download_content += f"{question}\n\n"
            if q_type == "Coding":
                download_content += "```python\n# Write your solution here\n```\n\n"

        download_content += "\n---\nQuestions generated by Euron Recruitment Agent"

        st.markdown("---")
        questions_bytes = download_content.encode()
        b64 = base64.b64encode(questions_bytes).decode()
        href = f'<a class="download-btn" href="data:text/markdown;base64,{b64}" download="euron_interview_questions.md">Download All Questions (.md)</a>'
        st.markdown(href, unsafe_allow_html=True)
        
        if st.button("Clear Questions"):
            st.session_state['interview_questions'] = []
            st.session_state['interview_results'] = {}
            st.session_state['question_params'] = {}
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)


def resume_improvement_section(has_resume, improve_resume_func=None):
    if not has_resume:
        st.warning("Please upload and analyze a resume first.")
        return
    st.markdown('<div class="card">', unsafe_allow_html=True)

    improvement_areas = st.multiselect(
        "Select areas to improve:",
        ["Content", "Format", "Skills Highlighting", "Experience Description", "Education", "Projects", "Achievements", "Overall Structure"],
        default=["Content", "Skills Highlighting"]
    )
    target_role = st.text_input("Target role (optional):", placeholder="e.g., Senior Data Scientist at Google")

    if st.button("Generate Resume Improvements"):
        if improve_resume_func:
            with st.spinner("Analyzing and generating improvements..."):
                improvements = improve_resume_func(improvement_areas, target_role)

            download_content = f"# Euron Recruitment Resume Improvement Suggestions\n\nTarget Role: {target_role if target_role else 'Not specified'}\n\n"

            for area, suggestions in improvements.items():
                with st.expander(f"Improvements for {area}", expanded=True):
                    st.markdown(f"<p>{suggestions['description']}</p>", unsafe_allow_html=True)
                    st.subheader("Specific Suggestions")
                    for i, suggestion in enumerate(suggestions["specific"]):
                        st.markdown(f'<div class="solution-detail"><strong>{i + 1}.</strong> {suggestion}</div>', unsafe_allow_html=True)

                    if "before_after" in suggestions:
                        st.markdown('<div class="comparison-container">', unsafe_allow_html=True)

                        st.markdown('<div class="comparison-box">', unsafe_allow_html=True)
                        st.markdown("<strong>Before:</strong>", unsafe_allow_html=True)
                        st.markdown(f"<pre>{suggestions['before_after']['before']}</pre>", unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)

                        st.markdown('<div class="comparison-box">', unsafe_allow_html=True)
                        st.markdown("<strong>After:</strong>", unsafe_allow_html=True)
                        st.markdown(f"<pre>{suggestions['before_after']['after']}</pre>", unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)

                        st.markdown('</div>', unsafe_allow_html=True)

                download_content += f"## Improvements for {area}\n\n"
                download_content += f"{suggestions['description']}\n\n"
                download_content += "### Specific Suggestions\n\n"
                for i, suggestion in enumerate(suggestions["specific"]):
                    download_content += f"{i + 1}. {suggestion}\n"
                download_content += "\n"
                if "before_after" in suggestions:
                    download_content += "### Before\n\n"
                    download_content += f"```\n{suggestions['before_after']['before']}\n```\n\n"
                    download_content += "### After\n\n"
                    download_content += f"```\n{suggestions['before_after']['after']}\n```\n\n"

            download_content += "\n--\nProvided by Euron Recruitment Agent"

            st.markdown("---")
            report_bytes = download_content.encode()
            b64 = base64.b64encode(report_bytes).decode()
            href = f'<a class="download-btn" href="data:text/markdown;base64,{b64}" download="euron_resume_improvements.md">Download All Suggestions</a>'
            st.markdown(href, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def improved_resume_section(has_resume, get_improved_resume_func=None):
    if not has_resume:
        st.warning("Please upload and analyze a resume first.")
        return
    st.markdown('<div class="card">', unsafe_allow_html=True)

    target_role = st.text_input("Target role:", placeholder="e.g., Senior Software Engineer")
    highlight_skills = st.text_area("Paste your JD to get updated Resume", placeholder="e.g., Python, React, Cloud Architecture")

    if st.button("Generate Improved Resume"):
        if get_improved_resume_func:
            with st.spinner("Creating improved resume..."):
                improved_resume = get_improved_resume_func(target_role, highlight_skills)

            st.subheader("Improved Resume")
            st.text_area("", improved_resume, height=400)

            col1, col2 = st.columns(2)

            with col1:
                resume_bytes = improved_resume.encode()
                b64 = base64.b64encode(resume_bytes).decode()
                href = f'<a class="download-btn" href="data:file/txt;base64,{b64}" download="euron_improved_resume.txt">Download as TXT</a>'
                st.markdown(href, unsafe_allow_html=True)

            with col2:
                md_content = f"""# {target_role if target_role else 'Professional'} Resume

{improved_resume}

---

Resume enhanced by Euron Recruitment Agent
"""
                md_bytes = md_content.encode()
                md_b64 = base64.b64encode(md_bytes).decode()
                md_href = f'<a class="download-btn" href="data:text/markdown;base64,{md_b64}" download="euron_improved_resume.md">Download as Markdown</a>'
                st.markdown(md_href, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def create_tabs():
    return st.tabs([
        "Resume Analysis",
        "Resume Q&A",
        "Interview Questions",
        "Resume Improvement",
        "Improved Resume"
    ])
