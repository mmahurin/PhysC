import { Routes, Route, NavLink } from 'react-router-dom'
import { Hospital } from 'lucide-react'
import { SubmissionPage } from '@/pages/SubmissionPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { cn } from '@/lib/utils'

function Navbar() {
  return (
    <nav className="sticky top-0 z-50 border-b bg-white shadow-sm">
      <div className="max-w-7xl mx-auto px-4 h-14 flex items-center gap-6">
        <div className="flex items-center gap-2 mr-4">
          <div className="rounded-md bg-primary p-1.5">
            <Hospital className="h-4 w-4 text-white" />
          </div>
          <span className="font-semibold text-foreground hidden sm:inline">
            Physician Credentialing
          </span>
        </div>

        <div className="flex gap-1">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              cn(
                'px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted'
              )
            }
          >
            Physician Submission
          </NavLink>
          <NavLink
            to="/dashboard"
            className={({ isActive }) =>
              cn(
                'px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted'
              )
            }
          >
            Specialist Dashboard
          </NavLink>
        </div>
      </div>
    </nav>
  )
}

export default function App() {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main>
        <Routes>
          <Route path="/" element={<SubmissionPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
        </Routes>
      </main>
    </div>
  )
}
