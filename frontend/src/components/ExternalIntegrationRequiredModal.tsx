import React, { useState } from 'react';
import { ShieldAlert, CheckCircle, ExternalLink, Key, Lock, X, AlertTriangle } from 'lucide-react';
import { translations, Language } from '../utils/translations';

interface ExternalIntegrationRequiredModalProps {
  isOpen: boolean;
  onClose: () => void;
  language?: Language;
}

export const ExternalIntegrationRequiredModal: React.FC<ExternalIntegrationRequiredModalProps> = ({
  isOpen,
  onClose,
  language = 'en'
}) => {
  const [showRequirements, setShowRequirements] = useState(false);

  if (!isOpen) return null;

  const t = translations[language] || translations.en;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
      <div 
        className="bg-white rounded-3xl max-w-lg w-full p-6 sm:p-8 shadow-2xl border border-slate-200 relative transform transition-all"
        role="dialog"
        aria-modal="true"
        aria-labelledby="external-integration-title"
      >
        <button
          onClick={onClose}
          className="absolute top-5 right-5 text-slate-400 hover:text-slate-600 p-1.5 rounded-full hover:bg-slate-100 transition-colors"
          aria-label="Close"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div className="w-12 h-12 rounded-2xl bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600 shadow-inner">
            <Lock className="w-6 h-6 text-amber-600" />
          </div>
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-amber-700 bg-amber-50 px-2.5 py-0.5 rounded-full">
              Enterprise Governance
            </span>
            <h3 id="external-integration-title" className="text-lg font-bold text-slate-900 mt-0.5">
              {t.sim_integration_title}
            </h3>
          </div>
        </div>

        <p className="text-xs text-slate-600 leading-relaxed mb-4">
          {t.sim_integration_body}
        </p>

        {/* Current Status Box */}
        <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 mb-5">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-semibold text-slate-600">Current Environment:</span>
            <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200 flex items-center gap-1">
              <CheckCircle className="w-3.5 h-3.5" />
              Simulation Mode Active
            </span>
          </div>
          <p className="text-[11px] text-slate-500 leading-relaxed">
            All clinical rules, triage workflows, voice dialogues, and medication schedules operate with 100% fidelity using local in-app simulation.
          </p>
        </div>

        {/* Integration Requirements Dropdown / View */}
        {showRequirements ? (
          <div className="bg-amber-50/60 border border-amber-200/80 rounded-2xl p-4 mb-5 space-y-3 text-xs animate-fade-in">
            <h4 className="font-bold text-amber-900 flex items-center gap-1.5">
              <Key className="w-4 h-4 text-amber-600" />
              Carrier Integration Prerequisites
            </h4>
            
            <div className="space-y-2 text-[11px] text-slate-700">
              <div className="p-2 bg-white rounded-lg border border-amber-100">
                <span className="font-semibold text-slate-900 block">1. Outbound PSTN Voice (Twilio)</span>
                Requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and verified Twilio Outbound Number configured in backend environment.
              </div>
              <div className="p-2 bg-white rounded-lg border border-amber-100">
                <span className="font-semibold text-slate-900 block">2. WhatsApp Business API (Meta Cloud)</span>
                Requires approved Meta WhatsApp Cloud API credentials, registered WABA Phone Number ID, and message template approvals.
              </div>
              <div className="p-2 bg-white rounded-lg border border-amber-100">
                <span className="font-semibold text-slate-900 block">3. Transactional SMS Gateway</span>
                Requires DLTE-approved template registration and commercial SMS aggregator credentials.
              </div>
            </div>

            <p className="text-[10px] text-amber-800 italic">
              Safety Guard: Never paste secret keys into the frontend or client browsers. Configure secrets via backend server environment variables.
            </p>
          </div>
        ) : null}

        {/* Action Buttons */}
        <div className="space-y-2.5">
          <button
            onClick={() => setShowRequirements(!showRequirements)}
            className="w-full py-2.5 px-4 rounded-xl border border-indigo-200 bg-indigo-50/60 hover:bg-indigo-100/70 text-indigo-700 font-semibold text-xs flex items-center justify-center gap-1.5 transition-colors"
          >
            <Key className="w-4 h-4 text-indigo-600" />
            {showRequirements ? 'Hide Integration Requirements' : t.sim_integration_req_btn}
          </button>

          <button
            onClick={onClose}
            className="w-full py-3 px-4 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs sm:text-sm shadow-md flex items-center justify-center gap-2 transition-all active:scale-[0.99]"
          >
            {t.sim_integration_demo_btn}
          </button>
        </div>

        <p className="text-[10px] text-center text-slate-400 mt-4">
          Strict ₹0 Architecture Policy • No payment methods or billing accounts required
        </p>
      </div>
    </div>
  );
};
