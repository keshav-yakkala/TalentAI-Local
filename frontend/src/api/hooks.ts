/**
 * API service hooks — all backed by TanStack Query
 * Each hook corresponds to a backend endpoint
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import apiClient from './client'
import type { Job, Application, Resume, ScreeningResult, RecruiterDashboard } from '@/types'

// ── Jobs ──────────────────────────────────────────────────────────────────────

export function useJobs(organizationId: string) {
  return useQuery({
    queryKey: ['jobs', organizationId],
    queryFn: async () => {
      const { data } = await apiClient.get<{ items: Job[]; total: number }>(
        `/jobs?organization_id=${organizationId}`
      )
      return data
    },
    enabled: !!organizationId,
  })
}

export function useJob(jobId: string) {
  return useQuery({
    queryKey: ['job', jobId],
    queryFn: async () => {
      const { data } = await apiClient.get<Job>(`/jobs/${jobId}`)
      return data
    },
    enabled: !!jobId,
  })
}

export function useCreateJob() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (jobData: Partial<Job>) => {
      const { data } = await apiClient.post<Job>('/jobs', jobData)
      return data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['jobs'] })
    },
  })
}

export function useAnalyzeJD() {
  return useMutation({
    mutationFn: async ({ jobId, jdText }: { jobId: string; jdText: string }) => {
      const { data } = await apiClient.post(`/jobs/${jobId}/analyze-jd`, { jd_text: jdText })
      return data
    },
  })
}

// ── Resumes ───────────────────────────────────────────────────────────────────

export function useUploadResume() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({
      file,
      candidateName,
      candidateEmail,
    }: {
      file: File
      candidateName?: string
      candidateEmail?: string
    }) => {
      const formData = new FormData()
      formData.append('file', file)
      if (candidateName) formData.append('candidate_name', candidateName)
      if (candidateEmail) formData.append('candidate_email', candidateEmail)

      const { data } = await apiClient.post<{ resume_id: string; candidate_id: string }>(
        '/resumes/upload',
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      )
      return data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['candidates'] })
    },
  })
}

export function useResumeStatus(resumeId: string) {
  return useQuery({
    queryKey: ['resume-status', resumeId],
    queryFn: async () => {
      const { data } = await apiClient.get<Resume>(`/resumes/${resumeId}/status`)
      return data
    },
    enabled: !!resumeId,
    refetchInterval: (query) => {
      const data = query.state.data
      // Poll every 3s if still processing
      if (!data || ['pending', 'parsing', 'extracting', 'embedding'].includes(data.parsing_status)) {
        return 3000
      }
      return false
    },
  })
}

// ── Screening ─────────────────────────────────────────────────────────────────

export function useScreeningResult(applicationId: string) {
  return useQuery({
    queryKey: ['screening', applicationId],
    queryFn: async () => {
      const { data } = await apiClient.get<ScreeningResult>(`/screening/${applicationId}`)
      return data
    },
    enabled: !!applicationId,
  })
}

export function useTriggerScreening() {
  return useMutation({
    mutationFn: async ({ applicationId }: { applicationId: string }) => {
      const { data } = await apiClient.post(`/screening/${applicationId}/start`)
      return data
    },
  })
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export function useDashboardStats(organizationId: string) {
  return useQuery({
    queryKey: ['dashboard', organizationId],
    queryFn: async () => {
      const { data } = await apiClient.get<RecruiterDashboard>(
        `/analytics/dashboard?organization_id=${organizationId}`
      )
      return data
    },
    enabled: !!organizationId,
    staleTime: 30_000,
  })
}
