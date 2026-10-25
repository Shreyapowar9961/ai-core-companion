import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { CallSimulatorModal } from './components/CallSimulatorModal';

import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { PatientDetailPage } from './pages/PatientDetailPage';
import { OnboardingPage } from './pages/OnboardingPage';
import { AlertsPage } from './pages/AlertsPage';
import { CallConsolePage } from './pages/CallConsolePage';
import { RulesConfigPage } from './pages/RulesConfigPage';
import { KnowledgeBasePage } from './pages/KnowledgeBasePage';
import { AuditTrailPage } from './pages/AuditTrailPage';
import { HeartPulse } from 'lucide-react';

// Protected Route Guard
const ProtectedLayout: React.FC<{ children: React.ReactNode; onOpenCallSimulator: () => void }> = ({
  children,
  onOpenCallSimulator
}) => {
  const { currentUser, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center p-6 text-white font-sans">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-600 shadow-xl text-white mb-4 animate-pulse">
          <HeartPulse className="w-8 h-8" />
        </div>
        <div className="w-6 h-6 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin mb-3" />
        <p className="text-sm font-semibold text-slate-200">Verifying Clinical Authorization...</p>
        <p className="text-xs text-slate-400 mt-1">Apex Heart & Recovery Institute · DB-05 RBAC</p>
      </div>
    );
  }

  if (!currentUser) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      {/* Top Navigation */}
      <Navbar onOpenCallSimulator={onOpenCallSimulator} />

      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar */}
        <Sidebar />

        {/* Main Workspace Viewport */}
        <main className="flex-1 overflow-y-auto p-6 md:p-8 custom-scrollbar">
          <div className="max-w-7xl mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};

// Login Route Guard: If already logged in, redirect to home
const LoginRoute: React.FC = () => {
  const { currentUser, isLoading } = useAuth();

  if (isLoading) {
    return null;
  }

  if (currentUser) {
    return <Navigate to="/" replace />;
  }

  return <LoginPage />;
};

export const App: React.FC = () => {
  const [isSimulatorOpen, setIsSimulatorOpen] = useState(false);

  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Login Route */}
          <Route path="/login" element={<LoginRoute />} />

          {/* Protected Clinical Workstation Routes */}
          <Route
            path="/*"
            element={
              <ProtectedLayout onOpenCallSimulator={() => setIsSimulatorOpen(true)}>
                <Routes>
                  <Route path="/" element={<DashboardPage onOpenCallSimulator={() => setIsSimulatorOpen(true)} />} />
                  <Route path="/patients" element={<DashboardPage onOpenCallSimulator={() => setIsSimulatorOpen(true)} />} />
                  <Route path="/patients/:id" element={<PatientDetailPage />} />
                  <Route path="/onboard" element={<OnboardingPage />} />
                  <Route path="/alerts" element={<AlertsPage />} />
                  <Route path="/call-console" element={<CallConsolePage />} />
                  <Route path="/rules" element={<RulesConfigPage />} />
                  <Route path="/knowledge" element={<KnowledgeBasePage />} />
                  <Route path="/audit" element={<AuditTrailPage />} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </ProtectedLayout>
            }
          />
        </Routes>

        {/* Interactive Voice Call Simulator Modal */}
        <CallSimulatorModal
          isOpen={isSimulatorOpen}
          onClose={() => setIsSimulatorOpen(false)}
        />
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
