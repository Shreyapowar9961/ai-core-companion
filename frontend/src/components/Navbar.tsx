import React from 'react';
import { useAuth } from '../context/AuthContext';
import { UserRole } from '../types';
import { HeartPulse, Bell, PhoneCall, ShieldCheck, UserCheck } from 'lucide-react';

interface NavbarProps {
  onOpenCallSimulator: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onOpenCallSimulator }) => {
  const { currentUser, switchRole } = useAuth();

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        
        {/* Brand / Logo */}
        <div className="flex items-center space-x-3">
          <div className="bg-indigo-600 text-white p-2 rounded-xl shadow-sm flex items-center justify-center">
            <HeartPulse className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-lg text-slate-900 tracking-tight">AI Care Companion</span>
              <span className="bg-indigo-50 text-indigo-700 text-[10px] font-semibold px-2 py-0.5 rounded-full border border-indigo-200">
                PostgreSQL & Supabase
              </span>
            </div>
            <p className="text-xs text-slate-500 font-medium hidden sm:block">
              Apex Heart & Recovery Institute · Multi-Facility Recovery Engine
            </p>
          </div>
        </div>

        {/* Actions & Role Switcher */}
        <div className="flex items-center space-x-4">
          
          {/* Quick Call Simulator Launch */}
          <button
            onClick={onOpenCallSimulator}
            className="hidden md:inline-flex items-center space-x-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold px-3 py-2 rounded-lg transition-colors shadow-xs"
          >
            <PhoneCall className="w-3.5 h-3.5" />
            <span>Simulate Voice Call</span>
          </button>

          {/* Role Switcher Pill */}
          <div className="flex items-center bg-slate-100 p-1 rounded-lg border border-slate-200 text-xs">
            <div className="flex items-center space-x-1 px-2 text-slate-500 font-medium">
              <ShieldCheck className="w-3.5 h-3.5 text-indigo-600" />
              <span className="hidden lg:inline">Role:</span>
            </div>
            {(['CLINICIAN', 'ADMIN', 'CAREGIVER', 'PATIENT'] as UserRole[]).map((r) => (
              <button
                key={r}
                onClick={() => switchRole(r)}
                className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                  currentUser.role === r
                    ? 'bg-white text-indigo-700 shadow-xs font-semibold'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {r === 'CLINICIAN' ? 'Clinician' : r === 'ADMIN' ? 'Admin' : r === 'CAREGIVER' ? 'Caregiver' : 'Patient'}
              </button>
            ))}
          </div>

          {/* User Profile Info */}
          <div className="flex items-center space-x-2 pl-2 border-l border-slate-200">
            <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-slate-700 font-semibold text-xs border border-slate-300">
              {currentUser.name.charAt(0)}
            </div>
            <div className="hidden xl:block text-left text-xs leading-tight">
              <p className="font-semibold text-slate-800">{currentUser.name}</p>
              <p className="text-slate-400 font-mono text-[10px]">{currentUser.email}</p>
            </div>
          </div>

        </div>

      </div>
    </header>
  );
};
