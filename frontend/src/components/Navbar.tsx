import React from 'react';
import { useAuth } from '../context/AuthContext';
import { HeartPulse, PhoneCall, ShieldCheck, LogOut, Building2 } from 'lucide-react';

interface NavbarProps {
  onOpenCallSimulator: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onOpenCallSimulator }) => {
  const { currentUser, logout } = useAuth();

  if (!currentUser) return null;

  const isAdmin = currentUser.role === 'ADMIN';

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
              <span className="bg-emerald-50 text-emerald-700 text-[10px] font-semibold px-2 py-0.5 rounded-full border border-emerald-200 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                Hospital Network Active
              </span>
            </div>
            <p className="text-xs text-slate-500 font-medium hidden sm:block">
              Apex Heart & Recovery Institute · Multi-Facility Recovery Engine
            </p>
          </div>
        </div>

        {/* Actions & Authenticated Staff Context */}
        <div className="flex items-center space-x-3 sm:space-x-4">
          
          {/* Quick Call Simulator Launch */}
          <button
            onClick={onOpenCallSimulator}
            className="hidden md:inline-flex items-center space-x-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold px-3 py-2 rounded-lg transition-colors shadow-xs"
          >
            <PhoneCall className="w-3.5 h-3.5" />
            <span>Simulate Voice Call</span>
          </button>

          {/* Trusted RBAC Role Badge (DB-05) */}
          <div className="flex items-center gap-2">
            <span
              className={`px-2.5 py-1 rounded-md text-xs font-semibold border flex items-center gap-1.5 ${
                isAdmin
                  ? 'bg-purple-50 text-purple-700 border-purple-200'
                  : 'bg-indigo-50 text-indigo-700 border-indigo-200'
              }`}
            >
              <ShieldCheck className={`w-3.5 h-3.5 ${isAdmin ? 'text-purple-600' : 'text-indigo-600'}`} />
              <span>{isAdmin ? 'Hospital Administrator' : 'Attending Clinician'}</span>
            </span>

            {/* Facility Multi-Tenancy Badge */}
            {currentUser.facility_id && (
              <span className="hidden lg:inline-flex items-center gap-1 px-2 py-1 rounded bg-slate-100 border border-slate-200 text-slate-600 text-[11px] font-medium">
                <Building2 className="w-3 h-3 text-slate-400" />
                <span>{currentUser.facility_id === 'facility-apex-1' ? 'Apex Heart' : currentUser.facility_id}</span>
              </span>
            )}
          </div>

          {/* User Profile Info & Sign Out */}
          <div className="flex items-center space-x-3 pl-3 border-l border-slate-200">
            <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-700 font-semibold text-xs border border-indigo-200">
              {currentUser.name ? currentUser.name.charAt(0) : 'U'}
            </div>
            <div className="hidden xl:block text-left text-xs leading-tight">
              <p className="font-semibold text-slate-800">{currentUser.name}</p>
              <p className="text-slate-400 font-mono text-[10px]">{currentUser.email}</p>
            </div>

            {/* Logout Button */}
            <button
              onClick={() => logout()}
              title="Sign Out"
              className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors border border-transparent hover:border-rose-200"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>

        </div>

      </div>
    </header>
  );
};
