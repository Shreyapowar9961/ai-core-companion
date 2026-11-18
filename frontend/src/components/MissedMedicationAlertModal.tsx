import React from 'react';
import { AlertCircle, Calendar, ArrowRight, X } from 'lucide-react';
import { translations, Language } from '../utils/translations';

interface MissedMedicationAlertModalProps {
  isOpen: boolean;
  onClose: () => void;
  medicineName: string;
  scheduledTime: string;
  language?: Language;
  onViewSchedule: () => void;
}

export const MissedMedicationAlertModal: React.FC<MissedMedicationAlertModalProps> = ({
  isOpen,
  onClose,
  medicineName,
  scheduledTime,
  language = 'en',
  onViewSchedule
}) => {
  if (!isOpen) return null;

  const t = translations[language] || translations.en;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
      <div 
        className="bg-white rounded-3xl max-w-md w-full p-6 sm:p-8 shadow-2xl border border-rose-100 relative transform transition-all"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="missed-med-title"
      >
        <button
          onClick={onClose}
          className="absolute top-5 right-5 text-slate-400 hover:text-slate-600 p-1.5 rounded-full hover:bg-slate-100 transition-colors"
          aria-label="Close"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div className="w-12 h-12 rounded-2xl bg-rose-50 border border-rose-100 flex items-center justify-center text-rose-600 shadow-inner">
            <AlertCircle className="w-6 h-6 text-rose-600" />
          </div>
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-rose-700 bg-rose-50 px-2.5 py-0.5 rounded-full">
              Clinical Alert
            </span>
            <h3 id="missed-med-title" className="text-lg font-bold text-slate-900 mt-0.5">
              {t.med_missed_alert_title}
            </h3>
          </div>
        </div>

        <p className="text-xs text-slate-600 leading-relaxed mb-5">
          {t.med_missed_alert_body}
        </p>

        {/* Real Missed Dose Details */}
        <div className="bg-rose-50/50 border border-rose-100 rounded-2xl p-4 mb-6 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500 font-medium">Unconfirmed Medicine:</span>
            <span className="text-sm font-bold text-rose-900">{medicineName}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500 font-medium">Scheduled Time:</span>
            <span className="text-xs font-mono font-medium text-slate-700">{scheduledTime}</span>
          </div>
          <div className="flex items-center justify-between pt-2 border-t border-rose-100 text-[11px]">
            <span className="text-slate-500">Record Status:</span>
            <span className="font-bold text-rose-700 uppercase tracking-wider">Reported Missed</span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="space-y-2.5">
          <button
            onClick={onViewSchedule}
            className="w-full py-3 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs sm:text-sm shadow-md shadow-indigo-600/20 flex items-center justify-center gap-2 transition-all active:scale-[0.99]"
          >
            <Calendar className="w-4 h-4" />
            {t.med_view_schedule}
            <ArrowRight className="w-4 h-4" />
          </button>

          <button
            onClick={onClose}
            className="w-full py-2.5 px-4 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs transition-colors active:scale-[0.99]"
          >
            {t.dismiss}
          </button>
        </div>

        <p className="text-[10px] text-center text-slate-400 mt-4">
          Repeated missed doses (≥2) are automatically escalated to your attending clinical team.
        </p>
      </div>
    </div>
  );
};
