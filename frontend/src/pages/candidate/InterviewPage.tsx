/**
 * TalentAI — Candidate AI Interview Platform
 * Powered exclusively by Grok AI (xAI).
 */

import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Mic, MicOff, Upload, Brain, CheckCircle2, AlertCircle,
  ChevronRight, BarChart3, Award, Clock, Zap, FileText,
  SkipForward, RotateCcw, Star, TrendingUp, Target,
  MessageSquare, Cpu, ArrowRight, Play, Square,
  Server, Terminal, RefreshCw, Sparkles, Loader2,
  XCircle, ChevronDown, ChevronUp, Edit3, Trash2,
} from 'lucide-react'
import {
  analyzeResume, generateInterviewQuestions, evaluateAnswer,
  generateFinalReport, extractTextFromFile,
  type ResumeAnalysis, type InterviewQuestion,
  type AnswerEvaluation, type InterviewReport,
} from '@/api/interviewEngine'
import { GROK_MODEL } from '@/api/grokClient'
import { useAuthStore } from '@/store/auth'
import { Link } from 'react-router-dom'

// ── Page-level state machine ──────────────────────────────────────────────────
type Stage =
  | 'upload'            // resume + JD form
  | 'analyzing'         // LLM analyzing resume
  | 'analysis'          // show analysis results
  | 'generating_qs'     // LLM generating questions
  | 'interview'         // question / answer loop
  | 'evaluating'        // LLM evaluating current answer
  | 'generating_report' // LLM generating final report
  | 'results'           // show final report

// ── SpeechRecognition types ───────────────────────────────────────────────────
interface SpeechResult {
  readonly isFinal: boolean
  readonly [index: number]: { readonly transcript: string }
}
interface SpeechResultList {
  readonly length: number
  readonly [index: number]: SpeechResult
}
interface SpeechEvent extends Event {
  readonly resultIndex: number
  readonly results: SpeechResultList
}
interface SR extends EventTarget {
  continuous: boolean
  interimResults: boolean
  lang: string
  maxAlternatives: number
  start(): void
  stop(): void
  abort(): void
  onresult: ((e: SpeechEvent) => void) | null
  onerror: ((e: Event) => void) | null
  onend: ((e: Event) => void) | null
}
interface SRConstructor { new(): SR }
declare global {
  interface Window { SpeechRecognition?: SRConstructor; webkitSpeechRecognition?: SRConstructor }
}

// ── Voice hook (push-to-talk, live real-time transcript) ──────────────────────
function useVoice(onUpdate: (text: string) => void) {
  const [isRecording, setIsRecording] = useState(false)
  const [supported, setSupported] = useState(false)
  const srRef = useRef<SR | null>(null)
  const accRef = useRef('') // accumulated FINAL text
  const isRecordingRef = useRef(false)

  useEffect(() => {
    const Ctor = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!Ctor) return
    setSupported(true)
    const sr = new Ctor()
    sr.continuous = true
    sr.interimResults = true // Live real-time feedback as user speaks
    sr.lang = 'en-US'
    sr.maxAlternatives = 1

    sr.onresult = (e: SpeechEvent) => {
      let interim = ''
      let finalStr = ''
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const transcript = e.results[i][0].transcript
        if (e.results[i].isFinal) {
          finalStr += transcript + ' '
        } else {
          interim += transcript
        }
      }
      if (finalStr) {
        accRef.current += (accRef.current ? ' ' : '') + finalStr.trim()
      }
      const fullText = (accRef.current + (interim ? ' ' + interim.trim() : '')).trim()
      onUpdate(fullText)
    }

    sr.onerror = (e) => {
      const errorMsg = (e as unknown as { error?: string })?.error
      if (errorMsg === 'no-speech') return
      setIsRecording(false)
      isRecordingRef.current = false
    }

    sr.onend = () => {
      if (isRecordingRef.current) {
        try {
          sr.start()
        } catch {
          setIsRecording(false)
          isRecordingRef.current = false
        }
      } else {
        setIsRecording(false)
      }
    }

    srRef.current = sr
    return () => {
      isRecordingRef.current = false
      try { sr.abort() } catch {}
    }
  }, [onUpdate])

  const start = useCallback(() => {
    if (!srRef.current) return
    accRef.current = ''
    isRecordingRef.current = true
    setIsRecording(true)
    try {
      srRef.current.start()
    } catch {}
  }, [])

  const stop = useCallback(() => {
    isRecordingRef.current = false
    setIsRecording(false)
    try {
      srRef.current?.stop()
    } catch {}
  }, [])

  const reset = useCallback(() => {
    isRecordingRef.current = false
    setIsRecording(false)
    accRef.current = ''
    try {
      srRef.current?.abort()
    } catch {}
  }, [])

  return { isRecording, supported, start, stop, reset, accumulated: accRef }
}

// ── UI helpers ────────────────────────────────────────────────────────────────
function CircularScore({ score, size = 80, color = '#7c3aed' }: { score: number; size?: number; color?: string }) {
  const r = (size - 10) / 2
  const circ = 2 * Math.PI * r
  return (
    <svg width={size} height={size} className="-rotate-90">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={6} />
      <motion.circle
        cx={size / 2} cy={size / 2} r={r} fill="none"
        stroke={color} strokeWidth={6} strokeLinecap="round"
        initial={{ strokeDasharray: `0 ${circ}` }}
        animate={{ strokeDasharray: `${(score / 100) * circ} ${circ}` }}
        transition={{ duration: 1.2, ease: 'easeOut' }}
      />
    </svg>
  )
}

function ScoreBar({ label, score, color }: { label: string; score: number; color: string }) {
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-slate-400">{label}</span>
        <span className="font-semibold text-white">{score}</span>
      </div>
      <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ background: color }}
          initial={{ width: 0 }}
          animate={{ width: `${score}%` }}
          transition={{ duration: 1, ease: 'easeOut' }}
        />
      </div>
    </div>
  )
}

function ThinkingDots() {
  return (
    <div className="flex gap-1.5 items-center">
      {[0, 1, 2].map(i => (
        <motion.div
          key={i}
          className="w-2 h-2 rounded-full bg-violet-400"
          animate={{ opacity: [0.3, 1, 0.3], scale: [0.8, 1.2, 0.8] }}
          transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
        />
      ))}
    </div>
  )
}

// ── Stage 1: Upload ───────────────────────────────────────────────────────────
function UploadStep({ onSubmit, ollamaModel }: {
  onSubmit: (text: string, filename: string, role: string, jd: string) => void
  ollamaModel: string | null
}) {
  const [file, setFile] = useState<File | null>(null)
  const [role, setRole] = useState('')
  const [jd, setJd] = useState('')
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  const handleFile = (f: File) => {
    const ok = ['application/pdf', 'text/plain', 'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
    if (!ok.includes(f.type) && !f.name.match(/\.(pdf|txt|doc|docx)$/i)) {
      setError('Please upload PDF, DOCX, or TXT.')
      return
    }
    setFile(f)
    setError('')
  }

  const handleSubmit = async () => {
    if (!file) { setError('Please upload your resume.'); return }
    if (!role.trim()) { setError('Please enter the job role.'); return }
    setLoading(true)
    try {
      const text = await extractTextFromFile(file)
      onSubmit(text, file.name, role.trim(), jd.trim())
    } catch {
      setError('Failed to read file. Try a different format.')
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-5">
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 bg-violet-500/10 border border-violet-500/20 rounded-full px-4 py-1.5 mb-4">
          <Sparkles className="w-4 h-4 text-violet-400" />
          <span className="text-sm text-violet-300 font-medium">
            Powered by Grok AI (xAI)
          </span>
        </div>
        <h1 className="font-outfit text-3xl font-bold text-white mb-2">Start Your AI Interview</h1>
        <p className="text-slate-400 text-sm">Upload resume + job details → AI screens you → Live interview with voice answers</p>
      </div>

      {/* Resume drop zone */}
      <div className="glass-card p-6">
        <label className="block text-sm font-semibold text-slate-300 mb-3">
          <FileText className="w-4 h-4 text-violet-400 inline mr-1.5" /> Your Resume / CV
        </label>
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files[0]; if (f) handleFile(f) }}
          onClick={() => fileRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
            dragging ? 'border-violet-400 bg-violet-500/10' :
            file ? 'border-emerald-500/40 bg-emerald-500/5' :
            'border-white/10 hover:border-violet-500/30 hover:bg-violet-500/5'
          }`}
        >
          <input ref={fileRef} type="file" className="hidden" accept=".pdf,.txt,.doc,.docx"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f) }}
          />
          {file ? (
            <div className="flex items-center justify-center gap-3">
              <CheckCircle2 className="w-8 h-8 text-emerald-400" />
              <div className="text-left">
                <p className="text-white font-medium">{file.name}</p>
                <p className="text-slate-400 text-sm">{(file.size / 1024).toFixed(0)} KB · Click to replace</p>
              </div>
            </div>
          ) : (
            <>
              <Upload className="w-9 h-9 text-slate-500 mx-auto mb-2" />
              <p className="text-slate-300 font-medium">Drop resume here or click to browse</p>
              <p className="text-slate-500 text-xs mt-1">PDF, DOCX, TXT · Max 10 MB</p>
            </>
          )}
        </div>
      </div>

      {/* Job details */}
      <div className="glass-card p-6 space-y-4">
        <div>
          <label className="block text-sm font-semibold text-slate-300 mb-1.5">
            <Target className="w-4 h-4 text-violet-400 inline mr-1.5" /> Job Role *
          </label>
          <input
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="input-field"
            placeholder="e.g. Software Engineer Intern, Junior Python Developer, Data Analyst"
            id="job-role-input"
          />
        </div>
        <div>
          <label className="block text-sm font-semibold text-slate-300 mb-1.5">
            <FileText className="w-4 h-4 text-violet-400 inline mr-1.5" />
            Job Description <span className="text-slate-500 font-normal">(highly recommended — helps AI ask the right questions)</span>
          </label>
          <textarea
            value={jd}
            onChange={(e) => setJd(e.target.value)}
            className="input-field resize-none text-sm"
            rows={5}
            placeholder="Paste the full job description here.&#10;&#10;Example: 'We are looking for a fresher/entry-level Python developer. No experience required. Must know Python basics and OOP concepts...'"
            id="jd-input"
          />
          <p className="text-xs text-slate-500 mt-1">
            💡 The AI reads the JD to understand experience level (fresher/senior), required skills, and tailors questions accordingly.
          </p>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3">
          <XCircle className="w-4 h-4 shrink-0" /><p className="text-sm">{error}</p>
        </div>
      )}

      <button
        onClick={handleSubmit}
        disabled={loading}
        id="start-btn"
        className="btn-primary w-full py-4 text-base"
      >
        {loading ? <><Loader2 className="w-5 h-5 animate-spin" /> Reading resume...</>
          : <><Brain className="w-5 h-5" /> Analyze & Start Interview <ArrowRight className="w-4 h-4" /></>}
      </button>
    </div>
  )
}

// ── Loading screen (reused for all LLM calls) ─────────────────────────────────
function LLMLoading({ title, subtitle, step }: { title: string; subtitle: string; step?: string }) {
  return (
    <div className="max-w-md mx-auto text-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="glass-card p-10"
        style={{ boxShadow: '0 0 60px rgba(124,58,237,0.2)' }}
      >
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center mx-auto mb-5">
          <Brain className="w-8 h-8 text-white animate-pulse" />
        </div>
        <h3 className="font-outfit text-xl font-bold text-white mb-2">{title}</h3>
        <p className="text-slate-400 text-sm mb-2">{subtitle}</p>
        {step && <p className="text-violet-400 text-xs font-medium mb-5">{step}</p>}
        <div className="flex justify-center">
          <ThinkingDots />
        </div>
        <p className="text-slate-600 text-xs mt-4">Using Grok 2 AI (xAI) · Cloud Inference</p>
      </motion.div>
    </div>
  )
}

// ── Stage 2: Analysis results ─────────────────────────────────────────────────
function AnalysisStep({ analysis, onStart }: { analysis: ResumeAnalysis; onStart: () => void }) {
  const fitColor =
    analysis.fit_score >= 80 ? '#10b981' :
    analysis.fit_score >= 60 ? '#3b82f6' :
    analysis.fit_score >= 40 ? '#f59e0b' : '#ef4444'

  const expBadgeColor: Record<string, string> = {
    fresher: 'bg-emerald-500/15 text-emerald-300',
    junior: 'bg-blue-500/15 text-blue-300',
    mid: 'bg-violet-500/15 text-violet-300',
    senior: 'bg-orange-500/15 text-orange-300',
  }

  return (
    <div className="max-w-3xl mx-auto space-y-5">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center">
        <div className="inline-flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-4 py-1.5 mb-4">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span className="text-sm text-emerald-300 font-medium">AI Analysis Complete</span>
        </div>
        <h2 className="font-outfit text-3xl font-bold text-white">Your Profile Snapshot</h2>
      </motion.div>

      {/* Score card */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.1 }}
        className="glass-card p-6"
        style={{ boxShadow: `0 0 50px ${fitColor}25` }}
      >
        <div className="flex items-center gap-6 flex-wrap">
          <div className="relative shrink-0">
            <CircularScore score={analysis.fit_score} size={110} color={fitColor} />
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="font-outfit text-2xl font-black text-white">{analysis.fit_score}</span>
              <span className="text-xs text-slate-400">/100</span>
            </div>
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span className="font-outfit text-2xl font-bold" style={{ color: fitColor }}>
                {analysis.fit_label}
              </span>
              <span className={`px-2 py-0.5 rounded-full text-xs font-semibold uppercase ${expBadgeColor[analysis.experience_level] || 'bg-slate-500/15 text-slate-300'}`}>
                {analysis.experience_level}
              </span>
            </div>
            <p className="text-sm text-slate-400 mb-1">
              <span className="text-slate-300 font-medium">JD requires:</span> {analysis.required_experience}
            </p>
            <p className="text-sm text-slate-300 leading-relaxed">{analysis.summary}</p>
            {analysis.matched_skills.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-3">
                {analysis.matched_skills.slice(0, 6).map(s => (
                  <span key={s} className="px-2 py-0.5 rounded-full bg-violet-500/10 border border-violet-500/20 text-violet-300 text-xs capitalize">{s}</span>
                ))}
              </div>
            )}
          </div>
        </div>
      </motion.div>

      {/* Skills analysis */}
      {(analysis.missing_skills.length > 0 || analysis.matched_skills.length > 0) && (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.15 }}
          className="grid grid-cols-2 gap-4"
        >
          <div className="glass-card p-4">
            <p className="text-xs font-semibold text-emerald-400 mb-2">✓ Matched Skills</p>
            <div className="flex flex-wrap gap-1">
              {analysis.matched_skills.slice(0, 8).map(s => (
                <span key={s} className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-300 capitalize">{s}</span>
              ))}
              {analysis.matched_skills.length === 0 && <span className="text-xs text-slate-500">None detected</span>}
            </div>
          </div>
          <div className="glass-card p-4">
            <p className="text-xs font-semibold text-red-400 mb-2">✗ Missing / To Build</p>
            <div className="flex flex-wrap gap-1">
              {analysis.missing_skills.slice(0, 8).map(s => (
                <span key={s} className="text-xs px-2 py-0.5 rounded-full bg-red-500/10 text-red-300 capitalize">{s}</span>
              ))}
              {analysis.missing_skills.length === 0 && <span className="text-xs text-slate-500">None missing</span>}
            </div>
          </div>
        </motion.div>
      )}

      {/* Strengths + Weaknesses */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <motion.div
          initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 }}
          className="glass-card p-5"
        >
          <h3 className="font-outfit font-bold text-emerald-400 flex items-center gap-2 mb-3 text-sm">
            <TrendingUp className="w-4 h-4" /> Strengths
          </h3>
          <div className="space-y-3">
            {analysis.strengths.map((s, i) => (
              <div key={i} className="flex items-start gap-2.5">
                <Star className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-semibold text-white">{s.label}</p>
                  <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">{s.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.25 }}
          className="glass-card p-5"
        >
          <h3 className="font-outfit font-bold text-amber-400 flex items-center gap-2 mb-3 text-sm">
            <AlertCircle className="w-4 h-4" /> Areas to Address
          </h3>
          <div className="space-y-3">
            {analysis.weaknesses.map((w, i) => (
              <div key={i} className="flex items-start gap-2.5">
                <AlertCircle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-semibold text-white">{w.label}</p>
                  <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">{w.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
        className="glass-card p-5 border border-violet-500/20 bg-violet-500/5"
      >
        <div className="flex items-start gap-3">
          <Mic className="w-5 h-5 text-violet-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-white mb-1">Interview starts next</p>
            <p className="text-xs text-slate-400">
              7 questions tailored to a <strong className="text-violet-300">{analysis.experience_level}</strong> candidate applying for <strong className="text-violet-300">{analysis.role}</strong>.
              Answer by <strong className="text-violet-300">voice</strong> (push mic button) or type. No time pressure.
            </p>
          </div>
        </div>
      </motion.div>

      <motion.button
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}
        onClick={onStart}
        id="begin-interview-btn"
        className="btn-primary w-full py-4 text-base"
      >
        <Play className="w-5 h-5" /> Generate Questions & Begin <ChevronRight className="w-4 h-4" />
      </motion.button>
    </div>
  )
}

// ── Stage 3: Interview (question / answer loop) ───────────────────────────────
function InterviewStep({
  questions, analysis, onComplete,
}: {
  questions: InterviewQuestion[]
  analysis: ResumeAnalysis
  onComplete: (evals: AnswerEvaluation[]) => void
}) {
  const [idx, setIdx] = useState(0)
  const [answer, setAnswer] = useState('')
  const [evals, setEvals] = useState<AnswerEvaluation[]>([])
  const [evaluating, setEvaluating] = useState(false)
  const [evalError, setEvalError] = useState('')
  const [startTime, setStartTime] = useState(Date.now())
  const [elapsed, setElapsed] = useState(0)
  const [voiceStatus, setVoiceStatus] = useState<'idle' | 'recording' | 'done'>('idle')

  const q = questions[idx]
  const progress = (idx / questions.length) * 100

  // Timer
  useEffect(() => {
    setStartTime(Date.now())
    setElapsed(0)
    const t = setInterval(() => setElapsed(Math.floor((Date.now() - startTime) / 1000)), 1000)
    return () => clearInterval(t)
  }, [idx])

  // Voice
  const handleVoiceUpdate = useCallback((text: string) => {
    setAnswer(text)
  }, [])

  const { isRecording, supported, start, stop, reset } = useVoice(handleVoiceUpdate)

  const handleStartVoice = () => {
    if (isRecording) {
      stop()
      setVoiceStatus('done')
    } else {
      reset()
      setAnswer('')
      start()
      setVoiceStatus('recording')
    }
  }

  const handleClearVoice = () => {
    reset()
    setAnswer('')
    setVoiceStatus('idle')
  }

  const submitAnswer = async () => {
    if (!answer.trim() && !isRecording) return
    if (isRecording) stop()
    setEvaluating(true)
    setEvalError('')

    const duration = Math.floor((Date.now() - startTime) / 1000)
    try {
      const evaluation = await evaluateAnswer(q, answer || '(No answer provided)', duration, analysis)
      const newEvals = [...evals, evaluation]
      setEvals(newEvals)

      if (idx + 1 >= questions.length) {
        onComplete(newEvals)
      } else {
        setIdx(idx + 1)
        setAnswer('')
        setVoiceStatus('idle')
        reset()
      }
    } catch (err) {
      setEvalError(err instanceof Error ? err.message : 'Evaluation failed. Check Ollama is running.')
    } finally {
      setEvaluating(false)
    }
  }

  const skipQuestion = () => {
    const skippedEval: AnswerEvaluation = {
      question_id: q.id,
      sequence: q.sequence,
      score: 0, clarity: 0, depth: 0, relevance: 0, communication: 0,
      feedback: 'Question was skipped.',
      positive_points: [],
      improvement_points: ['Do not skip questions — every answer counts.'],
      ideal_answer_hint: '',
    }
    const newEvals = [...evals, skippedEval]
    setEvals(newEvals)
    if (idx + 1 >= questions.length) {
      onComplete(newEvals)
    } else {
      setIdx(idx + 1)
      setAnswer('')
      setVoiceStatus('idle')
      reset()
    }
  }

  const diffBadge = { easy: 'bg-emerald-500/15 text-emerald-400', medium: 'bg-amber-500/15 text-amber-400', hard: 'bg-red-500/15 text-red-400' }[q.difficulty]
  const typeBadge: Record<string, string> = { technical: 'text-blue-400', behavioral: 'text-violet-400', situational: 'text-amber-400', project: 'text-emerald-400', system_design: 'text-pink-400' }

  const pad = (n: number) => n.toString().padStart(2, '0')

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      {/* Progress bar */}
      <div className="glass-card p-4">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-violet-500 flex items-center justify-center text-sm font-bold text-white">{idx + 1}</div>
            <div>
              <p className="text-xs text-slate-400">Question {idx + 1} of {questions.length}</p>
              <p className="text-sm font-medium text-white">{analysis.role} Interview</p>
            </div>
          </div>
          <div className="text-slate-400 text-xs flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5" />{pad(Math.floor(elapsed / 60))}:{pad(elapsed % 60)}
          </div>
        </div>
        <div className="h-1.5 rounded-full bg-white/5">
          <motion.div className="h-full rounded-full bg-gradient-to-r from-violet-500 to-purple-600" style={{ width: `${progress}%` }} transition={{ duration: 0.4 }} />
        </div>
      </div>

      {/* Question card */}
      <AnimatePresence mode="wait">
        <motion.div
          key={q.id}
          initial={{ opacity: 0, x: 40 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -40 }}
          transition={{ duration: 0.25 }}
          className="glass-card p-7"
          style={{ boxShadow: '0 0 40px rgba(124,58,237,0.12)' }}
        >
          {/* Tags */}
          <div className="flex items-center gap-2 mb-4 flex-wrap">
            <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${diffBadge}`}>
              {q.difficulty}
            </span>
            <span className={`text-xs font-medium ${typeBadge[q.type] || 'text-slate-400'}`}>
              {q.type.replace('_', ' ')}
            </span>
            <span className="text-xs text-slate-500">· {q.topic}</span>
          </div>

          {/* Question */}
          <div className="flex items-start gap-3 mb-5">
            <div className="w-7 h-7 rounded-full bg-violet-500/20 flex items-center justify-center shrink-0 mt-1">
              <MessageSquare className="w-3.5 h-3.5 text-violet-400" />
            </div>
            <p className="text-white text-lg leading-relaxed font-medium">{q.question}</p>
          </div>

          {/* Voice status bar */}
          <AnimatePresence>
            {isRecording && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="flex items-center gap-3 mb-3 px-4 py-2.5 rounded-xl bg-red-500/10 border border-red-500/20"
              >
                <div className="w-2.5 h-2.5 rounded-full bg-red-400 animate-pulse shrink-0" />
                <span className="text-sm text-red-300 font-medium">Listening... speak clearly</span>
                <div className="flex gap-0.5 ml-auto items-center h-5">
                  {Array.from({ length: 10 }).map((_, i) => (
                    <motion.div key={i} className="w-0.5 bg-red-400 rounded-full"
                      animate={{ height: [3, Math.random() * 14 + 4, 3] }}
                      transition={{ duration: 0.4 + Math.random() * 0.3, repeat: Infinity, delay: i * 0.04 }}
                    />
                  ))}
                </div>
              </motion.div>
            )}
            {voiceStatus === 'done' && !isRecording && answer && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-center gap-2 mb-3 px-3 py-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20"
              >
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span className="text-xs text-emerald-300">Voice captured — edit below if needed</span>
                <button onClick={handleClearVoice} className="ml-auto text-slate-500 hover:text-red-400 transition-colors">
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Answer textarea */}
          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            className="input-field resize-none mb-4 text-sm leading-relaxed"
            rows={5}
            placeholder={
              isRecording
                ? '🎤 Listening... Speak now (your words appear here in real-time)'
                : 'Type your answer here, or click Speak Answer to dictate...'
            }
            id={`answer-${q.id}`}
          />

          {evalError && (
            <div className="flex items-center gap-2 text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 mb-4">
              <XCircle className="w-4 h-4 shrink-0" />
              <p className="text-sm">{evalError}</p>
            </div>
          )}

          {/* Controls */}
          <div className="flex items-center gap-3 flex-wrap">
            {/* Voice button */}
            {supported ? (
              <button
                onClick={handleStartVoice}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isRecording
                    ? 'bg-red-500 text-white shadow-lg shadow-red-500/20 hover:bg-red-600'
                    : 'bg-violet-500/10 border border-violet-500/30 text-violet-300 hover:bg-violet-500/20'
                }`}
                id="voice-btn"
              >
                {isRecording ? <><Square className="w-4 h-4" />Stop Recording</> : <><Mic className="w-4 h-4" />Speak Answer</>}
              </button>
            ) : (
              <button disabled className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm bg-white/5 text-slate-500 cursor-not-allowed">
                <MicOff className="w-4 h-4" /> Voice (Chrome only)
              </button>
            )}

            {answer && !isRecording && (
              <button
                onClick={handleClearVoice}
                className="flex items-center gap-1.5 px-3 py-2.5 rounded-xl text-xs text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
                title="Clear answer and re-record"
                id="clear-answer-btn"
              >
                <Edit3 className="w-3.5 h-3.5" /> Clear
              </button>
            )}

            <button
              onClick={skipQuestion}
              className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
              id="skip-btn"
            >
              <SkipForward className="w-4 h-4" /> Skip
            </button>

            <button
              onClick={submitAnswer}
              disabled={evaluating || (!answer.trim() && !isRecording)}
              id="submit-answer-btn"
              className="btn-primary flex-1 py-2.5 text-sm ml-auto disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {evaluating
                ? <><Loader2 className="w-4 h-4 animate-spin" /> AI Evaluating...</>
                : idx + 1 >= questions.length
                ? <><CheckCircle2 className="w-4 h-4" /> Submit Final Answer</>
                : <><ChevronRight className="w-4 h-4" /> Submit & Next</>}
            </button>
          </div>

          {!supported && (
            <p className="text-xs text-slate-500 mt-2">
              💡 Voice requires Chrome or Edge. You can still type your answers.
            </p>
          )}
        </motion.div>
      </AnimatePresence>

      {/* Completed Q tracker */}
      {evals.length > 0 && (
        <div className="glass-card p-4">
          <p className="text-xs text-slate-500 font-medium mb-2">Answered</p>
          <div className="flex flex-wrap gap-2">
            {evals.map((ev, i) => (
              <div key={i} className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
                ev.score >= 70 ? 'bg-emerald-500/15 text-emerald-400' :
                ev.score >= 50 ? 'bg-amber-500/15 text-amber-400' :
                'bg-red-500/15 text-red-400'
              }`}>
                <CheckCircle2 className="w-3 h-3" /> Q{i + 1}: {ev.score}/100
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Stage 4: Results ──────────────────────────────────────────────────────────
function ResultsStep({
  report, evals, questions, analysis, onRestart,
}: {
  report: InterviewReport
  evals: AnswerEvaluation[]
  questions: InterviewQuestion[]
  analysis: ResumeAnalysis
  onRestart: () => void
}) {
  const [tab, setTab] = useState<'overview' | 'questions'>('overview')

  const gradeC: Record<string, { text: string; bg: string; border: string; glow: string }> = {
    A: { text: 'text-emerald-400', bg: 'bg-emerald-500/20', border: 'border-emerald-500/30', glow: 'rgba(16,185,129,0.25)' },
    B: { text: 'text-blue-400', bg: 'bg-blue-500/20', border: 'border-blue-500/30', glow: 'rgba(59,130,246,0.25)' },
    C: { text: 'text-amber-400', bg: 'bg-amber-500/20', border: 'border-amber-500/30', glow: 'rgba(245,158,11,0.25)' },
    D: { text: 'text-orange-400', bg: 'bg-orange-500/20', border: 'border-orange-500/30', glow: 'rgba(249,115,22,0.25)' },
    F: { text: 'text-red-400', bg: 'bg-red-500/20', border: 'border-red-500/30', glow: 'rgba(239,68,68,0.25)' },
  }
  const gc = gradeC[report.grade] ?? gradeC['C']

  const recColor: Record<string, string> = {
    'Strongly Recommend': 'text-emerald-400',
    'Recommend': 'text-blue-400',
    'Consider': 'text-amber-400',
    'Pass': 'text-red-400',
  }

  const dims = report.per_dimension_feedback.length > 0 ? report.per_dimension_feedback : [
    { dimension: 'Technical', score: report.technical_score, note: '' },
    { dimension: 'Communication', score: report.communication_score, note: '' },
    { dimension: 'Problem Solving', score: report.problem_solving_score, note: '' },
    { dimension: 'Cultural Fit', score: report.cultural_fit_score, note: '' },
  ]
  const dimColors = ['#3b82f6', '#7c3aed', '#10b981', '#f59e0b']

  return (
    <div className="max-w-3xl mx-auto space-y-5">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center">
        <div className="inline-flex items-center gap-2 bg-violet-500/10 border border-violet-500/20 rounded-full px-4 py-1.5 mb-4">
          <Award className="w-4 h-4 text-violet-400" />
          <span className="text-sm text-violet-300">AI Interview Report — {GROK_MODEL}</span>
        </div>
        <h2 className="font-outfit text-3xl font-bold text-white">Your Results</h2>
      </motion.div>

      {/* Grade hero */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.1 }}
        className={`glass-card p-7 border ${gc.border}`}
        style={{ boxShadow: `0 0 60px ${gc.glow}` }}
      >
        <div className="flex items-center gap-6 flex-wrap">
          <div className="relative shrink-0">
            <CircularScore score={report.overall_score} size={120}
              color={report.overall_score >= 70 ? '#10b981' : report.overall_score >= 55 ? '#f59e0b' : '#ef4444'} />
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="font-outfit text-3xl font-black text-white">{report.overall_score}</span>
              <span className="text-xs text-slate-400">/100</span>
            </div>
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-1">
              <span className={`text-5xl font-outfit font-black ${gc.text}`}>{report.grade}</span>
              <span className={`text-xl font-semibold ${recColor[report.recommendation] || 'text-white'}`}>{report.recommendation}</span>
            </div>
            <p className="text-slate-300 text-sm leading-relaxed max-w-md">{report.summary}</p>
          </div>
          <div className="w-full md:w-44 space-y-2">
            {dims.map((d, i) => (
              <ScoreBar key={i} label={d.dimension} score={d.score} color={dimColors[i % dimColors.length]} />
            ))}
          </div>
        </div>
      </motion.div>

      {/* Tabs */}
      <div className="flex gap-2">
        {(['overview', 'questions'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`flex-1 py-2.5 rounded-xl text-sm font-medium transition-all ${
              tab === t ? 'bg-violet-500 text-white' : 'bg-white/5 text-slate-400 hover:text-white hover:bg-white/8'
            }`} id={`tab-${t}`}
          >
            {t === 'overview' ? <><BarChart3 className="w-4 h-4 inline mr-1" />Overview</> : <><MessageSquare className="w-4 h-4 inline mr-1" />Per Question</>}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {tab === 'overview' ? (
          <motion.div key="ov" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="glass-card p-5">
                <h3 className="font-outfit font-bold text-emerald-400 flex items-center gap-2 mb-3 text-sm"><TrendingUp className="w-4 h-4" /> Top Strengths</h3>
                <div className="space-y-2">
                  {report.top_strengths.map((s, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 mt-0.5 shrink-0" />
                      <p className="text-sm text-slate-300">{s}</p>
                    </div>
                  ))}
                </div>
              </div>
              <div className="glass-card p-5">
                <h3 className="font-outfit font-bold text-amber-400 flex items-center gap-2 mb-3 text-sm"><Target className="w-4 h-4" /> Areas to Improve</h3>
                <div className="space-y-2">
                  {report.areas_to_improve.map((a, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <AlertCircle className="w-3.5 h-3.5 text-amber-400 mt-0.5 shrink-0" />
                      <p className="text-sm text-slate-300">{a}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {dims.some(d => d.note) && (
              <div className="glass-card p-5 space-y-3">
                <h3 className="font-outfit font-bold text-slate-300 text-sm mb-1">Dimension Feedback</h3>
                {dims.filter(d => d.note).map((d, i) => (
                  <div key={i}>
                    <div className="flex justify-between text-xs mb-0.5">
                      <span className="text-slate-400 font-medium">{d.dimension}</span>
                      <span className="text-white font-bold">{d.score}/100</span>
                    </div>
                    <p className="text-xs text-slate-500 mb-2">{d.note}</p>
                  </div>
                ))}
              </div>
            )}

            <div className="glass-card p-5 border border-violet-500/20 bg-violet-500/5">
              <h4 className="font-semibold text-violet-300 flex items-center gap-2 mb-2 text-sm">
                <Zap className="w-4 h-4" /> Recommended Next Steps
              </h4>
              <p className="text-sm text-slate-300">{report.next_steps}</p>
            </div>
          </motion.div>
        ) : (
          <motion.div key="qs" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-4">
            {evals.map((ev, i) => {
              const q = questions[i]
              if (!q) return null
              const sc = ev.score >= 70 ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/20'
                : ev.score >= 50 ? 'bg-amber-500/15 text-amber-400 border-amber-500/20'
                : 'bg-red-500/15 text-red-400 border-red-500/20'
              return (
                <div key={i} className="glass-card p-5">
                  <div className="flex items-start justify-between gap-4 mb-3">
                    <div className="flex-1">
                      <p className="text-xs text-slate-500 mb-1">Q{i + 1} · {q.topic} · {q.difficulty}</p>
                      <p className="text-sm text-slate-200 font-medium">{q.question}</p>
                    </div>
                    <div className={`border px-3 py-2 rounded-xl text-center shrink-0 ${sc}`}>
                      <span className="font-outfit font-bold text-lg">{ev.score}</span>
                      <p className="text-xs opacity-70">/100</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-4 gap-2 mb-3">
                    {[['Clarity', ev.clarity], ['Depth', ev.depth], ['Relevance', ev.relevance], ['Comm.', ev.communication]].map(([l, v]) => (
                      <div key={l} className="bg-white/5 rounded-lg p-2 text-center">
                        <div className="text-sm font-bold text-white">{v}</div>
                        <div className="text-xs text-slate-500">{l}</div>
                      </div>
                    ))}
                  </div>
                  <p className="text-xs text-slate-400 italic mb-2">{ev.feedback}</p>
                  {ev.positive_points.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-1">
                      {ev.positive_points.map((p, pi) => (
                        <span key={pi} className="text-xs bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded-full">✓ {p}</span>
                      ))}
                    </div>
                  )}
                  {ev.improvement_points.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {ev.improvement_points.map((p, pi) => (
                        <span key={pi} className="text-xs bg-amber-500/10 text-amber-400 px-2 py-0.5 rounded-full">→ {p}</span>
                      ))}
                    </div>
                  )}
                  {ev.ideal_answer_hint && (
                    <p className="text-xs text-violet-400 mt-2 italic">💡 {ev.ideal_answer_hint}</p>
                  )}
                </div>
              )
            })}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex gap-3">
        <button onClick={onRestart} className="btn-ghost flex-1 py-3 text-sm" id="restart-btn">
          <RotateCcw className="w-4 h-4" /> Try Again
        </button>
        <Link to="/candidate" className="btn-primary flex-1 py-3 text-sm text-center flex items-center justify-center gap-2">
          <Cpu className="w-4 h-4" /> Back to Portal
        </Link>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function CandidateInterviewPage() {
  const { user } = useAuthStore()
  const [stage, setStage] = useState<Stage>('upload')
  const [analysis, setAnalysis] = useState<ResumeAnalysis | null>(null)
  const [questions, setQuestions] = useState<InterviewQuestion[]>([])
  const [evals, setEvals] = useState<AnswerEvaluation[]>([])
  const [report, setReport] = useState<InterviewReport | null>(null)
  const [loadingMsg, setLoadingMsg] = useState({ title: '', subtitle: '', step: '' })
  const [jdRef, setJdRef] = useState('')

  // Step 1: Resume submitted → LLM analyze
  const handleUpload = async (resumeText: string, _filename: string, role: string, jd: string) => {
    setJdRef(jd)
    setLoadingMsg({
      title: 'Analyzing Your Resume',
      subtitle: 'Grok 2 AI (xAI) is analyzing your resume and JD...',
      step: 'Detecting experience level, skills, strengths & gaps',
    })
    setStage('analyzing')
    try {
      const res = await analyzeResume(resumeText, role, jd)
      setAnalysis(res)
      setStage('analysis')
    } catch (err) {
      alert(`Analysis failed: ${err instanceof Error ? err.message : err}`)
      setStage('upload')
    }
  }

  // Step 2: User clicks Begin → LLM generate questions
  const handleBegin = async () => {
    if (!analysis) return
    setLoadingMsg({
      title: 'Generating Interview Questions',
      subtitle: 'AI is creating 7 questions tailored to your profile...',
      step: `Experience level: ${analysis.experience_level} · Role: ${analysis.role}`,
    })
    setStage('generating_qs')
    try {
      const qs = await generateInterviewQuestions(analysis, jdRef, 7)
      setQuestions(qs)
      setStage('interview')
    } catch (err) {
      alert(`Question generation failed: ${err instanceof Error ? err.message : err}`)
      setStage('analysis')
    }
  }

  // Step 3: All answers submitted → LLM generate report
  const handleInterviewComplete = async (answeredEvals: AnswerEvaluation[]) => {
    if (!analysis) return
    setEvals(answeredEvals)
    setLoadingMsg({
      title: 'Generating Final Report',
      subtitle: 'AI is analyzing all your answers and compiling your report...',
      step: `Evaluated ${answeredEvals.length} answers · Calculating scores`,
    })
    setStage('generating_report')
    try {
      const r = await generateFinalReport(analysis, questions, answeredEvals)
      setReport(r)
      setStage('results')
    } catch (err) {
      alert(`Report generation failed: ${err instanceof Error ? err.message : err}`)
      setStage('results')
      // Still show results with whatever we have
      setReport({
        overall_score: Math.round(answeredEvals.reduce((s, e) => s + e.score, 0) / answeredEvals.length),
        grade: 'B', recommendation: 'Consider',
        technical_score: 60, communication_score: 60, problem_solving_score: 60, cultural_fit_score: 70,
        summary: 'Report could not be fully generated. Showing available data.',
        top_strengths: [], areas_to_improve: [],
        next_steps: 'Review per-question results in the Questions tab.',
        per_dimension_feedback: [],
      })
    }
  }

  const handleRestart = () => {
    setStage('upload')
    setAnalysis(null)
    setQuestions([])
    setEvals([])
    setReport(null)
    setJdRef('')
  }

  const stepLabels = [
    { id: 'upload', label: 'Upload', icon: <Upload className="w-3 h-3" /> },
    { id: 'analysis', label: 'Analysis', icon: <Brain className="w-3 h-3" /> },
    { id: 'interview', label: 'Interview', icon: <Mic className="w-3 h-3" /> },
    { id: 'results', label: 'Results', icon: <Award className="w-3 h-3" /> },
  ]
  const stageToStep: Record<string, string> = {
    upload: 'upload', analyzing: 'upload', analysis: 'analysis', generating_qs: 'analysis',
    interview: 'interview', evaluating: 'interview', generating_report: 'interview', results: 'results',
  }
  const stageOrder = ['upload', 'analysis', 'interview', 'results']
  const currentStep = stageToStep[stage] || 'upload'

  const isLoading = ['analyzing', 'generating_qs', 'generating_report'].includes(stage)

  return (
    <div className="min-h-screen py-10 px-4">
      {/* Nav */}
      <div className="max-w-3xl mx-auto mb-8 flex items-center justify-between">
        <Link to="/candidate" className="flex items-center gap-2 text-white font-outfit font-bold">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
            <Cpu className="w-4 h-4 text-white" />
          </div>
          TalentAI
        </Link>
        {user && (
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <div className="w-6 h-6 rounded-full bg-violet-500/30 flex items-center justify-center text-violet-300 text-xs font-bold">
              {user.full_name?.[0]}
            </div>
            {user.full_name}
          </div>
        )}
      </div>

      {/* Step tracker */}
      <div className="max-w-3xl mx-auto mb-10 flex items-center justify-center gap-0">
        {stepLabels.map((s, i) => {
          const idx = stageOrder.indexOf(s.id)
          const cur = stageOrder.indexOf(currentStep)
          const done = idx < cur
          const active = s.id === currentStep
          return (
            <div key={s.id} className="flex items-center">
              <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                active ? 'bg-violet-500 text-white' : done ? 'text-emerald-400' : 'text-slate-500'
              }`}>
                {done ? <CheckCircle2 className="w-3 h-3" /> : s.icon}
                <span className="hidden sm:inline">{s.label}</span>
              </div>
              {i < stepLabels.length - 1 && (
                <div className={`w-8 h-px mx-1 ${done ? 'bg-emerald-500/40' : 'bg-white/10'}`} />
              )}
            </div>
          )
        })}
      </div>

      {/* Stage renderer */}
      <AnimatePresence mode="wait">
        <motion.div
          key={stage}
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -15 }}
          transition={{ duration: 0.25 }}
        >
          {isLoading && (
            <LLMLoading {...loadingMsg} />
          )}
          {stage === 'upload' && (
            <UploadStep onSubmit={handleUpload} ollamaModel="Grok 2 AI" />
          )}
          {stage === 'analysis' && analysis && (
            <AnalysisStep analysis={analysis} onStart={handleBegin} />
          )}
          {stage === 'interview' && analysis && questions.length > 0 && (
            <InterviewStep questions={questions} analysis={analysis} onComplete={handleInterviewComplete} />
          )}
          {stage === 'results' && report && analysis && (
            <ResultsStep report={report} evals={evals} questions={questions} analysis={analysis} onRestart={handleRestart} />
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
