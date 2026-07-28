import re
import PyPDF2
import io
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import tempfile
import os
import json
import ollama

class ResumeAnalysisAgent:
    def __init__(self, model_name='llama3'):
        self.model_name = model_name
        self.cutoff_score = 75
        self.resume_text = None
        self.resume_embeddings = None
        self.analysis_result = None
        self.jd_text = None
        self.extracted_skills = None
        self.resume_weaknesses = []
        self.resume_strengths = []
        self.improvement_suggestions = {}

    def extract_text_from_pdf(self, pdf_file):
        try:
            if hasattr(pdf_file, 'getvalue'):
                pdf_data = pdf_file.getvalue()
                pdf_file_like = io.BytesIO(pdf_data)
                reader = PyPDF2.PdfReader(pdf_file_like)
            else:
                reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return ""

    def extract_text_from_txt(self, txt_file ):
        try:
            if hasattr(txt_file, 'getvalue'):
                return txt_file.getvalue().decode('utf-8')
            else:
                with open(txt_file, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            print(f"Error extracting text from text file: {e}")
            return ""

    def extract_text_from_file(self, file):
        if hasattr(file, 'name'):
            file_extension = file.name.split('.')[-1].lower()
        else:
            file_extension = file.split('.')[-1].lower()
        if file_extension == 'pdf':
            return self.extract_text_from_pdf(file)
        elif file_extension == 'txt':
            return self.extract_text_from_txt(file)
        else:
            print(f"Unsupported file extension: {file_extension}")
            return ""

    def embed_text(self, text):
        # Use a simple local embedding: mean of word ordinals (for demo; replace with better if needed)
        words = text.split()
        if not words:
            return np.zeros(300)
        arr = np.zeros(300)
        for i, word in enumerate(words):
            arr[i % 300] += sum(ord(c) for c in word)
        return arr / len(words)

    def embed_texts(self, texts):
        return np.array([self.embed_text(t) for t in texts])

    def create_resume_embeddings(self, text, chunk_size=1000, chunk_overlap=200):
        # Split text into chunks
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])
            start += chunk_size - chunk_overlap
        embeddings = self.embed_texts(chunks)
        return chunks, embeddings

    def semantic_search(self, query, chunks, embeddings, top_k=3):
        query_emb = self.embed_text(query)
        similarities = np.dot(embeddings, query_emb) / (np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_emb) + 1e-8)
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        return [chunks[i] for i in top_indices]

    def analyze_skill(self, resume_chunks, resume_embeddings, skill):
        query = f"On a scale of 0-10, how clearly does the candidate mention proficiency in {skill}? Provide a numeric rating first, followed by reasoning."
        # Find relevant chunks
        relevant_chunks = self.semantic_search(query, resume_chunks, resume_embeddings, top_k=2)
        context = "\n".join(relevant_chunks)
        prompt = f"{context}\n\n{query}"
        response = ollama.chat(model=self.model_name, messages=[{"role": "user", "content": prompt}])
        text = response['message']['content'].strip()
        match = re.search(r"(\d{1,2})", text)
        score = int(match.group(1)) if match else 0
        reasoning = text.split('.', 1)[1].strip() if '.' in text and len(text.split('.')) > 1 else ""
        return skill, min(score, 10), reasoning

    def analyze_resume_weaknesses(self):
        if not self.resume_text or not self.extracted_skills or not self.analysis_result:
            return []
        
        missing_skills = self.analysis_result.get("missing_skills", [])
        if not missing_skills:
            return []

        weaknesses = []
        # Batch analysis for missing skills
        skills_str = ", ".join(missing_skills)
        prompt = f'''Analyze the weaknesses in the resume relative to these missing or weak skills: {skills_str}.
        
        For each skill, provide:
        1. A concise description of what's missing (1-2 sentences).
        2. 2-3 specific improvement suggestions.
        3. A specific bullet point (example_addition) to add.

        Resume Content:
        {self.resume_text[:3000]}...

        Provide your response in this JSON format (a list of objects):
        [
          {{
            "skill": "skill_name",
            "weakness": "description",
            "improvement_suggestions": ["suggestion1", "suggestion2"],
            "example_addition": "bullet point"
          }}
        ]
        Return only valid JSON, no other text.'''

        try:
            response = ollama.chat(model=self.model_name, messages=[{"role": "user", "content": prompt}])
            weakness_content = response['message']['content'].strip()
            # Handle potential markdown formatting
            if "```json" in weakness_content:
                weakness_content = weakness_content.split("```json")[1].split("```")[0].strip()
            elif "```" in weakness_content:
                weakness_content = weakness_content.split("```")[1].split("```")[0].strip()
                
            weakness_list = json.loads(weakness_content)
            for item in weakness_list:
                skill_name = item.get("skill")
                weakness_detail = {
                    "skill": skill_name,
                    "score": self.analysis_result.get("skill_scores", {}).get(skill_name, 0),
                    "detail": item.get("weakness", "No specific details provided."),
                    "suggestions": item.get("improvement_suggestions", []),
                    "example": item.get("example_addition", "")
                }
                weaknesses.append(weakness_detail)
                self.improvement_suggestions[skill_name] = {
                    "suggestions": item.get("improvement_suggestions", []),
                    "example": item.get("example_addition", "")
                }
        except Exception as e:
            print(f"Error in batched weakness analysis: {e}")
            # Fallback for at least one skill if batching fails
            for skill in missing_skills[:1]: # Limit fallback to save time
                 weaknesses.append({"skill": skill, "score": 0, "detail": "Analysis failed or timed out."})

        self.resume_weaknesses = weaknesses
        return weaknesses

    def extract_skills_from_jd(self, jd_text):
        try:
            prompt = f""" 
Extract a comprehensive list of technical skills, technologies, and competencies required from this job description.
Format the output as a Python list of strings. Only include the list, nothing else.

Job Description:
{jd_text} """
            response = ollama.chat(model=self.model_name, messages=[{"role": "user", "content": prompt}])
            skills_text = response['message']['content']
            match = re.search(r'\[(.*?)\]', skills_text, re.DOTALL)
            if match:
                skills_text = match.group(0)
                skills_list = eval(skills_text)
                if isinstance(skills_list, list):
                    return skills_list
            skills = []
            for line in skills_text.split('\n'):
                line = line.strip()
                if line.startswith('-') or line.startswith('*'):
                    skill = line[2:].strip()
                    if skill:
                        skills.append(skill)
            return skills
        except Exception as e:
            print(f"Error extracting skills from job description: {e}")
            return []

    def semantic_skill_analysis(self, resume_text, skills):
        resume_chunks, resume_embeddings = self.create_resume_embeddings(resume_text)
        skill_scores = {}
        skill_reasoning = {}
        missing_skills = []
        total_score = 0
        
        # Batch analysis to avoid multiple sequential LLM calls
        skills_str = ", ".join(skills)
        prompt = f"""
        Analyze the candidate's proficiency in the following skills based on their resume.
        Skills to evaluate: {skills_str}

        Resume Chunks:
        {chr(10).join(resume_chunks[:5])} ... (truncated)

        For each skill, provide a score from 0 to 10 and a brief reasoning.
        Return the result ONLY as a JSON object where keys are skill names and values are objects with "score" and "reasoning".
        Example: {{"Python": {{"score": 9, "reasoning": "Extensive experience..."}}}}
        """
        
        try:
            response = ollama.chat(model=self.model_name, messages=[{"role": "user", "content": prompt}])
            content = response['message']['content'].strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            batch_results = json.loads(content)
            
            for skill in skills:
                res = batch_results.get(skill, {"score": 0, "reasoning": "Not found in resume."})
                score = min(int(res.get("score", 0)), 10)
                reasoning = res.get("reasoning", "")
                
                skill_scores[skill] = score
                skill_reasoning[skill] = reasoning
                total_score += score
                if score <= 5:
                    missing_skills.append(skill)
                    
        except Exception as e:
            print(f"Error in batched skill analysis: {e}")
            # Fallback to zeros
            for skill in skills:
                skill_scores[skill] = 0
                skill_reasoning[skill] = "Error in analysis."
                missing_skills.append(skill)
        overall_score = int((total_score / (10 * len(skills))) * 100)
        selected = overall_score >= self.cutoff_score
        reasoning = "Candidate evaluated based on explicit resume content using semantic similarity and clear numeric scoring."
        strengths = [skill for skill, score in skill_scores.items() if score >= 7]
        improvement_areas = missing_skills if not selected else []
        self.resume_strengths = strengths
        self.resume_embeddings = (resume_chunks, resume_embeddings)
        return {
            "overall_score": overall_score,
            "skill_scores": skill_scores,
            "skill_reasoning": skill_reasoning,
            "selected": selected,
            "reasoning": reasoning,
            "missing_skills": missing_skills,
            "strengths": strengths,
            "improvement_areas": improvement_areas
        }

    def analyze_resume(self, resume_file, role_requirements=None, custom_jd=None):
        self.resume_text = self.extract_text_from_file(resume_file)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w', encoding='utf-8') as tmp:
            tmp.write(self.resume_text)
            self.resume_file_path = tmp.name
            resume_file_ref = tmp
        
        # Close explicitly to be safe on Windows
        resume_file_ref.close()
        self.resume_embeddings = self.create_resume_embeddings(self.resume_text)
        if custom_jd:
            self.jd_text = self.extract_text_from_file(custom_jd)
            self.extracted_skills = self.extract_skills_from_jd(self.jd_text)
            self.analysis_result = self.semantic_skill_analysis(self.resume_text, self.extracted_skills)
        elif role_requirements:
            self.extracted_skills = role_requirements
            self.analysis_result = self.semantic_skill_analysis(self.resume_text, role_requirements)
        if self.analysis_result and "missing_skills" in self.analysis_result and self.analysis_result["missing_skills"]:
            self.analyze_resume_weaknesses()
        self.analysis_result["detailed_weaknesses"] = self.resume_weaknesses
        return self.analysis_result

    def ask_question(self, question):
        if not self.resume_embeddings or not self.resume_text:
            return "Please analyze a resume first."
        resume_chunks, resume_embeddings = self.resume_embeddings
        relevant_chunks = self.semantic_search(question, resume_chunks, resume_embeddings, top_k=3)
        context = "\n".join(relevant_chunks)
        prompt = f"{context}\n\nQuestion: {question}"
        response = ollama.chat(model=self.model_name, messages=[{"role": "user", "content": prompt}])
        return response['message']['content'].strip()

    def generate_interview_questions(self, question_types, difficulty, num_questions):
        """Generate interview questions based on the resume"""
        if not self.resume_text:
            print("Error: No resume text available for generating interview questions.")
            return []

        try:
            # Fallback for extracted_skills if empty or None
            skills_list = self.extracted_skills or []
            if not skills_list and self.analysis_result:
                skills_list = self.analysis_result.get('strengths', []) + self.analysis_result.get('missing_skills', [])

            strengths = self.analysis_result.get('strengths', []) if self.analysis_result else []
            missing_skills = self.analysis_result.get('missing_skills', []) if self.analysis_result else []

            skills_str = ", ".join(skills_list) if skills_list else "General technical skills from resume"
            strengths_str = ", ".join(strengths) if strengths else "Candidate qualifications"
            missing_str = ", ".join(missing_skills) if missing_skills else "N/A"

            context = (
                f"Resume Content (sample):\n{self.resume_text[:2000]}...\n"
                f"Skills to focus on: {skills_str}\n"
                f"Strengths: {strengths_str}\n"
                f"Areas for improvement: {missing_str}"
            )

            prompt = (
                f"Generate {num_questions} personalized {difficulty.lower()} level interview questions for this candidate "
                f"based on their resume and skills. Include only the following question types: {', '.join(question_types)}.\n"
                f"For each question:\n"
                f"1. Make the question specific to their background and skills.\n"
                f"2. For coding questions, include a clear problem statement.\n"
                f"{context}\n\n"
                f"Format the output strictly as a JSON array of objects. Each object must have 'type' and 'question' keys.\n"
                f"Example format:\n"
                f"[\n"
                f"  {{\"type\": \"{question_types[0] if question_types else 'Technical'}\", \"question\": \"Describe how you implemented...\"}}\n"
                f"]\n"
                f"Return ONLY valid JSON."
            )

            response = ollama.chat(model=self.model_name, messages=[{"role": "user", "content": prompt}])
            questions_text = response['message']['content'].strip()

            questions = []

            # 1. Try parsing JSON
            json_text = questions_text
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0].strip()
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0].strip()

            try:
                parsed_json = json.loads(json_text)
                if isinstance(parsed_json, list):
                    for item in parsed_json:
                        if isinstance(item, dict) and "type" in item and "question" in item:
                            q_type = str(item["type"])
                            q_text = str(item["question"])
                            matched_type = next((t for t in question_types if t.lower() in q_type.lower()), question_types[0] if question_types else q_type)
                            questions.append((matched_type, q_text))
            except Exception:
                pass

            # 2. Fallback regex tuple parsing
            if not questions:
                pattern = r'\("([^"]+)",\s*"([^"]+)"\)'
                matches = re.findall(pattern, questions_text, re.DOTALL)
                for match in matches:
                    q_type, q_text = match
                    matched_type = next((t for t in question_types if t.lower() in q_type.lower()), question_types[0] if question_types else q_type)
                    questions.append((matched_type, q_text))

            # 3. Robust line-by-line fallback parsing
            if not questions:
                lines = questions_text.split('\n')
                current_type = None
                current_question = []

                for line in lines:
                    line_clean = line.strip()
                    if not line_clean:
                        continue
                    
                    matched_t = next((t for t in question_types if t.lower() in line_clean.lower()), None)
                    is_header = matched_t and (
                        ":" in line_clean[:30] or 
                        any(line_clean.lower().startswith(prefix) for prefix in [matched_t.lower(), f"**{matched_t.lower()}", f"[{matched_t.lower()}"]) or
                        re.match(r'^\d+[\.\)]', line_clean)
                    )

                    if is_header or (matched_t and not current_type):
                        if current_type and current_question:
                            questions.append((current_type, " ".join(current_question)))
                            current_question = []
                        current_type = matched_t if matched_t else (question_types[0] if question_types else "General")
                        
                        if ":" in line_clean:
                            after_colon = line_clean.split(":", 1)[1].strip()
                            if after_colon:
                                current_question.append(after_colon)
                        else:
                            clean_text = re.sub(r'^\d+[\.\)]\s*', '', line_clean)
                            clean_text = re.sub(r'^\*\*\s*', '', clean_text)
                            current_question.append(clean_text)
                    elif current_type:
                        current_question.append(line_clean)

                if current_type and current_question:
                    questions.append((current_type, " ".join(current_question)))

            questions = questions[:num_questions]
            return questions

        except Exception as e:
            print(f"Error generating interview questions: {e}")
            return []

    def improve_resume(self, improvement_areas, target_role=""):
        """Improve resume content in specific areas"""
        if not self.resume_text:
            return {}

        try:
            improvements = {}

            # Handle "Skills Highlighting" locally
            if "Skills Highlighting" in improvement_areas and self.resume_weaknesses:
                skill_improvements = {
                    "description": "Your resume needs to better highlight key skills that are important for the role.",
                    "specific": [],
                }
                before_after_examples = {}

                for weakness in self.resume_weaknesses:
                    skill_name = weakness.get("skill", "")
                    if "suggestions" in weakness and weakness["suggestions"]:
                        for suggestion in weakness["suggestions"]:
                            skill_improvements["specific"].append(f"**{skill_name}**: {suggestion}")

                    if "example" in weakness and weakness["example"]:
                        resume_chunks = self.resume_text.split('\n\n')
                        relevant_chunk = ""
                        for chunk in resume_chunks:
                            if skill_name.lower() in chunk.lower() or "experience" in chunk.lower():
                                relevant_chunk = chunk
                                break
                        if relevant_chunk:
                            before_after_examples = {
                                "before": relevant_chunk.strip(),
                                "after": relevant_chunk.strip() + "\n" + weakness["example"]
                            }
                            skill_improvements["before_after"] = before_after_examples

                improvements["Skills Highlighting"] = skill_improvements

            remaining_areas = [area for area in improvement_areas if area not in improvements]

            if remaining_areas:
                weaknesses_text = ""
                if self.resume_weaknesses:
                    weaknesses_text = "Resume Weaknesses:\n"
                    for i, weakness in enumerate(self.resume_weaknesses):
                        weaknesses_text += f"{i + 1}. {weakness['skill']}: {weakness['detail']}\n"
                        if "suggestions" in weakness:
                            for sugg in weakness["suggestions"]:
                                weaknesses_text += f"  - {sugg}\n"

                context = (
                    f"Resume Content:\n{self.resume_text}\n"
                    f"Skills to focus on: {', '.join(self.extracted_skills)}\n"
                    f"Strengths: {', '.join(self.analysis_result.get('strengths', []))}\n"
                    f"Areas for improvement: {', '.join(self.analysis_result.get('missing_skills', []))}\n"
                    f"{weaknesses_text}\n"
                    f"Target role: {target_role if target_role else 'Not specified'}"
                )

                prompt = (
                    f"Provide detailed suggestions to improve this resume in the following areas: {', '.join(remaining_areas)}.\n"
                    f"{context}\n\n"
                    f"For each improvement area, provide:\n"
                    f"1. A general description of what needs improvement\n"
                    f"2. 3-5 specific actionable suggestions\n"
                    f"3. Where relevant, provide a before/after example\n"
                    f"Format the response as a JSON object with improvement areas as keys, each containing:\n"
                    f"  \"description\": general description\n"
                    f"  \"specific\": list of specific suggestions\n"
                    f"  \"before_after\": (where applicable) a dict with \"before\" and \"after\" examples\n"
                    f"Only include the requested improvement areas that aren't already covered.\n"
                    f"Focus particularly on addressing the resume weaknesses."
                )

                response = ollama.chat(model=self.model_name, messages=[{"role": "user", "content": prompt}])

                ai_improvements = {}
                json_match = re.search(r'```json\s*([\s\S]+?)\s*```', response['message']['content'])
                if json_match:
                    try:
                        ai_improvements = json.loads(json_match.group(1))
                        improvements.update(ai_improvements)
                    except json.JSONDecodeError:
                        pass

                if not ai_improvements:
                    # Fallback manual parsing
                    sections = response['message']['content'].split("##")
                    for section in sections:
                        if not section.strip():
                            continue
                        lines = section.strip().split("\n")
                        area = lines[0].strip() if lines else None
                        if area:
                            improvements[area] = {"description": "", "specific": []}
                            for line in lines[1:]:
                                if line.strip().startswith("-"):
                                    improvements[area]["specific"].append(line.strip()[2:])
                                elif not improvements[area]["description"]:
                                    improvements[area]["description"] = line.strip()

            for area in improvement_areas:
                if area not in improvements:
                    improvements[area] = {
                        "description": f"Improvements needed in {area}",
                        "specific": ["Review and enhance this section"]
                    }

            return improvements

        except Exception as e:
            print(f"Error generating resume improvements: {e}")
            return {area: {"description": "Error generating suggestions", "specific": []} for area in improvement_areas}
        
    def get_improved_resume(self, target_role="", highlight_skills=""):
        """Generate an improved version of the resume optimized for the job description."""
        if not self.resume_text:
            return "Please upload and analyze a resume first."
        try:
            # Parse highlight skills if provided
            skills_to_highlight = []
            if highlight_skills:
                if len(highlight_skills) > 100:
                    # Assume it's a JD text, extract skills
                    self.jd_text = highlight_skills
                    try:
                        parsed_skills = self.extract_skills_from_jd(highlight_skills)
                        if parsed_skills:
                            skills_to_highlight = parsed_skills
                        else:
                            skills_to_highlight = [s.strip() for s in highlight_skills.split(",") if s.strip()]
                    except Exception:
                        skills_to_highlight = [s.strip() for s in highlight_skills.split(",") if s.strip()]
                else:
                    skills_to_highlight = [s.strip() for s in highlight_skills.split(",") if s.strip()]
            else:
                if self.analysis_result:
                    skills_to_highlight = self.analysis_result.get('missing_skills', [])
                    skills_to_highlight.extend([
                        skill for skill in self.analysis_result.get('strengths', [])
                        if skill not in skills_to_highlight
                    ])
            if self.extracted_skills:
                skills_to_highlight.extend([
                    skill for skill in self.extracted_skills
                    if skill not in skills_to_highlight
                ])

            # Construct weakness context
            weakness_context = ""
            improvement_examples = ""
            if self.resume_weaknesses:
                weakness_context = "Address these specific weaknesses:\n"
                for weakness in self.resume_weaknesses:
                    skill_name = weakness.get('skill', '')
                    weakness_context += f"- {skill_name}: {weakness.get('detail', '')}\n"
                    if 'suggestions' in weakness and weakness['suggestions']:
                        weakness_context += "  Suggested improvements:\n"
                        for suggestion in weakness['suggestions']:
                            weakness_context += f"    * {suggestion}\n"
                    if 'example' in weakness and weakness['example']:
                        improvement_examples += f"For {skill_name}:\n{weakness['example']}\n\n"

            # Build job description or target role context
            jd_context = ""
            if self.jd_text:
                jd_context = f"Job Description:\n{self.jd_text}\n\n"
            elif target_role:
                jd_context = f"Target Role: {target_role}\n\n"

            prompt = f"""
    Rewrite and improve this resume to make it highly optimized for the target job.
    {jd_context}
    Original Resume:
    {self.resume_text}

    Skills to highlight (in order of priority): {', '.join(skills_to_highlight)}

    {weakness_context}
    Here are specific examples of content to add:
    {improvement_examples}
    Please improve the resume by:
    1. Adding strong, quantifiable achievements
    2. Highlighting the specified skills strategically for ATS scanning
    3. Addressing all the weakness areas identified with the specific suggestions provided
    4. Incorporating the example improvements provided above
    5. Structuring information in a clear, professional format
    6. Using industry-standard terminology
    7. Ensuring all relevant experience is properly emphasized
    8. Adding measurable outcomes and achievements

    Return only the improved resume text without any additional explanations.
    Format the resume in a modern, clean style with clear section headings.
    """

            response = ollama.chat(model=self.model_name, messages=[{"role": "user", "content": prompt}])
            improved_resume = response['message']['content'].strip()

            with tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w', encoding='utf-8') as tmp:
                tmp.write(improved_resume)
                self.improved_resume_path = tmp.name
                improved_resume_file = tmp # Get reference to close later if needed
            
            # Close explicitly to be safe on Windows
            improved_resume_file.close()

            return improved_resume
        except Exception as e:
            print(f"Error generating improved resume: {e}")
            return "Error generating improved resume. Please try again."

    def cleanup(self):
        """Clean up temporary files"""
        try:
            if hasattr(self, 'resume_file_path') and os.path.exists(self.resume_file_path):
                os.unlink(self.resume_file_path)
            if hasattr(self, 'improved_resume_path') and os.path.exists(self.improved_resume_path):
                os.unlink(self.improved_resume_path)
        except Exception as e:
            print(f"Error cleaning up temporary files: {e}")


