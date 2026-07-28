import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LandingPage from '@/pages/LandingPage'
import LoginPage from '@/pages/LoginPage'
import RegisterPage from '@/pages/RegisterPage'
import RecruiterDashboard from '@/pages/recruiter/Dashboard'
import JobsPage from '@/pages/recruiter/Jobs'
import NewJobPage from '@/pages/recruiter/NewJob'
import CandidatesPage from '@/pages/recruiter/Candidates'
import CandidateDetailPage from '@/pages/recruiter/CandidateDetail'
import CandidatePortal from '@/pages/candidate/Portal'
import CandidateInterviewPage from '@/pages/candidate/InterviewPage'
import { useAuthStore } from '@/store/auth'
import RecruiterLayout from '@/layouts/RecruiterLayout'

function ProtectedRoute({ children, role }: { children: React.ReactNode; role?: string }) {
  const { user, isAuthenticated } = useAuthStore()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (role && user?.role !== role) {
    // Redirect candidate to their portal, recruiter to dashboard
    if (user?.role === 'candidate') return <Navigate to="/candidate" replace />
    if (user?.role === 'recruiter') return <Navigate to="/recruiter/dashboard" replace />
    return <Navigate to="/" replace />
  }
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public */}
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* Candidate routes */}
        <Route
          path="/candidate"
          element={
            <ProtectedRoute role="candidate">
              <CandidatePortal />
            </ProtectedRoute>
          }
        />
        <Route
          path="/candidate/interview"
          element={
            <ProtectedRoute role="candidate">
              <CandidateInterviewPage />
            </ProtectedRoute>
          }
        />
        {/* Legacy candidate interview route */}
        <Route
          path="/candidate/interviews/:interviewId"
          element={
            <ProtectedRoute role="candidate">
              <CandidateInterviewPage />
            </ProtectedRoute>
          }
        />

        {/* Recruiter — protected */}
        <Route
          path="/recruiter"
          element={
            <ProtectedRoute role="recruiter">
              <RecruiterLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="dashboard" replace />} />
          <Route path="dashboard" element={<RecruiterDashboard />} />
          <Route path="jobs" element={<JobsPage />} />
          <Route path="jobs/new" element={<NewJobPage />} />
          <Route path="candidates" element={<CandidatesPage />} />
          <Route path="candidates/:candidateId" element={<CandidateDetailPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
