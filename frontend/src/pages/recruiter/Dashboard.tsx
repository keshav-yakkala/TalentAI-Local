import { motion } from 'framer-motion'
import {
  Briefcase, Users, CheckCircle2, Clock, Mic, FileText,
  TrendingUp, ArrowUpRight, Zap
} from 'lucide-react'
import { useAuthStore } from '@/store/auth'

const stats = [
  { label: 'Active Jobs', value: '12', trend: '+3 this week', icon: Briefcase, color: 'from-violet-500 to-purple-600', glow: 'rgba(124,58,237,0.25)' },
  { label: 'Total Applicants', value: '347', trend: '+48 today', icon: Users, color: 'from-blue-500 to-cyan-600', glow: 'rgba(59,130,246,0.25)' },
  { label: 'Candidates Screened', value: '284', trend: '81.8% rate', icon: CheckCircle2, color: 'from-emerald-500 to-teal-600', glow: 'rgba(16,185,129,0.25)' },
  { label: 'Interviews Active', value: '23', trend: '8 today', icon: Mic, color: 'from-amber-500 to-orange-600', glow: 'rgba(245,158,11,0.25)' },
]

const recentActivity = [
  { icon: FileText, text: 'Resume uploaded — Sarah Chen for Senior Engineer', time: '2 min ago', color: 'text-violet-400' },
  { icon: CheckCircle2, text: 'Screening complete — Marcus Johnson: Strong Match (87%)', time: '8 min ago', color: 'text-emerald-400' },
  { icon: Mic, text: 'Interview completed — Priya Sharma for ML Engineer role', time: '15 min ago', color: 'text-blue-400' },
  { icon: TrendingUp, text: 'Job posted — Senior Full-Stack Engineer — Remote', time: '1 hour ago', color: 'text-amber-400' },
  { icon: Users, text: '15 new applications received — Product Manager role', time: '2 hours ago', color: 'text-pink-400' },
]

export default function RecruiterDashboard() {
  const { user } = useAuthStore()
  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-outfit text-3xl font-bold text-white">
            {greeting}, {user?.full_name?.split(' ')[0]} 👋
          </h1>
          <p className="text-slate-400 mt-1">Here's what's happening with your recruitment pipeline today.</p>
        </div>
        <button className="btn-primary px-5 py-2.5 text-sm">
          <Zap className="w-4 h-4" />
          Quick Actions
        </button>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5">
        {stats.map((stat, i) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="glass-card p-5 group hover:scale-[1.02] transition-all duration-300"
            style={{ boxShadow: `0 0 30px ${stat.glow}` }}
          >
            <div className="flex items-start justify-between mb-4">
              <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${stat.color} flex items-center justify-center`}>
                <stat.icon className="w-5 h-5 text-white" />
              </div>
              <ArrowUpRight className="w-4 h-4 text-slate-600 group-hover:text-slate-400 transition-colors" />
            </div>
            <div className="font-outfit text-3xl font-black text-white mb-1">{stat.value}</div>
            <div className="text-sm text-slate-500">{stat.label}</div>
            <div className="text-xs text-emerald-400 mt-1.5">{stat.trend}</div>
          </motion.div>
        ))}
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Activity feed */}
        <div className="lg:col-span-2 glass-card p-6">
          <h2 className="font-outfit font-bold text-white text-lg mb-5 flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Recent Activity
          </h2>
          <div className="space-y-4">
            {recentActivity.map((item, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className="flex items-start gap-4 py-3 border-b border-white/5 last:border-0"
              >
                <div className={`w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center shrink-0 ${item.color}`}>
                  <item.icon className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-300 leading-relaxed">{item.text}</p>
                  <p className="text-xs text-slate-600 mt-0.5">{item.time}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Pipeline summary */}
        <div className="glass-card p-6">
          <h2 className="font-outfit font-bold text-white text-lg mb-5">Pipeline Status</h2>
          <div className="space-y-4">
            {[
              { label: 'Strong Match', count: 42, pct: 68, color: 'bg-emerald-500' },
              { label: 'Potential Match', count: 89, pct: 45, color: 'bg-blue-500' },
              { label: 'Human Review', count: 23, pct: 28, color: 'bg-amber-500' },
              { label: 'Weak Match', count: 130, pct: 15, color: 'bg-red-500/70' },
            ].map((item) => (
              <div key={item.label}>
                <div className="flex justify-between text-sm mb-1.5">
                  <span className="text-slate-400">{item.label}</span>
                  <span className="text-white font-medium">{item.count}</span>
                </div>
                <div className="h-1.5 rounded-full bg-white/5">
                  <motion.div
                    className={`h-full rounded-full ${item.color}`}
                    initial={{ width: 0 }}
                    animate={{ width: `${item.pct}%` }}
                    transition={{ duration: 0.8, delay: 0.3 }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 pt-6 border-t border-white/5">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-400">Avg. Time to Screen</span>
              <span className="text-white font-medium">2.3 min</span>
            </div>
            <div className="flex items-center justify-between text-sm mt-3">
              <span className="text-slate-400">Avg. Score Confidence</span>
              <span className="text-emerald-400 font-medium">91%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
