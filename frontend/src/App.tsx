import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { CallSimulatorModal } from './components/CallSimulatorModal';

import { DashboardPage } from './pages/DashboardPage';
import { PatientDetailPage } from './pages/PatientDetailPage';
import { OnboardingPage } from './pages/OnboardingPage';
import { AlertsPage } from './pages/AlertsPage';
import { CallConsolePage } from './pages/CallConsolePage';
import { RulesConfigPage } from './pages/RulesConfigPage';
import { KnowledgeBasePage } from './pages/KnowledgeBasePage';
import { AuditTrailPage } from './pages/AuditTrailPage';

export const App: React.FC = () => {
  const [isSimulatorOpen, setIsSimulatorOpen] = useState(false);

  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
          
          {/* Top Navigation */}
          <Navbar onOpenCallSimulator={() => setIsSimulatorOpen(true)} />

          <div className="flex-1 flex overflow-hidden">
            {/* Left Sidebar */}
            <Sidebar />

            {/* Main Workspace Viewport */}
            <main className="flex-1 overflow-y-auto p-6 md:p-8 custom-scrollbar">
              <div className="max-w-7xl mx-auto">
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
              </div>
            </main>
          </div>

          {/* Interactive Voice Call Simulator Modal */}
          <CallSimulatorModal
            isOpen={isSimulatorOpen}
            onClose={() => setIsSimulatorOpen(false)}
          />

        </div>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
