import { Link } from 'react-router-dom'
import { Plus, Search, Briefcase, MapPin, Clock, Users } from 'lucide-react'
import { motion } from 'framer-motion'

const mockJobs = [
  { id: '1', title: 'Senior Full-Stack Engineer', department: 'Engineering', location: 'Remote', status: 'active', applicants: 47, created_at: '2025-01-10' },
  { id: '2', title: 'ML Engineer — NLP', department: 'AI/ML', location: 'Hyderabad', status: 'active', applicants: 23, created_at: '2025-01-08' },
  { id: '3', title: 'Product Manager', department: 'Product', location: 'Bangalore', status: 'paused', applicants: 89, created_at: '2025-01-05' },
  { id: '4', title: 'DevOps Engineer', department: 'Platform', location: 'Remote', status: 'draft', applicants: 0, created_at: '2025-01-12' },
]

const statusColor: Record<string, string> = {
  active: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  paused: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  draft: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
  closed: 'bg-red-500/20 text-red-400 border-red-500/30',
}

export default function JobsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-outfit text-2xl font-bold text-white">Job Postings</h1>
          <p className="text-slate-400 text-sm mt-1">{mockJobs.length} positions across all departments</p>
        </div>
        <Link to="/recruiter/jobs/new" className="btn-primary px-5 py-2.5 text-sm">
          <Plus className="w-4 h-4" />
          New Job
        </Link>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
        <input
          className="input-field pl-11"
          placeholder="Search jobs by title, department..."
          id="jobs-search"
        />
      </div>

      {/* Job cards */}
      <div className="space-y-3">
        {mockJobs.map((job, i) => (
          <motion.div
            key={job.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className="glass-card p-5 hover:border-violet-500/20 cursor-pointer transition-all"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shrink-0">
                  <Briefcase className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-white">{job.title}</h3>
                  <div className="flex items-center gap-3 mt-1 text-sm text-slate-400">
                    <span>{job.department}</span>
                    <span className="flex items-center gap-1"><MapPin className="w-3 h-3" />{job.location}</span>
                    <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{job.created_at}</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <div className="text-right">
                  <div className="flex items-center gap-1 text-sm text-slate-300">
                    <Users className="w-3.5 h-3.5" />
                    <span>{job.applicants} applicants</span>
                  </div>
                </div>
                <span className={`score-badge border ${statusColor[job.status]}`}>
                  {job.status}
                </span>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
