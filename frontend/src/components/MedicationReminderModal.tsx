import React from 'react';
import { Pill, Clock, AlertTriangle, X, Check, XCircle } from 'lucide-react';
import { translations, Language } from '../utils/translations';

interface MedicationReminderModalProps {
  isOpen: boolean;
  onClose: () => void;
  medicineName: string;
  dosage: string;
  scheduledTime: string;
  instructions?: string;
  language?: Language;
  onConfirmTaken: () => void;
  onReportMissed: () => void;
  onRemindLater: () => void;
  isSubmitting?: boolean;
}

export const MedicationReminderModal: React.FC<MedicationReminderModalProps> = ({
  isOpen,
  onClose,
  medicineName,
  dosage,
  scheduledTime,
  instructions,
  language = 'en',
  onConfirmTaken,
  onReportMissed,
  onRemindLater,
  isSubmitting = false
}) => {
  if (!isOpen) return null;

  const t = translations[language] || translations.en;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
      <div 
        className="bg-white rounded-3xl max-w-md w-full p-6 sm:p-8 shadow-2xl border border-indigo-100 relative transform transition-all"
        role="dialog"
        aria-modal="true"
        aria-labelledby="med-reminder-title"
      >
        <button
          onClick={onClose}
          className="absolute top-5 right-5 text-slate-400 hover:text-slate-600 p-1.5 rounded-full hover:bg-slate-100 transition-colors"
          aria-label="Close"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div className="w-12 h-12 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 shadow-inner">
            <Pill className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-600 bg-indigo-50 px-2.5 py-0.5 rounded-full">
              {t.medications_tab}
            </span>
            <h3 id="med-reminder-title" className="text-lg font-bold text-slate-900 mt-0.5">
              {t.med_reminder_title}
            </h3>
          </div>
        </div>

        <p className="text-xs text-slate-600 leading-relaxed mb-5">
          {t.med_reminder_body}
        </p>

        {/* Real Medication Details Box */}
        <div className="bg-slate-50 border border-slate-200/80 rounded-2xl p-4 mb-6 space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500 font-medium">{t.today_meds}:</span>
            <span className="text-sm font-bold text-slate-900">{medicineName}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500 font-medium">{t.med_dosage}:</span>
            <span className="text-xs font-semibold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded-md">
              {dosage}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500 font-medium">{t.med_scheduled_time}:</span>
            <span className="text-xs font-mono text-slate-700 flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              {scheduledTime}
            </span>
          </div>
          {instructions && (
            <div className="pt-2 border-t border-slate-200/60 text-[11px] text-slate-600">
              <span className="font-semibold text-slate-700">Instructions: </span>
              {instructions}
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="space-y-2.5">
          <button
            onClick={onConfirmTaken}
            disabled={isSubmitting}
            className="w-full py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs sm:text-sm shadow-md shadow-emerald-600/20 flex items-center justify-center gap-2 transition-all active:scale-[0.99] disabled:opacity-50"
          >
            <Check className="w-4 h-4" />
            {t.med_mark_taken}
          </button>

          <div className="grid grid-cols-2 gap-2.5">
            <button
              onClick={onReportMissed}
              disabled={isSubmitting}
              className="py-2.5 px-3 rounded-xl border border-rose-200 bg-rose-50/50 hover:bg-rose-100/70 text-rose-700 font-semibold text-xs flex items-center justify-center gap-1.5 transition-colors active:scale-[0.99] disabled:opacity-50"
            >
              <XCircle className="w-4 h-4 text-rose-500" />
              {t.med_report_missed}
            </button>
            <button
              onClick={onRemindLater}
              disabled={isSubmitting}
              className="py-2.5 px-3 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs flex items-center justify-center gap-1.5 transition-colors active:scale-[0.99]"
            >
              <Clock className="w-4 h-4 text-slate-400" />
              {t.med_remind_later}
            </button>
          </div>
        </div>

        <p className="text-[10px] text-center text-slate-400 mt-4">
          Safe Clinical Reminder • Dismissing does not alter clinical adherence records
        </p>
      </div>
    </div>
  );
};
