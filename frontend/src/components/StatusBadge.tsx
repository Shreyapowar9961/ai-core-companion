import React from 'react';

interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const norm = status.toUpperCase();

  let colorClasses = 'bg-slate-100 text-slate-700 border-slate-200';

  if (norm === 'CRITICAL' || norm === 'CONSENT_WITHDRAWN' || norm === 'FAILED') {
    colorClasses = 'bg-rose-50 text-rose-700 border-rose-200';
  } else if (norm === 'HIGH' || norm === 'WARNING') {
    colorClasses = 'bg-orange-50 text-orange-700 border-orange-200';
  } else if (norm === 'MEDIUM' || norm === 'PAUSED' || norm === 'INTERRUPTED') {
    colorClasses = 'bg-amber-50 text-amber-700 border-amber-200';
  } else if (norm === 'ACTIVE' || norm === 'RESOLVED' || norm === 'COMPLETED' || norm === 'NORMAL' || norm === 'TAKEN') {
    colorClasses = 'bg-emerald-50 text-emerald-700 border-emerald-200';
  } else if (norm === 'OPEN' || norm === 'SCHEDULED' || norm === 'INFO' || norm === 'IN_PROGRESS') {
    colorClasses = 'bg-blue-50 text-blue-700 border-blue-200';
  } else if (norm === 'DRAFT') {
    colorClasses = 'bg-purple-50 text-purple-700 border-purple-200';
  }

  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs font-medium';

  return (
    <span className={`inline-flex items-center rounded-full border ${sizeClasses} ${colorClasses}`}>
      <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-current opacity-70" />
      {status.replace(/_/g, ' ')}
    </span>
  );
};
