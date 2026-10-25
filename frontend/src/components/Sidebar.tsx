import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  LayoutDashboard,
  Users,
  UserPlus,
  AlertTriangle,
  PhoneCall,
  BookOpen,
  Sliders,
  History,
  ShieldAlert
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const { currentUser } = useAuth();
  const isClinicianOrAdmin = currentUser.role === 'CLINICIAN' || currentUser.role === 'ADMIN';

  const navItems = [
    {
      to: '/',
      label: 'Clinical Overview',
      icon: LayoutDashboard,
      roles: ['CLINICIAN', 'ADMIN', 'CAREGIVER', 'PATIENT'],
    },
    {
      to: '/patients',
      label: 'Patients & 360 View',
      icon: Users,
      roles: ['CLINICIAN', 'ADMIN', 'CAREGIVER', 'PATIENT'],
    },
    {
      to: '/onboard',
      label: 'Discharge Onboarding',
      icon: UserPlus,
      roles: ['CLINICIAN', 'ADMIN'],
    },
    {
      to: '/alerts',
      label: 'Alerts & Triage SLA',
      icon: AlertTriangle,
      roles: ['CLINICIAN', 'ADMIN', 'CAREGIVER'],
    },
    {
      to: '/rules',
      label: 'Clinical Rules Engine',
      icon: Sliders,
      roles: ['CLINICIAN', 'ADMIN'],
    },
    {
      to: '/knowledge',
      label: 'Approved Knowledge',
      icon: BookOpen,
      roles: ['CLINICIAN', 'ADMIN', 'CAREGIVER', 'PATIENT'],
    },
    {
      to: '/audit',
      label: 'Clinical Audit & Journey',
      icon: History,
      roles: ['CLINICIAN', 'ADMIN'],
    },
  ];

  const visibleItems = navItems.filter((item) => item.roles.includes(currentUser.role));

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 min-h-[calc(100vh-4rem)] flex flex-col justify-between p-4 shrink-0">
      <div className="space-y-6">
        <div>
          <p className="px-3 text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
            Main Navigation
          </p>
          <nav className="space-y-1">
            {visibleItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/'}
                  className={({ isActive }) =>
                    `flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-indigo-600 text-white shadow-xs'
                        : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                    }`
                  }
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* Clinical Guardrail Indicator */}
        <div className="p-3 bg-slate-800/80 rounded-xl border border-slate-700/60">
          <div className="flex items-center space-x-2 text-indigo-400 text-xs font-semibold mb-1">
            <ShieldAlert className="w-4 h-4" />
            <span>Clinical Protocols Active</span>
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            Deterministic physician-configured thresholds active with immediate 15-minute emergency escalation.
          </p>
        </div>
      </div>

      {/* Facility Footer */}
      <div className="pt-4 border-t border-slate-800 text-xs text-slate-400">
        <p className="font-semibold text-slate-300">Apex Heart & Recovery</p>
        <p className="text-[10px] text-slate-400">Cardiology & Post-Op Recovery</p>
      </div>
    </aside>
  );
};
