import React, { useState } from 'react';
import { MessageSquare, MessageCircle, X, Info, ShieldCheck, CheckCheck } from 'lucide-react';
import { translations, Language } from '../utils/translations';

interface CommunicationPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  patientName: string;
  patientPhone?: string;
  defaultChannel?: 'SMS' | 'WHATSAPP';
  customMessage?: string;
  language?: Language;
}

export const CommunicationPreviewModal: React.FC<CommunicationPreviewModalProps> = ({
  isOpen,
  onClose,
  patientName,
  patientPhone = '',
  defaultChannel = 'SMS',
  customMessage,
  language = 'en'
}) => {
  const [activeTab, setActiveTab] = useState<'SMS' | 'WHATSAPP'>(defaultChannel);

  if (!isOpen) return null;

  const t = translations[language] || translations.en;

  const smsText = customMessage || (
    language === 'hi'
      ? `Apex Heart Institute: Namaste ${patientName}. Aapka dainik recovery check-in taiyar hai. Kripya portal kholein: care.apexcare.org/portal`
      : language === 'mr'
      ? `Apex Heart Institute: Namaskar ${patientName}. Tumcha dainik recovery check-in tayar ahe. Krupaya portal pahava: care.apexcare.org/portal`
      : `Apex Heart Institute: Namaste ${patientName}. Your scheduled recovery check-in is due today. Please open your patient portal: care.apexcare.org/portal`
  );

  const whatsappText = customMessage || (
    language === 'hi'
      ? `Namaste ${patientName},\n\nApex Heart Care ki taraf se yeh aapki dainik recovery check-in reminder hai.\n\nKripya apne portal par jakar aaj ke lakshan aur vitals darj karein.`
      : language === 'mr'
      ? `Namaskar ${patientName},\n\nApex Heart Care kadun he tumche dainik recovery check-in reminder ahe.\n\nKrupaya portal var jaaun aajchi lakshane nondva.`
      : `Hello ${patientName},\n\nThis is your scheduled recovery follow-up reminder from AI Care Companion (Apex Heart Institute).\n\nPlease complete your daily recovery check-in.`
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
      <div 
        className="bg-white rounded-3xl max-w-lg w-full p-6 sm:p-8 shadow-2xl border border-slate-200 relative transform transition-all"
        role="dialog"
        aria-modal="true"
        aria-labelledby="comm-preview-title"
      >
        <button
          onClick={onClose}
          className="absolute top-5 right-5 text-slate-400 hover:text-slate-600 p-1.5 rounded-full hover:bg-slate-100 transition-colors"
          aria-label="Close"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header with Mode Toggle */}
        <div className="flex items-center justify-between mb-5 pr-8">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-md">
                ₹0 Local Simulation
              </span>
            </div>
            <h3 id="comm-preview-title" className="text-lg font-bold text-slate-900 mt-1">
              {activeTab === 'SMS' ? t.sim_sms_title : t.sim_whatsapp_title}
            </h3>
          </div>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center bg-slate-100 p-1 rounded-xl mb-6">
          <button
            onClick={() => setActiveTab('SMS')}
            className={`flex-1 py-2 rounded-lg text-xs font-semibold flex items-center justify-center gap-2 transition-all ${
              activeTab === 'SMS'
                ? 'bg-white text-indigo-700 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <MessageSquare className="w-4 h-4 text-indigo-600" />
            SMS Notification
          </button>
          <button
            onClick={() => setActiveTab('WHATSAPP')}
            className={`flex-1 py-2 rounded-lg text-xs font-semibold flex items-center justify-center gap-2 transition-all ${
              activeTab === 'WHATSAPP'
                ? 'bg-white text-emerald-700 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <MessageCircle className="w-4 h-4 text-emerald-600" />
            WhatsApp Message
          </button>
        </div>

        {/* Channel Specific Simulation Previews */}
        {activeTab === 'SMS' ? (
          <div className="space-y-4">
            {/* SMS Device Simulation Card */}
            <div className="bg-slate-900 text-white rounded-2xl p-4 shadow-inner">
              <div className="flex items-center justify-between text-[11px] text-slate-400 pb-2 border-b border-slate-800">
                <span>SMS • {patientPhone}</span>
                <span>Now</span>
              </div>
              <div className="mt-3 bg-slate-800/80 rounded-xl p-3.5 border border-slate-700 text-xs leading-relaxed text-slate-100 font-sans">
                {smsText}
              </div>
            </div>

            {/* Simulation Status Badge */}
            <div className="bg-amber-50 border border-amber-200/80 rounded-xl p-3.5 flex items-start gap-3">
              <Info className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-bold text-amber-900">
                  {t.sim_sms_status}
                </p>
                <p className="text-[11px] text-amber-800/90 mt-0.5 leading-normal">
                  This message is rendered inside the application as a safe ₹0 local preview. No real SMS carrier API request was dispatched.
                </p>
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {/* WhatsApp Device Simulation Card */}
            <div className="bg-[#e5ddd5] rounded-2xl p-4 shadow-inner border border-emerald-900/10">
              <div className="flex items-center gap-2 bg-[#075e54] text-white p-2.5 rounded-xl shadow-sm mb-3">
                <div className="w-7 h-7 rounded-full bg-emerald-100 text-[#075e54] flex items-center justify-center font-bold text-xs">
                  AH
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1">
                    <span className="text-xs font-bold truncate">Apex Heart Institute</span>
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-300" />
                  </div>
                  <span className="text-[10px] text-emerald-200 block">Verified Healthcare Provider</span>
                </div>
              </div>

              <div className="max-w-[85%] bg-white rounded-2xl rounded-tl-sm p-3.5 shadow-sm text-xs text-slate-800 leading-relaxed space-y-1">
                <p className="whitespace-pre-line">{whatsappText}</p>
                <div className="flex items-center justify-end gap-1 text-[10px] text-slate-400 pt-1">
                  <span>10:30 AM</span>
                  <CheckCheck className="w-3.5 h-3.5 text-emerald-600" />
                </div>
              </div>
            </div>

            {/* Simulation Status Badge */}
            <div className="bg-emerald-50 border border-emerald-200/80 rounded-xl p-3.5 flex items-start gap-3">
              <Info className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-bold text-emerald-900">
                  {t.sim_whatsapp_status}
                </p>
                <p className="text-[11px] text-emerald-800/90 mt-0.5 leading-normal">
                  WhatsApp follow-up is simulated locally. Integration with Meta WhatsApp Business Cloud API requires company subscription approval and verified phone number credentials.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Close Button */}
        <div className="mt-6">
          <button
            onClick={onClose}
            className="w-full py-2.5 px-4 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs transition-colors active:scale-[0.99]"
          >
            {t.dismiss}
          </button>
        </div>
      </div>
    </div>
  );
};
