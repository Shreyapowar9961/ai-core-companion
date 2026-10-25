import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  HeartPulse,
  Lock,
  Mail,
  ShieldCheck,
  AlertCircle,
  CheckCircle2,
  Building2,
  Stethoscope,
  ShieldAlert,
  ArrowRight
} from 'lucide-react';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Check if redirected due to expired session
  const redirectReason = (location.state as any)?.reason;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setErrorMessage('Please enter both your clinical email address and password.');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      await login(email, password);
      const from = (location.state as any)?.from?.pathname || '/';
      navigate(from, { replace: true });
    } catch (err: any) {
      setErrorMessage(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickFill = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setErrorMessage(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-950 flex flex-col justify-center items-center p-4 sm:p-6 font-sans">
      
      {/* Background Subtle Hospital Geometry */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-indigo-900/20 via-transparent to-transparent pointer-events-none" />

      <div className="w-full max-w-md relative z-10">

        {/* Brand Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-indigo-600 shadow-xl shadow-indigo-600/30 text-white mb-4">
            <HeartPulse className="w-9 h-9 animate-pulse" />
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            AI Care Companion
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1 font-medium">
            Apex Heart & Recovery Institute · Multi-Facility Recovery Engine
          </p>
          <div className="inline-flex items-center gap-1.5 mt-3 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            Secured Clinical Workstation (DB-05 RBAC)
          </div>
        </div>

        {/* Login Card */}
        <div className="bg-white rounded-2xl shadow-2xl border border-slate-100 p-6 sm:p-8">
          
          <div className="mb-6">
            <h2 className="text-lg font-bold text-slate-900">Clinical Staff Sign In</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Authorized attending clinicians and administrators only
            </p>
          </div>

          {/* Session Expiry or Error Alert */}
          {redirectReason && (
            <div className="mb-4 p-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-xs flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <span>Your session has expired. Please log in again to continue.</span>
            </div>
          )}

          {errorMessage && (
            <div className="mb-4 p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-2">
              <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email Field */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Hospital Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="clinician@apexcare.org"
                  required
                  disabled={isLoading}
                  className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors disabled:bg-slate-50 disabled:text-slate-400"
                />
              </div>
            </div>

            {/* Password Field */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  required
                  disabled={isLoading}
                  className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors disabled:bg-slate-50 disabled:text-slate-400"
                />
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full mt-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2.5 px-4 rounded-lg text-sm shadow-md transition-colors flex items-center justify-center gap-2 disabled:bg-indigo-400 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Verifying Credentials...</span>
                </>
              ) : (
                <>
                  <span>Sign In to Dashboard</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Quick-Fill Authorized Test Accounts (Demo Mode) */}
          <div className="mt-6 pt-5 border-t border-slate-200">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                Authorized Clinical Accounts
              </span>
              <span className="text-[10px] text-indigo-600 font-medium">Click to populate</span>
            </div>

            <div className="space-y-2">
              <button
                type="button"
                onClick={() => handleQuickFill('dr.neha@apexcare.org', 'Clinician123!')}
                className="w-full text-left p-2.5 rounded-lg border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/50 transition-all flex items-center justify-between text-xs group"
              >
                <div className="flex items-center gap-2">
                  <div className="p-1 rounded bg-indigo-100 text-indigo-700">
                    <Stethoscope className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <p className="font-semibold text-slate-800 group-hover:text-indigo-900">Dr. Neha Kulkarni</p>
                    <p className="text-[11px] text-slate-500">Attending Clinician (Apex Heart)</p>
                  </div>
                </div>
                <span className="text-[10px] font-medium text-slate-400 group-hover:text-indigo-600">Fill</span>
              </button>

              <button
                type="button"
                onClick={() => handleQuickFill('admin@apexcare.org', 'Admin123!')}
                className="w-full text-left p-2.5 rounded-lg border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/50 transition-all flex items-center justify-between text-xs group"
              >
                <div className="flex items-center gap-2">
                  <div className="p-1 rounded bg-purple-100 text-purple-700">
                    <ShieldCheck className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <p className="font-semibold text-slate-800 group-hover:text-purple-900">Rajesh Sharma</p>
                    <p className="text-[11px] text-slate-500">Hospital Administrator (Full Scope)</p>
                  </div>
                </div>
                <span className="text-[10px] font-medium text-slate-400 group-hover:text-purple-600">Fill</span>
              </button>
            </div>
          </div>

          {/* BRD Architectural Note */}
          <div className="mt-5 p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-[11px] text-slate-500 leading-relaxed">
            <p className="font-semibold text-slate-700 mb-0.5">Clinical Access Control (BRD DB-05):</p>
            Patients interact exclusively via outbound interactive voice calls; caregivers receive consented SMS summaries. Dashboard access is strictly restricted to authenticated hospital staff.
          </div>

        </div>

        {/* Footer */}
        <p className="text-center text-xs text-slate-500 mt-6">
          Apex Heart & Recovery Institute · Post-Discharge Monitoring Platform
        </p>

      </div>
    </div>
  );
};
