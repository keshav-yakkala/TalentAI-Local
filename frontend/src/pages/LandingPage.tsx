import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Brain, FileText, Users, MessageSquare, BarChart3,
  Shield, Zap, ChevronRight, Star, ArrowRight, CheckCircle2,
  Cpu, Network, Search
} from 'lucide-react'

const features = [
  {
    icon: Brain,
    title: 'AI Resume Intelligence',
    description: 'Multi-dimensional structured extraction using LLM + Pydantic validation. Skills, experience, projects — all parsed and verified.',
    color: 'from-violet-500 to-purple-600',
    glow: 'rgba(124, 58, 237, 0.3)',
  },
  {
    icon: Search,
    title: 'RAG-Powered Screening',
    description: 'Evidence-based candidate scoring backed by semantic search. Every score is grounded in actual resume evidence, not guesswork.',
    color: 'from-blue-500 to-cyan-600',
    glow: 'rgba(59, 130, 246, 0.3)',
  },
  {
    icon: MessageSquare,
    title: 'Adaptive AI Interviews',
    description: 'Stateful interviews that adapt in real-time. Strong answers increase difficulty; weak answers trigger clarification. Voice or text.',
    color: 'from-emerald-500 to-teal-600',
    glow: 'rgba(16, 185, 129, 0.3)',
  },
  {
    icon: BarChart3,
    title: 'Explainable Scoring',
    description: 'Weighted category scores — technical, experience, projects, education. AI provides evidence; humans make the final call.',
    color: 'from-orange-500 to-amber-600',
    glow: 'rgba(245, 158, 11, 0.3)',
  },
  {
    icon: Network,
    title: 'LangGraph Workflows',
    description: 'All AI operations run as persistent, resumable LangGraph workflows. Paused interviews resume. Failed parsing routes to human review.',
    color: 'from-pink-500 to-rose-600',
    glow: 'rgba(236, 72, 153, 0.3)',
  },
  {
    icon: Shield,
    title: 'Privacy & Security',
    description: 'Strict multi-tenant isolation. Organization A cannot see Organization B data — enforced at the database level, not just in prompts.',
    color: 'from-slate-500 to-zinc-600',
    glow: 'rgba(100, 116, 139, 0.3)',
  },
]

const stats = [
  { value: '10x', label: 'Faster Screening' },
  { value: '95%', label: 'Evidence Rate' },
  { value: '100%', label: 'Human Authority' },
  { value: 'Zero', label: 'Data Leakage' },
]

const steps = [
  { num: '01', title: 'Upload Resumes', desc: 'PDF or DOCX. Bulk upload supported. AI parses and indexes automatically in the background.' },
  { num: '02', title: 'Paste Your JD', desc: 'Paste or upload a job description. AI extracts structured requirements for screening.' },
  { num: '03', title: 'AI Screens Candidates', desc: 'LangGraph-powered screening with evidence-based scoring across 7 weighted categories.' },
  { num: '04', title: 'Conduct AI Interviews', desc: 'Adaptive interviews with voice support. One question at a time, dynamically adjusted.' },
  { num: '05', title: 'Review & Decide', desc: 'Full evidence reports. AI recommends — you decide. Human authority is always preserved.' },
]

export default function LandingPage() {
  return (
    <div className="min-h-screen overflow-x-hidden">
      {/* Navigation */}
      <nav className="fixed top-0 inset-x-0 z-50 border-b border-white/5 bg-[#060B18]/80 backdrop-blur-xl">
        <div className="mx-auto max-w-7xl px-6 flex items-center justify-between h-16">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
              <Cpu className="w-4 h-4 text-white" />
            </div>
            <span className="font-outfit font-bold text-lg tracking-tight text-white">TalentAI</span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm text-slate-400">
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="#how-it-works" className="hover:text-white transition-colors">How it works</a>
            <a href="#security" className="hover:text-white transition-colors">Security</a>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/login" className="text-sm text-slate-400 hover:text-white transition-colors font-medium">Sign in</Link>
            <Link
              to="/register"
              className="btn-primary px-5 py-2.5 text-sm"
            >
              Get started free
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative pt-36 pb-24 px-6">
        {/* Background orbs */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-40 left-1/2 -translate-x-1/2 w-[800px] h-[800px] rounded-full opacity-20"
            style={{ background: 'radial-gradient(circle, rgba(124,58,237,0.4) 0%, transparent 70%)' }} />
          <div className="absolute top-60 right-0 w-[400px] h-[400px] rounded-full opacity-10"
            style={{ background: 'radial-gradient(circle, rgba(6,214,160,0.5) 0%, transparent 70%)' }} />
        </div>

        <div className="relative mx-auto max-w-5xl text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="inline-flex items-center gap-2 rounded-full border border-violet-500/30 bg-violet-500/10 px-4 py-2 text-xs text-violet-300 font-medium mb-8">
              <Zap className="w-3 h-3" />
              Powered by LangGraph + RAG + Whisper
            </div>

            <h1 className="font-outfit text-5xl md:text-7xl font-black tracking-tight mb-6 leading-none">
              <span className="gradient-text">AI-Powered</span>
              <br />
              <span className="text-white">Recruitment Intelligence</span>
            </h1>

            <p className="text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed">
              From resume parsing to adaptive AI interviews — TalentAI gives your team
              evidence-based insights while keeping humans in control of every hiring decision.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link to="/register?role=recruiter" className="btn-primary px-8 py-4 text-base w-full sm:w-auto">
                Start hiring smarter
                <ArrowRight className="w-4 h-4" />
              </Link>
              <Link to="/register?role=candidate" className="btn-ghost px-8 py-4 text-base w-full sm:w-auto">
                Apply as a candidate
              </Link>
            </div>
          </motion.div>

          {/* Stats */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="mt-20 grid grid-cols-2 md:grid-cols-4 gap-6"
          >
            {stats.map((stat) => (
              <div key={stat.label} className="glass-card p-6">
                <div className="font-outfit text-3xl font-black gradient-text-purple mb-1">{stat.value}</div>
                <div className="text-sm text-slate-500">{stat.label}</div>
              </div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-24 px-6">
        <div className="mx-auto max-w-7xl">
          <div className="text-center mb-16">
            <h2 className="font-outfit text-4xl font-bold text-white mb-4">
              Production-grade AI recruitment
            </h2>
            <p className="text-slate-400 text-lg max-w-xl mx-auto">
              Built with LangGraph, RAG pipelines, and pgvector — not just another chatbot wrapper.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, i) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                className="glass-card p-6 group hover:scale-[1.02] transition-transform duration-300"
                style={{ boxShadow: `0 0 40px ${feature.glow}` }}
              >
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${feature.color} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300`}>
                  <feature.icon className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-white font-semibold text-lg mb-2">{feature.title}</h3>
                <p className="text-slate-400 text-sm leading-relaxed">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="py-24 px-6 border-t border-white/5">
        <div className="mx-auto max-w-4xl">
          <div className="text-center mb-16">
            <h2 className="font-outfit text-4xl font-bold text-white mb-4">How TalentAI works</h2>
            <p className="text-slate-400 text-lg">Five steps from resume upload to confident hiring decision</p>
          </div>

          <div className="space-y-8">
            {steps.map((step, i) => (
              <motion.div
                key={step.num}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                className="flex gap-6 glass-card p-6"
              >
                <div className="shrink-0 font-outfit text-4xl font-black gradient-text-purple opacity-60">{step.num}</div>
                <div>
                  <h3 className="text-white font-semibold text-lg mb-1">{step.title}</h3>
                  <p className="text-slate-400 text-sm leading-relaxed">{step.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Security */}
      <section id="security" className="py-24 px-6">
        <div className="mx-auto max-w-4xl">
          <div className="glass-card p-12 text-center border-violet-500/20"
            style={{ background: 'linear-gradient(135deg, rgba(124,58,237,0.1) 0%, rgba(6,214,160,0.05) 100%)' }}>
            <Shield className="w-16 h-16 text-violet-400 mx-auto mb-6 animate-float" />
            <h2 className="font-outfit text-3xl font-bold text-white mb-4">Built for enterprise security</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-8 text-left">
              {[
                'Multi-tenant data isolation enforced at database level',
                'JWT authentication with bcrypt password hashing',
                'No eval() — all LLM outputs validated with Pydantic',
                'Cross-tenant access attempts logged as CRITICAL',
                'Organization ID never trusted from client requests',
                'Audit log for every sensitive action',
              ].map((item) => (
                <div key={item} className="flex items-start gap-3">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                  <span className="text-slate-300 text-sm">{item}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 px-6 border-t border-white/5">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="font-outfit text-4xl font-bold text-white mb-4">
            Ready to transform your recruitment?
          </h2>
          <p className="text-slate-400 text-lg mb-10">
            TalentAI handles the analysis. You make the decisions.
          </p>
          <Link to="/register?role=recruiter" className="btn-primary px-10 py-5 text-lg inline-flex">
            Get started for free
            <ChevronRight className="w-5 h-5" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 py-12 px-6">
        <div className="mx-auto max-w-7xl flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
              <Cpu className="w-3 h-3 text-white" />
            </div>
            <span className="font-outfit font-bold text-white">TalentAI</span>
          </div>
          <p className="text-slate-500 text-sm">AI-powered recruitment intelligence from resume to interview.</p>
          <p className="text-slate-600 text-xs">© 2025 TalentAI. Built with LangGraph + FastAPI + React.</p>
        </div>
      </footer>
    </div>
  )
}
