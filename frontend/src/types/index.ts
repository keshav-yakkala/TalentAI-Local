/**
 * TalentAI — TypeScript type definitions
 * Mirrors the backend Pydantic schemas exactly.
 */

// ── Auth ──────────────────────────────────────────────────────────────────────

export type UserRole = 'admin' | 'recruiter' | 'candidate'

export interface User {
  id: string
  email: string
  full_name: string
  role: UserRole
  is_active: boolean
  created_at: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  full_name: string
  role: UserRole
}

// ── Organization ──────────────────────────────────────────────────────────────

export interface Organization {
  id: string
  name: string
  created_at: string
}

// ── Jobs ──────────────────────────────────────────────────────────────────────

export type JobStatus = 'draft' | 'active' | 'paused' | 'closed' | 'archived'
export type EmploymentType = 'full_time' | 'part_time' | 'contract' | 'internship' | 'freelance'
export type RequirementType = 'required_skill' | 'preferred_skill' | 'experience' | 'education' | 'certification' | 'domain'
export type RequirementImportance = 'must_have' | 'nice_to_have'

export interface JobRequirement {
  id: string
  requirement_type: RequirementType
  name: string
  importance: RequirementImportance
  weight: number | null
  minimum_level: string | null
}

export interface Job {
  id: string
  organization_id: string
  title: string
  description: string | null
  department: string | null
  location: string | null
  employment_type: EmploymentType | null
  status: JobStatus
  created_at: string
  updated_at: string
  requirements: JobRequirement[]
}

// ── Candidates ────────────────────────────────────────────────────────────────

export interface Candidate {
  id: string
  full_name: string
  email: string | null
  phone: string | null
  location: string | null
  summary: string | null
  created_at: string
}

// ── Resume ────────────────────────────────────────────────────────────────────

export type ParsingStatus = 'pending' | 'parsing' | 'extracting' | 'embedding' | 'completed' | 'failed' | 'human_review_required'

export interface Resume {
  id: string
  candidate_id: string
  original_filename: string
  mime_type: string
  parsing_status: ParsingStatus
  extraction_confidence: number | null
  created_at: string
}

// ── Applications ──────────────────────────────────────────────────────────────

export type ApplicationStatus =
  | 'applied' | 'processing' | 'screened' | 'human_review'
  | 'shortlisted' | 'interview_invited' | 'interviewing'
  | 'interview_completed' | 'final_review' | 'selected' | 'rejected'

export interface Application {
  id: string
  candidate_id: string
  job_id: string
  status: ApplicationStatus
  created_at: string
}

// ── Screening ─────────────────────────────────────────────────────────────────

export type ScreeningRecommendation = 'strong_match' | 'potential_match' | 'needs_human_review' | 'weak_match'

export interface ScreeningResult {
  id: string
  application_id: string
  overall_score: number | null
  technical_score: number | null
  experience_score: number | null
  project_score: number | null
  education_score: number | null
  domain_score: number | null
  semantic_match_score: number | null
  confidence_score: number | null
  recommendation: ScreeningRecommendation | null
  explanation: string | null
  evidence_json: Record<string, unknown> | null
  created_at: string
}

// ── Interviews ────────────────────────────────────────────────────────────────

export type InterviewStatus = 'pending' | 'in_progress' | 'paused' | 'completed' | 'failed'
export type InterviewDifficulty = 'easy' | 'medium' | 'hard' | 'adaptive'
export type QuestionType = 'resume_based' | 'project_deep_dive' | 'technical_fundamentals' | 'system_design' | 'scenario_based' | 'debugging' | 'behavioral' | 'follow_up' | 'clarification'

export interface Interview {
  id: string
  application_id: string
  status: InterviewStatus
  difficulty: InterviewDifficulty
  started_at: string | null
  completed_at: string | null
}

export interface InterviewQuestion {
  id: string
  sequence_number: number
  question: string
  question_type: QuestionType
  topic: string | null
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export interface RecruiterDashboard {
  active_jobs: number
  total_applicants: number
  candidates_screened: number
  candidates_awaiting_review: number
  interviews_scheduled: number
  interviews_completed: number
  recent_activity: Array<Record<string, unknown>>
}

// ── API Responses ─────────────────────────────────────────────────────────────

export interface APIError {
  success: false
  error: string
  code?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}
