import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Mic, MicOff, Send, Brain, ChevronRight, CheckCircle2,
  Clock, Loader2, Volume2, AlertCircle, BarChart3, User, Cpu
} from 'lucide-react'

type InterviewPhase = 'intro' | 'interviewing' | 'evaluating' | 'completed'
type MessageRole = 'interviewer' | 'candidate'

interface Message {
  id: string
  role: MessageRole
  text: string
  questionType?: string
  topic?: string
  evaluation?: {
    correctness: number
    depth: number
    clarity: number
  }
}

// Demo data — will be backed by WebSocket + LangGraph in production
const demoMessages: Message[] = [
  {
    id: '1',
    role: 'interviewer',
    text: "Welcome! I'm your AI interviewer today. I've reviewed your resume and I'll be asking you questions tailored to your experience. Let's start with something from your work at Scale AI.",
    questionType: 'introduction',
    topic: 'Introduction',
  },
  {
    id: '2',
    role: 'interviewer',
    text: "You mentioned building an RLHF pipeline at Scale AI. Can you walk me through the architecture? Specifically, how did you handle reward model training stability and what techniques did you use to prevent reward hacking?",
    questionType: 'experience_deep_dive',
    topic: 'RLHF',
  },
]

export default function InterviewPage() {
  const [phase, setPhase] = useState<InterviewPhase>('intro')
  const [messages, setMessages] = useState<Message[]>([])
  const [textInput, setTextInput] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const [isThinking, setIsThinking] = useState(false)
  const [questionNumber, setQuestionNumber] = useState(0)
  const [difficulty, setDifficulty] = useState<'easy' | 'medium' | 'hard'>('medium')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isThinking])

  const startInterview = () => {
    setPhase('interviewing')
    setMessages([demoMessages[0]])
    setTimeout(() => {
      setIsThinking(true)
      setTimeout(() => {
        setIsThinking(false)
        setMessages((prev) => [...prev, demoMessages[1]])
        setQuestionNumber(1)
      }, 1500)
    }, 800)
  }

  const submitAnswer = (text: string) => {
    if (!text.trim()) return
    const answer: Message = { id: Date.now().toString(), role: 'candidate', text }
    setMessages((prev) => [...prev, answer])
    setTextInput('')
    setIsThinking(true)

    // Simulate AI generating next question
    setTimeout(() => {
      setIsThinking(false)
      if (questionNumber >= 5) {
        setPhase('completed')
        return
      }
      const nextQ: Message = {
        id: Date.now().toString() + '-q',
        role: 'interviewer',
        text: questionNumber === 1
          ? "Excellent explanation! Let me dig deeper. In your PyTorch LLM fine-tuning work — if you had a GPU cluster losing 15% throughput mid-training run, how would you systematically diagnose whether it's a compute, memory, or network bottleneck?"
          : "Thanks for that thorough answer. One final question: describe the most technically challenging bug you've debugged in a distributed ML system. Walk me through your debugging methodology.",
        questionType: 'technical_fundamentals',
        topic: 'Systems Debugging',
      }
      setMessages((prev) => [...prev, nextQ])
      setQuestionNumber((n) => n + 1)
      if (questionNumber === 2) setDifficulty('hard')
    }, 2000)
  }

  const difficultyColor = { easy: 'text-emerald-400', medium: 'text-amber-400', hard: 'text-red-400' }

  return (
    <div className="min-h-screen bg-[#060B18] flex flex-col">
      {/* Header */}
      <header className="border-b border-white/5 bg-[#0A1022]/80 backdrop-blur px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
            <Cpu className="w-4 h-4 text-white" />
          </div>
          <div>
            <p className="font-semibold text-white text-sm">TalentAI Interview</p>
            <p className="text-xs text-slate-500">Senior ML Engineer · Scale AI Application</p>
          </div>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-1.5 text-slate-400">
            <ChevronRight className="w-3.5 h-3.5" />
            <span>Q{questionNumber}/8</span>
          </div>
          <div className={`flex items-center gap-1.5 ${difficultyColor[difficulty]}`}>
            <BarChart3 className="w-3.5 h-3.5" />
            <span className="capitalize">{difficulty}</span>
          </div>
          <div className="w-24 h-1.5 bg-white/5 rounded-full">
            <motion.div
              className="h-full bg-violet-500 rounded-full"
              animate={{ width: `${(questionNumber / 8) * 100}%` }}
            />
          </div>
        </div>
      </header>

      {/* Chat area */}
      <main className="flex-1 overflow-y-auto px-4 py-6 max-w-3xl mx-auto w-full">
        <AnimatePresence mode="popLayout">
          {phase === 'intro' && (
            <motion.div
              key="intro"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="glass-card p-10 text-center mt-12"
            >
              <div className="w-20 h-20 rounded-full bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center mx-auto mb-6 animate-glow">
                <Brain className="w-10 h-10 text-white" />
              </div>
              <h1 className="font-outfit text-2xl font-bold text-white mb-3">
                Your AI Interview is Ready
              </h1>
              <p className="text-slate-400 mb-6 leading-relaxed max-w-md mx-auto">
                This is an adaptive interview. Questions will adjust to your answers —
                strong responses increase difficulty, weaker ones invite clarification.
                You can type or speak your answers.
              </p>
              <div className="grid grid-cols-3 gap-4 mb-8 text-sm">
                {[
                  { icon: Brain, label: '8 Questions', desc: 'Adaptive depth' },
                  { icon: Mic, label: 'Voice or Text', desc: 'Your choice' },
                  { icon: BarChart3, label: '5 Dimensions', desc: 'Scored' },
                ].map((item) => (
                  <div key={item.label} className="glass-card p-4 text-center">
                    <item.icon className="w-5 h-5 text-violet-400 mx-auto mb-2" />
                    <div className="text-white font-medium">{item.label}</div>
                    <div className="text-slate-500 text-xs">{item.desc}</div>
                  </div>
                ))}
              </div>
              <button
                onClick={startInterview}
                className="btn-primary px-10 py-4 text-lg"
                id="start-interview"
              >
                Begin Interview
                <ChevronRight className="w-5 h-5" />
              </button>
            </motion.div>
          )}

          {(phase === 'interviewing' || phase === 'evaluating') && (
            <div className="space-y-5">
              {messages.map((msg) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex gap-3 ${msg.role === 'candidate' ? 'justify-end' : 'justify-start'}`}
                >
                  {msg.role === 'interviewer' && (
                    <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shrink-0">
                      <Brain className="w-4 h-4 text-white" />
                    </div>
                  )}
                  <div className={`max-w-[80%] rounded-2xl px-5 py-4 ${
                    msg.role === 'interviewer'
                      ? 'glass-card border-violet-500/10'
                      : 'bg-violet-600 text-white'
                  }`}>
                    {msg.questionType && (
                      <p className="text-xs text-violet-400 mb-1.5 font-medium uppercase tracking-wide">
                        {msg.topic}
                      </p>
                    )}
                    <p className={`text-sm leading-relaxed ${msg.role === 'interviewer' ? 'text-slate-200' : 'text-white'}`}>
                      {msg.text}
                    </p>
                  </div>
                  {msg.role === 'candidate' && (
                    <div className="w-9 h-9 rounded-xl bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center shrink-0">
                      <User className="w-4 h-4 text-emerald-400" />
                    </div>
                  )}
                </motion.div>
              ))}

              {isThinking && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex gap-3"
                >
                  <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
                    <Brain className="w-4 h-4 text-white" />
                  </div>
                  <div className="glass-card px-5 py-4 flex items-center gap-2">
                    <Loader2 className="w-4 h-4 text-violet-400 animate-spin" />
                    <span className="text-slate-400 text-sm">Thinking...</span>
                  </div>
                </motion.div>
              )}

              <div ref={bottomRef} />
            </div>
          )}

          {phase === 'completed' && (
            <motion.div
              key="completed"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass-card p-10 text-center mt-8"
            >
              <CheckCircle2 className="w-16 h-16 text-emerald-400 mx-auto mb-4 animate-float" />
              <h2 className="font-outfit text-2xl font-bold text-white mb-2">Interview Complete!</h2>
              <p className="text-slate-400 mb-6">
                Your answers are being evaluated. You'll receive a detailed report shortly.
              </p>
              <div className="grid grid-cols-3 gap-4 mb-8">
                {[
                  { label: 'Questions Answered', value: '6' },
                  { label: 'Topics Covered', value: '4' },
                  { label: 'Final Difficulty', value: 'Hard' },
                ].map((item) => (
                  <div key={item.label} className="glass-card p-4 text-center">
                    <div className="font-outfit text-2xl font-black text-white">{item.value}</div>
                    <div className="text-xs text-slate-500 mt-1">{item.label}</div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Input area */}
      {(phase === 'interviewing') && !isThinking && (
        <footer className="border-t border-white/5 bg-[#0A1022]/80 backdrop-blur px-4 py-4">
          <div className="max-w-3xl mx-auto flex gap-3 items-end">
            <div className="flex-1">
              <textarea
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    submitAnswer(textInput)
                  }
                }}
                placeholder="Type your answer... (Shift+Enter for new line)"
                className="input-field min-h-[80px] resize-none"
                id="interview-answer-input"
              />
            </div>
            <div className="flex flex-col gap-2 pb-0.5">
              <button
                onClick={() => setIsRecording(!isRecording)}
                className={`p-3 rounded-xl border transition-all ${
                  isRecording
                    ? 'bg-red-500/20 border-red-500/30 text-red-400'
                    : 'btn-ghost'
                }`}
                title="Voice input"
                id="toggle-recording"
              >
                {isRecording ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
              </button>
              <button
                onClick={() => submitAnswer(textInput)}
                disabled={!textInput.trim()}
                className="btn-primary p-3"
                id="submit-answer"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        </footer>
      )}
    </div>
  )
}
