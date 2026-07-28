import sys
import os

sys.path.insert(0, os.path.abspath("."))

from agents import ResumeAnalysisAgent

def main():
    print("=" * 60)
    print("DEMO: GENERATING INTERVIEW QUESTIONS")
    print("=" * 60)
    
    agent = ResumeAnalysisAgent()
    
    # 1. Provide sample resume text (No explicit JD / extracted_skills set initially)
    sample_resume = """
    ALEX MORGAN
    Senior Full Stack & AI Engineer
    San Francisco, CA | alex.morgan@email.com
    
    SUMMARY:
    Experienced Software Engineer with 6+ years of expertise in Python, React, TypeScript, FastAPI, PostgreSQL, Docker, PyTorch, and Ollama/LLM integrations. Built high-throughput microservices and AI agents.
    
    WORK EXPERIENCE:
    Lead AI Engineer - TechCorp Solutions (2022 - Present)
    - Designed and deployed RAG pipelines using LangChain, Qdrant, and OpenAI/Ollama LLMs.
    - Optimized database queries in PostgreSQL, reducing query latency by 40%.
    - Built responsive frontend applications using React, Next.js, and Tailwind CSS.
    
    Full Stack Developer - Innovate Labs (2018 - 2022)
    - Developed RESTful APIs in Python FastAPI and Flask.
    - Implemented CI/CD pipelines with GitHub Actions and Docker containers.
    
    SKILLS:
    Python, React, TypeScript, FastAPI, Docker, PyTorch, PostgreSQL, RAG, Machine Learning, Git
    """
    
    print("\n[Step 1] Loading candidate resume into ResumeAnalysisAgent...")
    agent.resume_text = sample_resume
    
    # Simulate resume analysis result
    agent.analysis_result = {
        "overall_score": 88,
        "strengths": ["Python", "React", "FastAPI", "Docker", "PyTorch"],
        "missing_skills": ["Kubernetes", "GraphQL"]
    }
    
    print(f"Candidate Resume Loaded ({len(sample_resume)} characters).")
    print(f"Extracted Strengths: {', '.join(agent.analysis_result['strengths'])}")
    
    print("\n[Step 2] Generating Interview Questions...")
    question_types = ["Basic", "Technical", "Coding", "Scenario"]
    difficulty = "Medium"
    num_questions = 4
    
    print(f"Request Parameters:")
    print(f"  - Question Types: {question_types}")
    print(f"  - Difficulty: {difficulty}")
    print(f"  - Count: {num_questions}")
    print("-" * 60)
    
    try:
        questions = agent.generate_interview_questions(question_types, difficulty, num_questions)
        
        if not questions:
            print("\n❌ Output: No questions were generated (Empty list returned).")
        else:
            print(f"\n✅ SUCCESS! Generated {len(questions)} Interview Questions:\n")
            for idx, (q_type, q_text) in enumerate(questions, 1):
                print(f"Question {idx} [{q_type}]:")
                print(f"  {q_text}\n")
    except Exception as e:
        print(f"\n❌ Error calling generate_interview_questions: {e}")

if __name__ == "__main__":
    main()
