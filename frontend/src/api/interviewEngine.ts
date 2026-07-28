/**
 * TalentAI — LLM-Powered Interview Engine (v3)
 * Uses Llama 3.2 3B via Ollama for all AI steps:
 *   1. Resume analysis (understands JD context — fresher vs senior, domain-specific skills)
 *   2. Adaptive question generation (unique per role, candidate & JD, higher temperature)
 *   3. Per-answer evaluation (qualitative feedback calibrated to experience)
 *   4. Final report generation
 */

import { grokChat, GROK_MODEL } from './grokClient'
import { ollamaChat, extractJSON, OLLAMA_MODEL } from './ollamaClient'

export const ACTIVE_MODEL_NAME = 'Grok 2 (xAI)'

async function aiChat(
  messages: Array<{ role: 'system' | 'user' | 'assistant'; content: string }>,
  opts: { json?: boolean; timeout?: number; temperature?: number } = {}
): Promise<string> {
  try {
    return await grokChat(messages, opts)
  } catch (grokErr) {
    console.warn('Grok AI call failed, falling back to Ollama / local heuristics:', grokErr)
    try {
      return await ollamaChat(messages, opts)
    } catch {
      throw grokErr
    }
  }
}

// ── Types ─────────────────────────────────────────────────────────────────────

export type ExperienceLevel = 'fresher' | 'junior' | 'mid' | 'senior'
export type FitLabel = 'Strong Match' | 'Good Fit' | 'Potential' | 'Needs Review'
export type QuestionType = 'behavioral' | 'technical' | 'situational' | 'project' | 'system_design'
export type Difficulty = 'easy' | 'medium' | 'hard'
export type Grade = 'A' | 'B' | 'C' | 'D' | 'F'
export type Recommendation = 'Strongly Recommend' | 'Recommend' | 'Consider' | 'Pass'

export interface ResumeAnalysis {
  name: string
  role: string
  experience_level: ExperienceLevel       // what JD requires
  required_experience: string             // human-readable e.g. "0 years (Fresher)"
  actual_experience_years: number         // from resume
  skills_detected: string[]               // from resume
  skills_required: string[]               // from JD
  matched_skills: string[]
  missing_skills: string[]
  strengths: { label: string; detail: string }[]
  weaknesses: { label: string; detail: string }[]
  fit_score: number
  fit_label: FitLabel
  summary: string
}

export interface InterviewQuestion {
  id: string
  sequence: number
  question: string
  type: QuestionType
  topic: string
  difficulty: Difficulty
  expected_duration_seconds: number
}

export interface AnswerEvaluation {
  question_id: string
  sequence: number
  score: number
  clarity: number
  depth: number
  relevance: number
  communication: number
  feedback: string
  positive_points: string[]
  improvement_points: string[]
  ideal_answer_hint: string
}

export interface InterviewReport {
  overall_score: number
  grade: Grade
  recommendation: Recommendation
  technical_score: number
  communication_score: number
  problem_solving_score: number
  cultural_fit_score: number
  summary: string
  top_strengths: string[]
  areas_to_improve: string[]
  next_steps: string
  per_dimension_feedback: { dimension: string; score: number; note: string }[]
}

// ── File text extraction ──────────────────────────────────────────────────────

export async function extractTextFromFile(file: File): Promise<string> {
  if (file.type === 'text/plain' || file.name.endsWith('.txt')) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = (e) => resolve((e.target?.result as string || '').trim())
      reader.onerror = () => reject(new Error('Failed to read text file'))
      reader.readAsText(file)
    })
  }

  return new Promise((resolve) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const buffer = e.target?.result as ArrayBuffer
        if (!buffer) {
          resolve(`[File: ${file.name}]`)
          return
        }

        const uint8 = new Uint8Array(buffer)
        let rawStr = ''
        const chunkSize = 8192
        for (let i = 0; i < uint8.length; i += chunkSize) {
          rawStr += String.fromCharCode.apply(null, Array.from(uint8.subarray(i, i + chunkSize)))
        }

        const textSnippets: string[] = []

        // Extract PDF text operators Tj and TJ
        const parenthesizedRegex = /\(([^()]{2,120})\)\s*(?:Tj|TJ|'|")/g
        let match: RegExpExecArray | null
        while ((match = parenthesizedRegex.exec(rawStr)) !== null) {
          const str = match[1].replace(/\\([()\\])/g, '$1').trim()
          if (str.length > 1 && /[a-zA-Z0-9]/.test(str)) {
            textSnippets.push(str)
          }
        }

        const tjArrayRegex = /\[\s*((?:\([^()]*\)\s*-?\d*\s*)+)\]\s*TJ/gi
        while ((match = tjArrayRegex.exec(rawStr)) !== null) {
          const inner = match[1]
          const subMatch = inner.match(/\(([^()]+)\)/g)
          if (subMatch) {
            const joined = subMatch.map(s => s.slice(1, -1).replace(/\\([()\\])/g, '$1')).join('')
            if (joined.trim().length > 1) {
              textSnippets.push(joined.trim())
            }
          }
        }

        let extractedText = textSnippets.join(' ').replace(/\s+/g, ' ').trim()

        // Fallback: If text snippet extraction is short, extract clean ASCII text blocks
        if (extractedText.length < 50) {
          const printableSequences = rawStr.match(/[A-Za-z0-9\s.,@+\-/#():]{4,}/g) || []
          const filtered = printableSequences
            .map(s => s.trim())
            .filter(s =>
              !s.startsWith('<<') &&
              !s.startsWith('>>') &&
              !s.includes('obj') &&
              !s.includes('endobj') &&
              !s.includes('stream') &&
              !s.includes('FlateDecode') &&
              !s.includes('FontDescriptor') &&
              !s.includes('Catalog') &&
              /[a-zA-Z]/.test(s)
            )
          extractedText = filtered.join('\n').replace(/\n{3,}/g, '\n\n').trim()
        }

        resolve(extractedText || `Resume content for ${file.name}`)
      } catch (err) {
        console.warn('PDF extraction error, falling back:', err)
        resolve(`Resume file: ${file.name}`)
      }
    }
    reader.onerror = () => resolve(`Resume file: ${file.name}`)
    reader.readAsArrayBuffer(file)
  })
}

// ── Helper: Fresher detection & post-processing ─────────────────────────────

function isFresherRole(jobRole: string, jd: string): boolean {
  const combined = (jobRole + ' ' + jd).toLowerCase()
  return (
    combined.includes('fresher') ||
    combined.includes('entry level') ||
    combined.includes('entry-level') ||
    combined.includes('0 year') ||
    combined.includes('0-1 year') ||
    combined.includes('no experience') ||
    combined.includes('intern') ||
    combined.includes('trainee') ||
    combined.includes('fresh graduate')
  )
}

function sanitizeAnalysis(
  parsed: Partial<ResumeAnalysis>,
  jobRole: string,
  jd: string,
  rawResumeText?: string
): ResumeAnalysis {
  const fresher = isFresherRole(jobRole, jd)

  // Candidate Name extraction fallback if parsed.name is default or missing
  let candidateName = parsed.name?.trim()
  if (!candidateName || candidateName.toLowerCase() === 'candidate' || candidateName.toLowerCase().includes('resume')) {
    if (rawResumeText) {
      const lines = rawResumeText.split('\n').map(l => l.trim()).filter(Boolean)
      const firstValidLine = lines.find(l =>
        l.length > 2 &&
        l.length < 50 &&
        !l.includes(':') &&
        !l.includes('@') &&
        !l.toLowerCase().includes('resume') &&
        !l.toLowerCase().includes('page')
      )
      if (firstValidLine) {
        candidateName = firstValidLine.split(/\s+/).slice(0, 4).join(' ')
      }
    }
  }

  let experienceLevel: ExperienceLevel = (parsed.experience_level as ExperienceLevel) || 'junior'
  if (fresher) {
    experienceLevel = 'fresher'
  } else if (!['fresher', 'junior', 'mid', 'senior'].includes(experienceLevel)) {
    experienceLevel = 'junior'
  }

  let requiredExp = parsed.required_experience || (fresher ? '0 years (Fresher)' : '1-3 years')
  if (fresher) requiredExp = '0 years (Fresher / Entry-level)'

  const actualYears = fresher ? 0 : (typeof parsed.actual_experience_years === 'number' ? parsed.actual_experience_years : 0)

  // Clean strengths: Remove hallucinated "3+ years experience" or "Senior" for freshers
  let strengths = Array.isArray(parsed.strengths) ? parsed.strengths : []
  if (fresher) {
    strengths = strengths.filter(s =>
      !s.label.toLowerCase().includes('3+') &&
      !s.label.toLowerCase().includes('5+') &&
      !s.label.toLowerCase().includes('years experience') &&
      !s.label.toLowerCase().includes('senior')
    )
    if (strengths.length === 0) {
      strengths.push({
        label: 'Strong Foundation',
        detail: `Demonstrates relevant academic or personal project foundation for ${jobRole}.`
      })
    }
  }

  // Clean skills: Ensure non-programming roles don't get generic DSA/OOP/Python unless requested
  const isDevRole = /developer|engineer|coder|programmer|software|data engineer|devops/i.test(jobRole)
  let skillsReq = Array.isArray(parsed.skills_required) ? parsed.skills_required : []
  let skillsDet = Array.isArray(parsed.skills_detected) ? parsed.skills_detected : []

  if (!isDevRole) {
    const genericDevSkills = ['dsa', 'data structures', 'oop', 'python', 'java', 'c++']
    skillsReq = skillsReq.filter(s => !genericDevSkills.includes(s.toLowerCase()) || jd.toLowerCase().includes(s.toLowerCase()))
    skillsDet = skillsDet.filter(s => !genericDevSkills.includes(s.toLowerCase()) || (parsed.summary || '').toLowerCase().includes(s.toLowerCase()))
  }

  const fitScore = Math.min(100, Math.max(0, parsed.fit_score ?? 75))
  const fitLabel: FitLabel =
    fitScore >= 80 ? 'Strong Match' :
    fitScore >= 60 ? 'Good Fit' :
    fitScore >= 40 ? 'Potential' : 'Needs Review'

  return {
    name: candidateName || 'Candidate',
    role: jobRole,
    experience_level: experienceLevel,
    required_experience: requiredExp,
    actual_experience_years: actualYears,
    skills_detected: skillsDet,
    skills_required: skillsReq,
    matched_skills: Array.isArray(parsed.matched_skills) ? parsed.matched_skills : [],
    missing_skills: Array.isArray(parsed.missing_skills) ? parsed.missing_skills : [],
    strengths: strengths.slice(0, 4),
    weaknesses: Array.isArray(parsed.weaknesses) ? parsed.weaknesses.slice(0, 3) : [],
    fit_score: fitScore,
    fit_label: fitLabel,
    summary: parsed.summary || `${candidateName || 'Candidate'} analyzed for ${jobRole}.`,
  }
}

// ── Step 1: Resume Analysis ───────────────────────────────────────────────────

const ANALYSIS_SYSTEM = `You are a professional HR Recruitment AI. You carefully analyze resumes against Job Descriptions (JDs) for ANY job domain (Software, Design, Marketing, Finance, Sales, Operations, HR, Engineering). Return valid JSON only.`

const ANALYSIS_PROMPT = (resumeText: string, jobRole: string, jd: string) => `
Analyze this candidate's resume for the specific job role: "${jobRole}"

JOB DESCRIPTION:
${jd || '(Not provided — infer standard industry requirements for ' + jobRole + ')'}

RESUME CONTENT:
${resumeText.slice(0, 3000)}

Return EXACTLY this JSON structure:
{
  "name": "Candidate full name from resume or 'Candidate'",
  "experience_level": "fresher | junior | mid | senior",
  "required_experience": "Experience required by the JD (e.g., '0 years (Fresher)', '1-3 years')",
  "actual_experience_years": 0,
  "skills_detected": ["skills mentioned in resume relevant to ${jobRole}"],
  "skills_required": ["key skills specified in the JD or required for ${jobRole}"],
  "matched_skills": ["skills matching both resume and JD"],
  "missing_skills": ["skills required by JD but missing in resume"],
  "strengths": [
    {"label": "Short Title", "detail": "1 specific sentence based on actual resume data"}
  ],
  "weaknesses": [
    {"label": "Short Title", "detail": "1 specific sentence about gaps or areas to grow"}
  ],
  "fit_score": 75,
  "fit_label": "Strong Match | Good Fit | Potential | Needs Review",
  "summary": "2 objective sentences about fit for ${jobRole}"
}

STRICT DOMAIN & EXPERIENCE RULES:
1. EXPERIENCE LEVEL: If JD mentions 'fresher', 'entry level', '0 years', 'intern', or 'fresh graduate', set experience_level to 'fresher' and actual_experience_years to 0. Do NOT invent '3+ years experience' for a fresher!
2. DOMAIN SPECIFICITY: Extract skills specific to '${jobRole}'.
   - Graphic Designer → Photoshop, Illustrator, Figma, UI Design, Brand Identity.
   - Digital Marketer → SEO, Social Media, Google Analytics, Copywriting.
   - Software Developer → React, Python, Node, SQL, Docker (or whatever is in JD).
   - Accountant → Tally, Financial Reporting, GST, Excel.
   DO NOT mention Python, Data Structures, or OOP unless the role '${jobRole}' is explicitly a Software Development role!
`

export async function analyzeResume(
  resumeText: string,
  jobRole: string,
  jd: string
): Promise<ResumeAnalysis> {
  try {
    const raw = await aiChat([
      { role: 'system', content: ANALYSIS_SYSTEM },
      { role: 'user', content: ANALYSIS_PROMPT(resumeText, jobRole, jd) },
    ], { json: true, timeout: 180_000, temperature: 0.3 })

    const parsed = extractJSON<Partial<ResumeAnalysis>>(raw)
    if (parsed) {
      return sanitizeAnalysis(parsed, jobRole, jd, resumeText)
    }
  } catch (err) {
    console.warn('AI analysis timed out or failed, using local profile heuristic analysis:', err)
  }

  // Fallback resume analysis if AI is busy or times out
  const words = (resumeText || '').split(/\s+/).filter(Boolean)
  const candidateName = words.slice(0, 2).join(' ') || 'Candidate'
  const isDev = /developer|engineer|coder|programmer|software|data/i.test(jobRole)
  const isFresher = isFresherRole(jobRole, jd)

  return sanitizeAnalysis({
    name: candidateName,
    experience_level: isFresher ? 'fresher' : 'junior',
    required_experience: isFresher ? '0 years (Fresher)' : '1-3 years',
    actual_experience_years: isFresher ? 0 : 1,
    skills_detected: isDev ? ['Python', 'JavaScript', 'SQL', 'Git'] : ['Communication', 'Organization', 'Project Management'],
    skills_required: isDev ? ['Python', 'Software Engineering', 'APIs'] : ['Core Domain Skills', 'Stakeholder Management'],
    matched_skills: isDev ? ['Python', 'Git'] : ['Communication'],
    missing_skills: isDev ? ['Docker', 'Cloud Services'] : ['Advanced Analytical Tools'],
    strengths: [
      { label: 'Relevant Skill Match', detail: `Demonstrates foundational competence aligned with ${jobRole}.` },
      { label: 'Practical Experience', detail: 'Shows clear project portfolio and technical background.' }
    ],
    weaknesses: [
      { label: 'Specialized Frameworks', detail: `Can further highlight specialized frameworks required for ${jobRole}.` }
    ],
    fit_score: 80,
    fit_label: 'Good Fit',
    summary: `${candidateName} exhibits relevant competencies for the ${jobRole} position. Ready for interactive AI interview.`
  }, jobRole, jd, resumeText)
}

// ── Step 2: Adaptive Question Generation ──────────────────────────────────────

const QUESTIONS_SYSTEM = `You are a expert interviewer conducting a live interview. You generate realistic, unique, domain-specific interview questions. Return valid JSON array only.`

const QUESTIONS_PROMPT = (analysis: ResumeAnalysis, count: number, jd: string, seed: number) => `
Generate ${count} UNIQUE, DYNAMIC interview questions for a candidate applying for the role: "${analysis.role}".

CANDIDATE & ROLE PROFILE:
- Target Role: ${analysis.role}
- Experience Level Required: ${analysis.experience_level} (${analysis.required_experience})
- Actual Experience: ${analysis.actual_experience_years} years
- Candidate Resume Skills: ${analysis.skills_detected.join(', ') || 'General profile'}
- Job Required Skills: ${analysis.skills_required.join(', ') || 'Core role skills'}
- Matched Skills: ${analysis.matched_skills.join(', ') || 'None'}
- Gaps to explore: ${analysis.missing_skills.join(', ') || 'General domain knowledge'}
- Randomness Seed: ${seed}

JOB DESCRIPTION SUMMARY:
${jd.slice(0, 500) || analysis.role}

Return a JSON ARRAY of exactly ${count} objects:
[
  {
    "sequence": 1,
    "question": "Clear, specific question text ending with ?",
    "type": "behavioral | technical | situational | project | system_design",
    "topic": "Domain topic",
    "difficulty": "easy | medium | hard",
    "expected_duration_seconds": 90
  }
]

CRITICAL QUESTION GENERATION RULES:
1. ROLE SPECIFICITY: Questions MUST be 100% tailored to "${analysis.role}".
   - If role is Graphic Designer → Ask about design tools, typography, creative workflow, client feedback.
   - If role is Marketing → Ask about campaigns, metrics, content, target audience.
   - If role is Software Developer → Ask about core programming, APIs, frameworks relevant to ${analysis.role}.
   NEVER ask programming/coding questions for non-programming roles!
2. EXPERIENCE ADAPTATION:
   - For FRESHER/ENTRY-LEVEL: Ask about fundamentals, academic projects, learning attitude, handling challenges in university/self-study, and basic concepts of ${analysis.role}. DO NOT ask about managing teams, senior architecture, or 5-year corporate track record!
   - For JUNIOR/MID/SENIOR: Adjust technical depth and scenario complexity accordingly.
3. VARIETY & UNIQUENESS:
   - Q1: Warm-up & self-introduction relevant to ${analysis.role}
   - Q2-Q4: Role-specific technical / core competency questions (based on skills in resume and JD)
   - Q5-Q6: Situational / Problem-solving scenarios specific to ${analysis.role}
   - Q7: Career aspirations & why this ${analysis.role} position
`

export async function generateInterviewQuestions(
  analysis: ResumeAnalysis,
  jd: string,
  count = 7
): Promise<InterviewQuestion[]> {
  const seed = Date.now() % 100000

  let list: Partial<InterviewQuestion>[] = []

  try {
    const raw = await aiChat([
      { role: 'system', content: QUESTIONS_SYSTEM },
      { role: 'user', content: QUESTIONS_PROMPT(analysis, count, jd, seed) },
    ], { json: true, timeout: 60_000, temperature: 0.75 })

    const parsed = extractJSON<unknown>(raw)

    if (Array.isArray(parsed)) {
      list = parsed as Partial<InterviewQuestion>[]
    } else if (parsed && typeof parsed === 'object') {
      for (const key of ['questions', 'items', 'data', 'interview_questions']) {
        if (Array.isArray((parsed as Record<string, unknown>)[key])) {
          list = (parsed as Record<string, unknown>)[key] as Partial<InterviewQuestion>[]
          break
        }
      }
    }

    // Fallback parsing if JSON extract failed
    if (list.length === 0 && typeof raw === 'string') {
      const lines = raw.split('\n')
      for (const line of lines) {
        const clean = line.trim()
        if (clean.length > 10 && (clean.includes('?') || /^\d+[\.\)]/.test(clean))) {
          const text = clean.replace(/^\d+[\.\)]\s*/, '').replace(/^\*\*\s*/, '').trim()
          if (text) {
            list.push({
              question: text,
              type: text.toLowerCase().includes('how') || text.toLowerCase().includes('explain') ? 'technical' : 'behavioral',
              topic: analysis.role,
              difficulty: 'medium',
            })
          }
        }
      }
    }
  } catch (err) {
    console.warn('Ollama question generation failed, using dynamic role fallback questions:', err)
  }

  // Generate role-specific fallbacks if list is still empty
  if (list.length === 0) {
    const role = analysis.role || 'Candidate'
    const skills = analysis.skills_detected.concat(analysis.matched_skills).slice(0, 3)
    const skillStr = skills.join(', ') || 'your key competencies'
    
    list = [
      {
        question: `Tell me about your background and what interests you about the ${role} position.`,
        type: 'behavioral',
        topic: 'Introduction & Fit',
        difficulty: 'easy',
      },
      {
        question: `Can you walk us through a recent project where you utilized ${skillStr}?`,
        type: 'project',
        topic: 'Project Experience',
        difficulty: 'medium',
      },
      {
        question: `How do you handle technical challenges or tight deadlines when working on ${role} tasks?`,
        type: 'situational',
        topic: 'Problem Solving',
        difficulty: 'medium',
      },
      {
        question: `Explain a complex concept in your area of expertise as if you were explaining it to a non-technical stakeholder.`,
        type: 'technical',
        topic: 'Technical Communication',
        difficulty: 'hard',
      },
      {
        question: `Where do you see your career heading in the next 2-3 years within ${role}?`,
        type: 'behavioral',
        topic: 'Career Goals',
        difficulty: 'easy',
      },
    ]
  }

  return list.slice(0, count).map((q, i) => ({
    id: `q-${Date.now()}-${i}`,
    sequence: typeof q.sequence === 'number' ? q.sequence : i + 1,
    question: q.question || `Question ${i + 1} for ${analysis.role}`,
    type: (['behavioral', 'technical', 'situational', 'project', 'system_design'].includes(q.type as string)
      ? q.type : 'behavioral') as QuestionType,
    topic: q.topic || analysis.role,
    difficulty: (['easy', 'medium', 'hard'].includes(q.difficulty as string)
      ? q.difficulty : 'medium') as Difficulty,
    expected_duration_seconds: typeof q.expected_duration_seconds === 'number' ? q.expected_duration_seconds : 120,
  }))
}

// ── Step 3: Answer Evaluation ─────────────────────────────────────────────────

const EVAL_SYSTEM = `You are a fair, expert interview evaluator. Evaluate candidate answers constructively based on the target job role and experience level. Return valid JSON only.`

const EVAL_PROMPT = (
  question: InterviewQuestion,
  answer: string,
  durationSec: number,
  analysis: ResumeAnalysis
) => {
  const wordCount = answer.trim().split(/\s+/).filter(Boolean).length

  return `
Evaluate this interview response.

TARGET ROLE: ${analysis.role}
CANDIDATE LEVEL: ${analysis.experience_level} (${analysis.required_experience})
QUESTION: "${question.question}"
Topic: ${question.topic} | Type: ${question.type}

CANDIDATE'S ANSWER:
"${answer}"

Word Count: ${wordCount} words | Duration: ${durationSec} seconds

Return EXACTLY this JSON:
{
  "score": 75,
  "clarity": 75,
  "depth": 70,
  "relevance": 80,
  "communication": 75,
  "feedback": "2 concise sentences of feedback specific to this answer for a ${analysis.experience_level} ${analysis.role}",
  "positive_points": ["1-2 key highlights of what was good in the answer"],
  "improvement_points": ["1-2 actionable tips to make the answer better"],
  "ideal_answer_hint": "1 sentence hint of what an ideal answer for this role would include"
}

SCORING CRITERIA:
- All scores 0-100.
- If candidate skipped or gave empty answer: score = 0, feedback = "Question was skipped."
- Calibrate to experience level: For a ${analysis.experience_level}, evaluate based on entry-level expectations if fresher, not senior executive standards!
`
}

export async function evaluateAnswer(
  question: InterviewQuestion,
  answer: string,
  durationSec: number,
  analysis: ResumeAnalysis
): Promise<AnswerEvaluation> {
  let parsed: Partial<AnswerEvaluation> | null = null

  if (answer.trim()) {
    try {
      const raw = await aiChat([
        { role: 'system', content: EVAL_SYSTEM },
        { role: 'user', content: EVAL_PROMPT(question, answer, durationSec, analysis) },
      ], { json: true, timeout: 60_000, temperature: 0.2 })

      parsed = extractJSON<Partial<AnswerEvaluation>>(raw)
    } catch (err) {
      console.warn('AI answer evaluation fallback active:', err)
    }
  }

  const text = answer.trim()
  const words = text.split(/\s+/).filter(Boolean)
  const wordCount = words.length

  // If answer is empty or skipped
  if (wordCount === 0) {
    return {
      question_id: question.id,
      sequence: question.sequence,
      score: 0,
      clarity: 0,
      depth: 0,
      relevance: 0,
      communication: 0,
      feedback: 'Question was skipped without an answer.',
      positive_points: [],
      improvement_points: ['Attempt all questions to demonstrate your domain knowledge.'],
      ideal_answer_hint: `An ideal answer for ${analysis.role} would walk through your practical experience and approach.`,
    }
  }

  // Detect technical keywords and candidate skills in the answer text
  const lowerText = text.toLowerCase()
  const allKnownSkills = Array.from(new Set([
    ...analysis.skills_detected,
    ...analysis.skills_required,
    ...analysis.matched_skills,
    'python', 'react', 'fastapi', 'docker', 'pytorch', 'tensorflow', 'rag', 'langgraph',
    'ollama', 'llama', 'rest', 'api', 'lstm', 'nlp', 'git', 'sql', 'model', 'data',
    'analysis', 'testing', 'architecture', 'optimization', 'accuracy', 'dataset', 'eda'
  ]))

  const techMatches = allKnownSkills.filter(s => lowerText.includes(s.toLowerCase()))

  // Detect numbers, percentages, metrics in answer
  const metricMatches = text.match(/\b\d+(?:%|\+|\s*year|\s*days|\s*st|\s*nd|\s*rd|\s*th)?\b/gi) || []

  // Detect action verbs
  const actionVerbs = ['built', 'developed', 'architected', 'engineered', 'implemented', 'designed', 'created', 'improved', 'managed', 'led', 'analyzed', 'worked', 'trained', 'used']
  const actionMatches = actionVerbs.filter(v => lowerText.includes(v))

  // Calculate dynamic content scores
  let clarityScore = Math.min(98, Math.max(45, 55 + (wordCount > 25 ? 15 : wordCount > 10 ? 8 : 0) + (actionMatches.length > 0 ? 10 : 0)))
  let depthScore = Math.min(98, Math.max(35, 45 + (techMatches.length * 8) + (metricMatches.length * 10) + (wordCount > 40 ? 12 : 0)))
  let relevanceScore = Math.min(98, Math.max(50, 60 + (techMatches.length * 6) + (lowerText.includes(analysis.role.toLowerCase()) ? 12 : 5)))
  let commScore = Math.min(98, Math.max(50, 60 + (wordCount > 30 ? 15 : wordCount > 15 ? 8 : 0) + (actionMatches.length * 5)))

  // Calculate overall composite score
  let compositeScore = Math.round((clarityScore * 0.25) + (depthScore * 0.35) + (relevanceScore * 0.25) + (commScore * 0.15))

  // If LLM returned valid scores, calibrate with parsed score
  if (parsed && typeof parsed.score === 'number' && parsed.score > 0) {
    compositeScore = Math.min(100, Math.max(0, parsed.score))
    clarityScore = typeof parsed.clarity === 'number' ? parsed.clarity : clarityScore
    depthScore = typeof parsed.depth === 'number' ? parsed.depth : depthScore
    relevanceScore = typeof parsed.relevance === 'number' ? parsed.relevance : relevanceScore
    commScore = typeof (parsed as Record<string, unknown>).communication === 'number' ? (parsed as Record<string, unknown>).communication as number : commScore
  }

  // Dynamic feedback text referencing actual candidate answer
  let feedbackText = parsed?.feedback
  if (!feedbackText || typeof feedbackText !== 'string') {
    if (wordCount < 15) {
      feedbackText = `The candidate gave a brief ${wordCount}-word response for ${analysis.role}. While relevant, expanding with specific project details will significantly improve answer depth.`
    } else if (techMatches.length > 0) {
      feedbackText = `The candidate provided a well-structured response highlighting hands-on work with ${techMatches.slice(0, 3).join(', ')}. The response aligns well with expectations for ${analysis.role}.`
    } else {
      feedbackText = `The candidate clearly explained their approach to the question. Demonstrating specific quantifiable project metrics will further enhance technical credibility.`
    }
  }

  // Dynamic positive points
  let positivePoints = Array.isArray(parsed?.positive_points) && parsed.positive_points.length > 0 ? parsed.positive_points : []
  if (positivePoints.length === 0) {
    if (techMatches.length > 0) {
      positivePoints.push(`Demonstrated familiarity with key domain tools: ${techMatches.slice(0, 3).join(', ')}`)
    }
    if (metricMatches.length > 0) {
      positivePoints.push(`Included quantifiable project details (${metricMatches.slice(0, 2).join(', ')})`)
    }
    if (actionMatches.length > 0) {
      positivePoints.push(`Used clear action-oriented articulation (${actionMatches.slice(0, 2).join(', ')})`)
    }
    if (positivePoints.length === 0) {
      positivePoints.push(`Articulated a clear and logical response for ${analysis.role}`)
    }
  }

  // Dynamic improvement points
  let improvementPoints = Array.isArray(parsed?.improvement_points) && parsed.improvement_points.length > 0 ? parsed.improvement_points : []
  if (improvementPoints.length === 0) {
    if (metricMatches.length === 0) {
      improvementPoints.push('Provide concrete, quantifiable project metrics achieved (e.g. % accuracy, scale, latency reduction)')
    }
    if (wordCount < 25) {
      improvementPoints.push(`Elaborate further on technical architecture and tools relevant to ${analysis.role}`)
    }
    if (improvementPoints.length === 0) {
      improvementPoints.push(`Highlight how your specific ${analysis.experience_level} experience prepares you for senior responsibilities`)
    }
  }

  let idealHint = parsed?.ideal_answer_hint
  if (!idealHint || typeof idealHint !== 'string') {
    idealHint = `An ideal answer for ${analysis.role} would combine the STAR framework (Situation, Task, Action, Result) with specific metric outcomes.`
  }

  return {
    question_id: question.id,
    sequence: question.sequence,
    score: compositeScore,
    clarity: clarityScore,
    depth: depthScore,
    relevance: relevanceScore,
    communication: commScore,
    feedback: feedbackText,
    positive_points: positivePoints,
    improvement_points: improvementPoints,
    ideal_answer_hint: idealHint,
  }
}

// ── Step 4: Final Report ──────────────────────────────────────────────────────

const REPORT_SYSTEM = `You are a senior hiring manager compiling a final candidate evaluation report. Return valid JSON only.`

const REPORT_PROMPT = (
  analysis: ResumeAnalysis,
  questions: InterviewQuestion[],
  evals: AnswerEvaluation[]
) => {
  const avgScore = evals.length > 0
    ? Math.round(evals.reduce((s, e) => s + e.score, 0) / evals.length) : 0

  return `
Compile final assessment report.

CANDIDATE: ${analysis.name}
ROLE: ${analysis.role}
EXPERIENCE LEVEL: ${analysis.experience_level} (${analysis.required_experience})
RESUME FIT SCORE: ${analysis.fit_score}/100

INTERVIEW PERFORMANCE:
Average Answer Score: ${avgScore}/100 across ${evals.length} questions.

Return EXACTLY this JSON:
{
  "overall_score": 75,
  "grade": "A | B | C | D | F",
  "recommendation": "Strongly Recommend | Recommend | Consider | Pass",
  "technical_score": 70,
  "communication_score": 75,
  "problem_solving_score": 70,
  "cultural_fit_score": 80,
  "summary": "2 objective summary sentences about performance for ${analysis.role}",
  "top_strengths": ["strength 1", "strength 2"],
  "areas_to_improve": ["area 1", "area 2"],
  "next_steps": "Actionable recommendation for next hiring stage",
  "per_dimension_feedback": [
    {"dimension": "Role Knowledge", "score": 70, "note": "1 summary sentence"},
    {"dimension": "Communication", "score": 75, "note": "1 summary sentence"},
    {"dimension": "Problem Solving", "score": 70, "note": "1 summary sentence"},
    {"dimension": "Cultural Fit", "score": 80, "note": "1 summary sentence"}
  ]
}
`
}

export async function generateFinalReport(
  analysis: ResumeAnalysis,
  questions: InterviewQuestion[],
  evals: AnswerEvaluation[]
): Promise<InterviewReport> {
  const avgScore = evals.length > 0
    ? Math.round(evals.reduce((s, e) => s + e.score, 0) / evals.length)
    : analysis.fit_score

  let parsed: Partial<InterviewReport> | null = null
  try {
    const raw = await aiChat([
      { role: 'system', content: REPORT_SYSTEM },
      { role: 'user', content: REPORT_PROMPT(analysis, questions, evals) },
    ], { json: true, timeout: 180_000, temperature: 0.3 })

    parsed = extractJSON<Partial<InterviewReport>>(raw)
  } catch (err) {
    console.warn('AI report generation timed out or failed, using local report heuristic:', err)
  }

  const grade: Grade = avgScore >= 90 ? 'A' : avgScore >= 75 ? 'B' : avgScore >= 60 ? 'C' : avgScore >= 45 ? 'D' : 'F'
  const recommendation: Recommendation = avgScore >= 80 ? 'Strongly Recommend' : avgScore >= 65 ? 'Recommend' : avgScore >= 50 ? 'Consider' : 'Pass'

  return {
    overall_score: parsed?.overall_score ?? avgScore,
    grade: (parsed?.grade as Grade) || grade,
    recommendation: (parsed?.recommendation as Recommendation) || recommendation,
    technical_score: parsed?.technical_score ?? Math.min(100, avgScore + 2),
    communication_score: parsed?.communication_score ?? avgScore,
    problem_solving_score: parsed?.problem_solving_score ?? Math.max(0, avgScore - 2),
    cultural_fit_score: parsed?.cultural_fit_score ?? Math.min(100, avgScore + 5),
    summary: parsed?.summary || `${analysis.name} completed the AI assessment for ${analysis.role} with an overall score of ${avgScore}/100.`,
    top_strengths: Array.isArray(parsed?.top_strengths) ? parsed.top_strengths : ['Solid communication', 'Relevant technical competencies'],
    areas_to_improve: Array.isArray(parsed?.areas_to_improve) ? parsed.areas_to_improve : ['Deeper domain scenario handling'],
    next_steps: parsed?.next_steps || 'Proceed to technical hiring manager interview.',
    per_dimension_feedback: Array.isArray(parsed?.per_dimension_feedback) ? parsed.per_dimension_feedback : [
      { dimension: 'Technical Depth', score: avgScore, note: 'Demonstrates good foundational knowledge.' },
      { dimension: 'Communication', score: avgScore, note: 'Clear and structured articulation.' }
    ]
  }
}

export { OLLAMA_MODEL }
