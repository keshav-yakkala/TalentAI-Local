import { useParams, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ArrowLeft, CheckCircle2, XCircle, AlertCircle, Brain, FileText,
  Briefcase, GraduationCap, Code2, Mic, TrendingUp, MessageSquare,
  ChevronRight, Star, User
} from 'lucide-react'

// Demo data — will come from API in production
const mockCandidate = {
  id: '1',
  full_name: 'Sarah Chen',
  email: 'sarah@example.com',
  phone: '+1 415 555 0123',
  location: 'San Francisco, CA',
  summary: 'Senior ML Engineer with 6 years of experience building production ML systems at scale. Deep expertise in LLMs, RAG pipelines, and distributed training. Open source contributor to Hugging Face transformers.',
  skills: [
    { name: 'Python', proficiency: 'advanced', evidence: 'Used in all 5 projects listed on resume' },
    { name: 'PyTorch', proficiency: 'advanced', evidence: 'Built custom training loops for LLM fine-tuning at Anthropic' },
    { name: 'FastAPI', proficiency: 'intermediate', evidence: 'Built production API serving 10M+ requests/day' },
    { name: 'Kubernetes', proficiency: 'intermediate', evidence: 'Managed GPU cluster deployment at startup' },
    { name: 'LangChain', proficiency: 'advanced', evidence: 'Built RAG system for enterprise search product' },
  ],
  experience: [
    { company: 'Scale AI', title: 'Senior ML Engineer', duration: '2022–Present', description: 'Built RLHF pipeline for LLM alignment. Led team of 5 engineers.' },
    { company: 'Anthropic', title: 'ML Engineer', duration: '2020–2022', description: 'Fine-tuned Claude safety models. Implemented constitutional AI training.' },
    { company: 'Google', title: 'Software Engineer', duration: '2018–2020', description: 'Backend infrastructure for Google Search.' },
  ],
  education: [{ degree: 'MS Computer Science', institution: 'Stanford University', year: '2018' }],
  screening: {
    overall_score: 87,
    technical_score: 91,
    experience_score: 85,
    project_score: 88,
    education_score: 90,
    confidence_score: 0.94,
    recommendation: 'strong_match',
    explanation: 'Sarah is an exceptional match for the Senior ML Engineer role. She has 6 years of directly relevant experience, with deep expertise in LLMs and production ML systems. All required skills were verified with concrete evidence. Her experience at Scale AI and Anthropic demonstrates exactly the type of work this role requires. The only gap noted is Docker experience (preferred, not required). Strongly recommended for technical interview.',
    missing_required_skills: [],
    skill_matches: [
      { skill_name: 'Python', found: true, evidence: 'Extensive use across all projects' },
      { skill_name: 'PyTorch', found: true, evidence: 'Fine-tuned LLMs at Anthropic' },
      { skill_name: 'FastAPI', found: true, evidence: 'Production API serving 10M req/day' },
      { skill_name: 'Docker', found: false, evidence: 'No explicit mention in resume' },
      { skill_name: 'LLMs', found: true, evidence: 'Core specialization — multiple projects' },
    ],
  },
}

function ScoreBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="h-2 rounded-full bg-white/5 overflow-hidden">
      <motion.div
        className={`h-full rounded-full ${color}`}
        initial={{ width: 0 }}
        animate={{ width: `${value}%` }}
        transition={{ duration: 0.8, ease: 'easeOut' }}
      />
    </div>
  )
}

export default function CandidateDetailPage() {
  const { candidateId } = useParams()
  const c = mockCandidate // In production: use API hook
  const s = c.screening

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link to="/recruiter/candidates" className="btn-ghost px-3 py-2 text-sm">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div className="flex-1">
          <h1 className="font-outfit text-2xl font-bold text-white">{c.full_name}</h1>
          <p className="text-slate-400 text-sm">{c.email} · {c.location}</p>
        </div>
        <div className="text-right">
          <div className={`font-outfit text-4xl font-black ${
            s.overall_score >= 75 ? 'text-emerald-400' : s.overall_score >= 55 ? 'text-blue-400' : 'text-amber-400'
          }`}>{s.overall_score}</div>
          <div className="text-xs text-slate-500">Overall Score / 100</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column: Profile */}
        <div className="lg:col-span-2 space-y-5">
          {/* Summary */}
          <div className="glass-card p-6">
            <div className="flex items-center gap-2 mb-3">
              <User className="w-4 h-4 text-violet-400" />
              <h2 className="font-semibold text-white">Professional Summary</h2>
            </div>
            <p className="text-slate-300 text-sm leading-relaxed">{c.summary}</p>
          </div>

          {/* Skill Match Evidence */}
          <div className="glass-card p-6">
            <div className="flex items-center gap-2 mb-4">
              <Code2 className="w-4 h-4 text-violet-400" />
              <h2 className="font-semibold text-white">Skill Match Evidence</h2>
              <span className="text-xs text-slate-500 ml-auto">AI-verified, not assumed</span>
            </div>
            <div className="space-y-3">
              {s.skill_matches.map((match) => (
                <div key={match.skill_name} className="flex items-start gap-3 py-2 border-b border-white/5 last:border-0">
                  {match.found ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  ) : (
                    <XCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                  )}
                  <div>
                    <span className="text-sm font-medium text-white">{match.skill_name}</span>
                    <p className="text-xs text-slate-500 mt-0.5 italic">"{match.evidence}"</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Experience */}
          <div className="glass-card p-6">
            <div className="flex items-center gap-2 mb-4">
              <Briefcase className="w-4 h-4 text-violet-400" />
              <h2 className="font-semibold text-white">Work Experience</h2>
            </div>
            <div className="space-y-5">
              {c.experience.map((exp, i) => (
                <div key={i} className="relative pl-5 border-l border-white/10">
                  <div className="absolute -left-1.5 top-1.5 w-3 h-3 rounded-full bg-violet-500 border-2 border-[#0A1022]" />
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="font-medium text-white">{exp.title}</h3>
                      <p className="text-violet-300 text-sm">{exp.company}</p>
                    </div>
                    <span className="text-xs text-slate-500">{exp.duration}</span>
                  </div>
                  <p className="text-slate-400 text-sm mt-1">{exp.description}</p>
                </div>
              ))}
            </div>
          </div>

          {/* AI Explanation */}
          <div className="glass-card p-6 border-violet-500/20" style={{ background: 'rgba(124,58,237,0.05)' }}>
            <div className="flex items-center gap-2 mb-3">
              <Brain className="w-4 h-4 text-violet-400" />
              <h2 className="font-semibold text-white">AI Screening Summary</h2>
              <span className={`score-badge ml-auto ${
                s.recommendation === 'strong_match' ? 'strong' :
                s.recommendation === 'potential_match' ? 'potential' : 'review'
              }`}>{s.recommendation.replace(/_/g, ' ')}</span>
            </div>
            <p className="text-slate-300 text-sm leading-relaxed">{s.explanation}</p>
            <div className="mt-3 flex items-center gap-2 text-xs text-slate-500">
              <AlertCircle className="w-3.5 h-3.5" />
              AI recommendation — human decision required
            </div>
          </div>
        </div>

        {/* Right column: Scores */}
        <div className="space-y-5">
          {/* Category scores */}
          <div className="glass-card p-5">
            <h2 className="font-semibold text-white mb-4 text-sm">Category Scores</h2>
            <div className="space-y-4">
              {[
                { label: 'Required Skills', value: s.technical_score, color: 'bg-violet-500', weight: '30%' },
                { label: 'Experience', value: s.experience_score, color: 'bg-blue-500', weight: '20%' },
                { label: 'Projects', value: s.project_score, color: 'bg-emerald-500', weight: '20%' },
                { label: 'Education', value: s.education_score, color: 'bg-amber-500', weight: '5%' },
              ].map((cat) => (
                <div key={cat.label}>
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="text-slate-400">{cat.label}</span>
                    <div className="flex gap-2">
                      <span className="text-slate-600">{cat.weight}</span>
                      <span className="text-white font-medium">{cat.value}</span>
                    </div>
                  </div>
                  <ScoreBar value={cat.value} color={cat.color} />
                </div>
              ))}
            </div>
            <div className="mt-4 pt-4 border-t border-white/5 flex justify-between text-sm">
              <span className="text-slate-400">AI Confidence</span>
              <span className="text-emerald-400 font-semibold">{(s.confidence_score * 100).toFixed(0)}%</span>
            </div>
          </div>

          {/* Actions */}
          <div className="glass-card p-5 space-y-3">
            <h2 className="font-semibold text-white text-sm mb-2">Actions</h2>
            <button className="btn-primary w-full py-2.5 text-sm" id="invite-interview">
              <Mic className="w-4 h-4" />
              Invite for AI Interview
            </button>
            <button className="btn-ghost w-full py-2.5 text-sm">
              <MessageSquare className="w-4 h-4" />
              Send Message
            </button>
            <button className="btn-ghost w-full py-2.5 text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10">
              <XCircle className="w-4 h-4" />
              Reject Candidate
            </button>
          </div>

          {/* Skills cloud */}
          <div className="glass-card p-5">
            <h2 className="font-semibold text-white text-sm mb-3">Verified Skills</h2>
            <div className="flex flex-wrap gap-2">
              {c.skills.map((skill) => (
                <div key={skill.name} title={skill.evidence}
                  className="px-3 py-1.5 rounded-xl bg-white/5 border border-white/[0.08] text-sm text-slate-300 hover:bg-violet-500/10 hover:border-violet-500/30 transition-colors cursor-help">
                  {skill.name}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
