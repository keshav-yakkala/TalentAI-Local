import { useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Upload, Search, Filter, User, CheckCircle2, Clock, AlertCircle,
  FileText, Loader2, X, ChevronRight, TrendingUp, Star, Brain
} from 'lucide-react'
import { useUploadResume } from '@/api/hooks'
import type { ParsingStatus } from '@/types'

// Mock candidates for demo — replaced with API in production
const mockCandidates = [
  {
    id: '1', full_name: 'Sarah Chen', email: 'sarah@example.com', location: 'San Francisco',
    score: 87, recommendation: 'strong_match', parsing_status: 'completed' as ParsingStatus,
    job: 'Senior ML Engineer', applied: '2025-01-13',
    skills: ['Python', 'PyTorch', 'FastAPI', 'LLMs'],
  },
  {
    id: '2', full_name: 'Marcus Johnson', email: 'marcus@example.com', location: 'New York',
    score: 72, recommendation: 'potential_match', parsing_status: 'completed' as ParsingStatus,
    job: 'Full-Stack Engineer', applied: '2025-01-12',
    skills: ['React', 'TypeScript', 'Node.js'],
  },
  {
    id: '3', full_name: 'Priya Sharma', email: 'priya@example.com', location: 'Bangalore',
    score: 0, recommendation: 'pending', parsing_status: 'embedding' as ParsingStatus,
    job: 'Product Manager', applied: '2025-01-14',
    skills: [],
  },
  {
    id: '4', full_name: 'Alex Kim', email: 'alex@example.com', location: 'Remote',
    score: 45, recommendation: 'needs_human_review', parsing_status: 'completed' as ParsingStatus,
    job: 'DevOps Engineer', applied: '2025-01-11',
    skills: ['AWS', 'Kubernetes', 'Terraform'],
  },
]

const statusConfig: Record<ParsingStatus, { label: string; color: string; icon: typeof CheckCircle2 }> = {
  pending: { label: 'Pending', color: 'text-slate-400', icon: Clock },
  parsing: { label: 'Parsing', color: 'text-blue-400', icon: Loader2 },
  extracting: { label: 'Extracting', color: 'text-violet-400', icon: Brain },
  embedding: { label: 'Embedding', color: 'text-amber-400', icon: Loader2 },
  completed: { label: 'Screened', color: 'text-emerald-400', icon: CheckCircle2 },
  failed: { label: 'Failed', color: 'text-red-400', icon: AlertCircle },
  human_review_required: { label: 'Review Needed', color: 'text-amber-400', icon: AlertCircle },
}

const recommendationBadge: Record<string, string> = {
  strong_match: 'score-badge strong',
  potential_match: 'score-badge potential',
  needs_human_review: 'score-badge review',
  weak_match: 'score-badge weak',
  pending: 'score-badge bg-slate-500/20 text-slate-400 border border-slate-500/30',
}

function UploadDropzone() {
  const [isDragging, setIsDragging] = useState(false)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const { mutate: upload, isPending, isSuccess, isError } = useUploadResume()

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) {
      setUploadedFile(file)
      upload({ file })
    }
  }, [upload])

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setUploadedFile(file)
      upload({ file })
    }
  }

  return (
    <div
      className={`relative rounded-2xl border-2 border-dashed p-8 text-center transition-all duration-300 ${
        isDragging
          ? 'border-violet-500 bg-violet-500/10'
          : 'border-white/10 bg-white/2 hover:border-violet-500/40 hover:bg-white/5'
      }`}
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
    >
      <input
        type="file"
        accept=".pdf,.docx,.txt"
        onChange={handleFileInput}
        className="absolute inset-0 opacity-0 cursor-pointer"
        id="resume-upload-input"
      />

      {isSuccess ? (
        <div className="space-y-2">
          <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto" />
          <p className="text-white font-medium">Resume uploaded!</p>
          <p className="text-slate-400 text-sm">AI is parsing and indexing in the background</p>
        </div>
      ) : isPending ? (
        <div className="space-y-2">
          <Loader2 className="w-10 h-10 text-violet-400 mx-auto animate-spin" />
          <p className="text-white font-medium">Uploading {uploadedFile?.name}...</p>
        </div>
      ) : (
        <div className="space-y-3">
          <Upload className="w-10 h-10 text-slate-500 mx-auto" />
          <div>
            <p className="text-white font-medium">Drop resume here or click to browse</p>
            <p className="text-slate-500 text-sm mt-1">PDF, DOCX, or TXT · Max 20MB</p>
          </div>
          {isError && (
            <p className="text-red-400 text-sm">Upload failed. Please try again.</p>
          )}
        </div>
      )}
    </div>
  )
}

export default function CandidatesPage() {
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<string>('all')
  const [showUpload, setShowUpload] = useState(false)

  const filtered = mockCandidates.filter((c) => {
    const matchSearch = c.full_name.toLowerCase().includes(search.toLowerCase()) ||
      c.email.toLowerCase().includes(search.toLowerCase())
    const matchFilter = filter === 'all' || c.recommendation === filter
    return matchSearch && matchFilter
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="font-outfit text-2xl font-bold text-white">Candidates</h1>
          <p className="text-slate-400 text-sm mt-1">{mockCandidates.length} candidates across all jobs</p>
        </div>
        <button
          onClick={() => setShowUpload(!showUpload)}
          className="btn-primary px-5 py-2.5 text-sm"
          id="toggle-upload"
        >
          <Upload className="w-4 h-4" />
          Upload Resume
        </button>
      </div>

      {/* Upload dropzone */}
      <AnimatePresence>
        {showUpload && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="glass-card p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold text-white">Upload Candidate Resume</h2>
                <button onClick={() => setShowUpload(false)} className="text-slate-500 hover:text-white">
                  <X className="w-4 h-4" />
                </button>
              </div>
              <UploadDropzone />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Search + Filter */}
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input-field pl-11"
            placeholder="Search candidates..."
            id="candidates-search"
          />
        </div>
        <div className="flex gap-2">
          {(['all', 'strong_match', 'potential_match', 'needs_human_review']).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${
                filter === f ? 'bg-violet-500 text-white' : 'btn-ghost'
              }`}
            >
              {f === 'all' ? 'All' : f.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Candidate cards */}
      <div className="space-y-3">
        <AnimatePresence>
          {filtered.map((candidate, i) => {
            const status = statusConfig[candidate.parsing_status]
            const StatusIcon = status.icon
            return (
              <motion.div
                key={candidate.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ delay: i * 0.04 }}
                className="glass-card p-5 hover:border-violet-500/20 transition-all"
              >
                <div className="flex items-center gap-5">
                  {/* Avatar */}
                  <div className="w-12 h-12 rounded-full bg-gradient-to-br from-violet-400 to-purple-600 flex items-center justify-center text-lg font-bold text-white shrink-0">
                    {candidate.full_name[0]}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start gap-3 flex-wrap">
                      <h3 className="font-semibold text-white">{candidate.full_name}</h3>
                      <span className={recommendationBadge[candidate.recommendation]}>
                        {candidate.recommendation.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 mt-1 text-sm text-slate-400 flex-wrap">
                      <span>{candidate.email}</span>
                      <span>{candidate.location}</span>
                      <span className="text-slate-600">→</span>
                      <span className="text-slate-300">{candidate.job}</span>
                    </div>
                    {candidate.skills.length > 0 && (
                      <div className="flex gap-1.5 mt-2 flex-wrap">
                        {candidate.skills.slice(0, 4).map((s) => (
                          <span key={s} className="px-2 py-0.5 rounded-md bg-white/5 text-slate-400 text-xs">{s}</span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Score + Status */}
                  <div className="shrink-0 text-right space-y-2">
                    {candidate.score > 0 ? (
                      <div>
                        <div className={`font-outfit text-2xl font-black ${
                          candidate.score >= 75 ? 'text-emerald-400' :
                          candidate.score >= 55 ? 'text-blue-400' :
                          'text-amber-400'
                        }`}>{candidate.score}</div>
                        <div className="text-xs text-slate-500">/ 100</div>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1.5 text-sm">
                        <StatusIcon className={`w-4 h-4 ${status.color} ${candidate.parsing_status === 'embedding' || candidate.parsing_status === 'parsing' ? 'animate-spin' : ''}`} />
                        <span className={status.color}>{status.label}</span>
                      </div>
                    )}
                    <Link
                      to={`/recruiter/candidates/${candidate.id}`}
                      className="flex items-center gap-1 text-xs text-violet-400 hover:text-violet-300"
                    >
                      View Profile <ChevronRight className="w-3 h-3" />
                    </Link>
                  </div>
                </div>
              </motion.div>
            )
          })}
        </AnimatePresence>

        {filtered.length === 0 && (
          <div className="glass-card p-12 text-center">
            <User className="w-10 h-10 text-slate-600 mx-auto mb-3" />
            <p className="text-white font-medium">No candidates found</p>
            <p className="text-slate-500 text-sm mt-1">Try adjusting your filters or upload a resume</p>
          </div>
        )}
      </div>
    </div>
  )
}
