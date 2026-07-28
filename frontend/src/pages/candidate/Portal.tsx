/**
 * TalentAI — Candidate Portal
 * Landing page for candidates after login — shows interview options
 */
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import {
  Brain, Mic, FileText, Award, ArrowRight, Cpu,
  CheckCircle2, Zap, BarChart3, LogOut
} from 'lucide-react'
import { useAuthStore } from '@/store/auth'

const steps = [
  { icon: FileText, color: 'from-violet-500 to-purple-600', label: 'Upload Resume', desc: 'PDF, DOCX, or TXT — we parse it instantly.' },
  { icon: Brain, color: 'from-blue-500 to-cyan-600', label: 'AI Screening', desc: 'Get strengths, weaknesses, and fit score in seconds.' },
  { icon: Mic, color: 'from-pink-500 to-rose-600', label: 'Voice Interview', desc: 'Answer questions by voice — just like a real interview.' },
  { icon: Award, color: 'from-amber-500 to-orange-600', label: 'Get Results', desc: 'Receive a detailed score report with feedback.' },
]

export default function CandidatePortal() {
  const { user, logout } = useAuthStore()

  return (
    <div className="min-h-screen py-10 px-4">
      {/* Nav */}
      <div className="max-w-4xl mx-auto mb-12 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 text-white font-outfit font-bold text-lg">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
            <Cpu className="w-5 h-5 text-white" />
          </div>
          TalentAI
        </Link>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10">
            <div className="w-5 h-5 rounded-full bg-violet-500 flex items-center justify-center text-xs font-bold text-white">
              {user?.full_name?.[0] || 'C'}
            </div>
            <span className="text-sm text-slate-300">{user?.full_name}</span>
          </div>
          <button
            onClick={logout}
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
            title="Sign out"
            id="candidate-logout-btn"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="max-w-4xl mx-auto">
        {/* Hero */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-16"
        >
          <div className="inline-flex items-center gap-2 bg-violet-500/10 border border-violet-500/20 rounded-full px-4 py-2 mb-6">
            <Zap className="w-4 h-4 text-violet-400" />
            <span className="text-sm text-violet-300 font-medium">AI-Powered Interview Platform</span>
          </div>
          <h1 className="font-outfit text-5xl font-black text-white mb-4 leading-tight">
            Welcome back,<br />
            <span className="bg-gradient-to-r from-violet-400 to-purple-400 bg-clip-text text-transparent">
              {user?.full_name?.split(' ')[0] || 'Candidate'}! 👋
            </span>
          </h1>
          <p className="text-slate-400 text-lg max-w-xl mx-auto">
            Upload your resume, get AI feedback, and practice your interview with voice answers — all in one place.
          </p>
        </motion.div>

        {/* CTA */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1 }}
          className="glass-card p-10 text-center mb-12 border border-violet-500/20"
          style={{ boxShadow: '0 0 80px rgba(124,58,237,0.15)' }}
        >
          <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center mx-auto mb-6">
            <Brain className="w-10 h-10 text-white" />
          </div>
          <h2 className="font-outfit text-2xl font-bold text-white mb-3">
            Start AI Interview
          </h2>
          <p className="text-slate-400 mb-8 max-w-md mx-auto">
            Upload your resume and job details. Our AI will analyze your profile and conduct a live interview — answerable by voice or text.
          </p>
          <Link
            to="/candidate/interview"
            id="start-interview-link"
            className="btn-primary inline-flex items-center gap-2 px-10 py-4 text-base"
          >
            <Mic className="w-5 h-5" /> Start Interview Now
            <ArrowRight className="w-4 h-4" />
          </Link>
        </motion.div>

        {/* How it works */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <h3 className="font-outfit text-xl font-bold text-white text-center mb-6">How It Works</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {steps.map((s, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 * i + 0.3 }}
                className="glass-card p-5 text-center"
              >
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${s.color} flex items-center justify-center mx-auto mb-3`}>
                  <s.icon className="w-6 h-6 text-white" />
                </div>
                <div className="text-xs text-slate-500 font-medium mb-1">Step {i + 1}</div>
                <p className="text-sm font-semibold text-white mb-1">{s.label}</p>
                <p className="text-xs text-slate-400">{s.desc}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Features */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-4"
        >
          {[
            { icon: Mic, label: 'Voice Recognition', desc: 'Answer naturally by speaking — just like a real interview.' },
            { icon: BarChart3, label: 'Detailed Scores', desc: 'Per-question clarity, depth, and relevance scoring.' },
            { icon: CheckCircle2, label: 'AI Feedback', desc: 'Actionable improvements for every answer you give.' },
          ].map((f, i) => (
            <div key={i} className="flex items-start gap-4 p-5 rounded-xl bg-white/[0.03] border border-white/[0.06]">
              <div className="w-9 h-9 rounded-lg bg-violet-500/15 flex items-center justify-center shrink-0">
                <f.icon className="w-4 h-4 text-violet-400" />
              </div>
              <div>
                <p className="text-sm font-semibold text-white mb-0.5">{f.label}</p>
                <p className="text-xs text-slate-400">{f.desc}</p>
              </div>
            </div>
          ))}
        </motion.div>
      </div>
    </div>
  )
}
