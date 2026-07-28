import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Briefcase, MapPin, Building2, ChevronRight, Loader2,
  Wand2, CheckCircle2, AlertCircle, ArrowLeft, Plus, X
} from 'lucide-react'
import { useMutation } from '@tanstack/react-query'
import apiClient from '@/api/client'
import { useAuthStore } from '@/store/auth'

const schema = z.object({
  title: z.string().min(2, 'Job title is required').max(256),
  department: z.string().optional(),
  location: z.string().optional(),
  employment_type: z.enum(['full_time', 'part_time', 'contract', 'internship', 'freelance']).optional(),
  jd_text: z.string().min(50, 'Job description must be at least 50 characters'),
})

type FormData = z.infer<typeof schema>

const employmentTypes = [
  { value: 'full_time', label: 'Full-time' },
  { value: 'part_time', label: 'Part-time' },
  { value: 'contract', label: 'Contract' },
  { value: 'internship', label: 'Internship' },
  { value: 'freelance', label: 'Freelance' },
]

interface ExtractedRequirements {
  required_skills: Array<{ name: string }>
  preferred_skills: Array<{ name: string }>
  min_years_experience: number | null
  education_requirement: string | null
}

export default function NewJobPage() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const [step, setStep] = useState<'form' | 'reviewing' | 'done'>('form')
  const [extracted, setExtracted] = useState<ExtractedRequirements | null>(null)

  const { register, handleSubmit, watch, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const jdText = watch('jd_text', '')

  // Create job and trigger JD analysis
  const { mutate, isPending, error } = useMutation({
    mutationFn: async (data: FormData) => {
      // Step 1: Create the job
      const { data: job } = await apiClient.post('/jobs', {
        title: data.title,
        department: data.department,
        location: data.location,
        employment_type: data.employment_type,
        description: data.jd_text,
        organization_id: user?.id, // Will be resolved from org membership server-side
      })

      // Step 2: Trigger JD analysis
      try {
        const { data: analysis } = await apiClient.post(`/jobs/${job.id}/analyze-jd`, {
          jd_text: data.jd_text,
        })
        setExtracted(analysis)
      } catch {
        // JD analysis is non-blocking
      }

      return job
    },
    onSuccess: () => {
      setStep('done')
      setTimeout(() => navigate('/recruiter/jobs'), 2000)
    },
  })

  const errorMessage = error
    ? ((error as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to create job')
    : null

  return (
    <div className="max-w-3xl">
      <div className="flex items-center gap-4 mb-8">
        <button
          onClick={() => navigate('/recruiter/jobs')}
          className="btn-ghost px-3 py-2 text-sm"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <h1 className="font-outfit text-2xl font-bold text-white">Create New Job Posting</h1>
          <p className="text-slate-400 text-sm mt-0.5">AI will extract structured requirements from your JD automatically</p>
        </div>
      </div>

      <AnimatePresence mode="wait">
        {step === 'done' ? (
          <motion.div
            key="done"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="glass-card p-12 text-center"
          >
            <div className="w-16 h-16 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center mx-auto mb-4">
              <CheckCircle2 className="w-8 h-8 text-emerald-400" />
            </div>
            <h2 className="font-outfit text-xl font-bold text-white mb-2">Job Created!</h2>
            <p className="text-slate-400 text-sm">AI is now analyzing your job description in the background...</p>
            {extracted && (
              <div className="mt-6 text-left space-y-3">
                <div className="glass-card p-4">
                  <p className="text-xs text-slate-500 mb-2">Required Skills Extracted</p>
                  <div className="flex flex-wrap gap-2">
                    {extracted.required_skills.slice(0, 8).map((s) => (
                      <span key={s.name} className="score-badge bg-violet-500/20 text-violet-300 border border-violet-500/30">{s.name}</span>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </motion.div>
        ) : (
          <motion.form
            key="form"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            onSubmit={handleSubmit((data) => mutate(data))}
            className="space-y-6"
          >
            {/* Basic Info */}
            <div className="glass-card p-6 space-y-5">
              <h2 className="font-semibold text-white flex items-center gap-2">
                <Briefcase className="w-4 h-4 text-violet-400" />
                Job Details
              </h2>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Job Title *</label>
                <input
                  {...register('title')}
                  className="input-field"
                  placeholder="Senior Full-Stack Engineer"
                  id="job-title"
                />
                {errors.title && <p className="text-xs text-red-400 mt-1">{errors.title.message}</p>}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">
                    <Building2 className="w-3.5 h-3.5 inline mr-1" />Department
                  </label>
                  <input
                    {...register('department')}
                    className="input-field"
                    placeholder="Engineering"
                    id="job-department"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">
                    <MapPin className="w-3.5 h-3.5 inline mr-1" />Location
                  </label>
                  <input
                    {...register('location')}
                    className="input-field"
                    placeholder="Remote / Bangalore"
                    id="job-location"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Employment Type</label>
                <div className="flex flex-wrap gap-2">
                  {employmentTypes.map((type) => (
                    <label
                      key={type.value}
                      className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm cursor-pointer hover:bg-white/[0.08] transition-colors"
                    >
                      <input
                        {...register('employment_type')}
                        type="radio"
                        value={type.value}
                        className="accent-violet-500"
                      />
                      {type.label}
                    </label>
                  ))}
                </div>
              </div>
            </div>

            {/* JD Input */}
            <div className="glass-card p-6">
              <h2 className="font-semibold text-white flex items-center gap-2 mb-2">
                <Wand2 className="w-4 h-4 text-violet-400" />
                Job Description
                <span className="text-xs text-violet-400 font-normal ml-auto">AI will extract requirements automatically</span>
              </h2>
              <p className="text-slate-500 text-xs mb-4">Paste the full job description including responsibilities, requirements, and qualifications.</p>

              <textarea
                {...register('jd_text')}
                className="input-field min-h-[280px] font-mono text-sm resize-y"
                placeholder="We are looking for a Senior Full-Stack Engineer to join our team...

Responsibilities:
- Build scalable web applications
- ...

Requirements:
- 5+ years of experience with Python and FastAPI
- Strong knowledge of React and TypeScript
- ..."
                id="job-jd-text"
              />
              {errors.jd_text && <p className="text-xs text-red-400 mt-1">{errors.jd_text.message}</p>}

              <div className="flex items-center justify-between mt-3">
                <span className="text-xs text-slate-600">{jdText.length} characters</span>
                {jdText.length >= 200 && (
                  <span className="text-xs text-emerald-400 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" />
                    Good JD length for AI extraction
                  </span>
                )}
              </div>
            </div>

            {errorMessage && (
              <div className="flex items-start gap-2 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3">
                <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                <p className="text-sm text-red-400">{errorMessage}</p>
              </div>
            )}

            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => navigate('/recruiter/jobs')}
                className="btn-ghost px-6 py-3"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isPending}
                id="create-job-submit"
                className="btn-primary px-8 py-3 flex-1"
              >
                {isPending ? (
                  <><Loader2 className="w-4 h-4 animate-spin" />Creating job & analyzing JD...</>
                ) : (
                  <>Create Job Posting <ChevronRight className="w-4 h-4" /></>
                )}
              </button>
            </div>
          </motion.form>
        )}
      </AnimatePresence>
    </div>
  )
}
