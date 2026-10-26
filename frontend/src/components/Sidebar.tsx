import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  LayoutDashboard,
  Users,
  UserPlus,
  AlertTriangle,
  BookOpen,
  Sliders,
  History
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const { currentUser } = useAuth();
  if (!currentUser) return null;

  const navItems = [
    {
      to: '/',
      label: 'Clinical Overview',
      icon: LayoutDashboard,
      roles: ['CLINICIAN', 'ADMIN'],
    },
    {
      to: '/patients',
      label: 'Patients & 360 View',
      icon: Users,
      roles: ['CLINICIAN', 'ADMIN'],
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
      roles: ['CLINICIAN', 'ADMIN'],
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
      roles: ['CLINICIAN', 'ADMIN'],
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
            Clinical Workstation
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
                    `flex items-center space-x-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-colors ${
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
      </div>

      {/* Facility Footer */}
      <div className="pt-4 border-t border-slate-800 text-xs text-slate-400">
        <p className="font-semibold text-slate-300">Apex Heart & Recovery</p>
        <p className="text-[10px] text-slate-500">Hospital Cardiology Network</p>
      </div>
    </aside>
  );
};
