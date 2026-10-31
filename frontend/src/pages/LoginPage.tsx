import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import {
  HeartPulse, Lock, Mail, Phone, AlertCircle, ShieldAlert,
  ArrowRight, UserCheck, ShieldCheck, CheckCircle2, KeyRound
} from 'lucide-react';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  const [mode, setMode] = useState<'staff' | 'patient'>('staff');
  const [patientView, setPatientView] = useState<'login' | 'register' | 'forgot'>('login');

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [phone, setPhone] = useState('+919820011223');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const redirectReason = (location.state as any)?.reason;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);

    if (mode === 'patient' && patientView === 'register') {
      // Patient Registration / Account Provisioning
      if (!email || !password || !phone) {
        setErrorMessage('Please enter email, password, and registered phone number.');
        return;
      }
      setIsLoading(true);
      try {
        await apiClient.registerPatientAccount({
          email,
          password,
          phone
        });
        setSuccessMessage('Account activated successfully! Logging you in...');
        await login(email, password);
        navigate('/portal', { replace: true });
      } catch (err: any) {
        setErrorMessage(err.message || 'Registration failed. Verify phone number matches your discharge record.');
      } finally {
        setIsLoading(false);
      }
      return;
    }

    if (patientView === 'forgot') {
      if (!email || !password) {
        setErrorMessage('Please enter your email and new password.');
        return;
      }
      setIsLoading(true);
      try {
        await apiClient.resetPassword(email, password);
        setSuccessMessage('Password reset successfully. Please sign in with your new password.');
        setPatientView('login');
      } catch (err: any) {
        setErrorMessage(err.message || 'Password reset failed.');
      } finally {
        setIsLoading(false);
      }
      return;
    }

    // Normal Login
    if (!email || !password) {
      setErrorMessage('Please enter both your email address and password.');
      return;
    }

    setIsLoading(true);
    try {
      await login(email, password);
      const from = (location.state as any)?.from?.pathname;
      if (mode === 'patient') {
        navigate('/portal', { replace: true });
      } else {
        navigate(from || '/', { replace: true });
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  const setDemoCredentials = (role: 'doctor' | 'admin' | 'patient') => {
    setErrorMessage(null);
    setSuccessMessage(null);
    if (role === 'doctor') {
      setMode('staff');
      setPatientView('login');
      setEmail('dr.neha@apexcare.org');
      setPassword('Clinician123!');
    } else if (role === 'admin') {
      setMode('staff');
      setPatientView('login');
      setEmail('admin@apexcare.org');
      setPassword('Admin123!');
    } else {
      setMode('patient');
      setPatientView('login');
      setEmail('patient.ramesh@apexcare.org');
      setPassword('Patient123!');
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col justify-center items-center p-4 sm:p-6 font-sans">
      <div className="w-full max-w-md relative z-10">

        {/* Brand Header */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-600 text-white mb-3 shadow-lg shadow-indigo-600/30">
            <HeartPulse className="w-8 h-8" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            AI Care Companion
          </h1>
          <p className="text-xs text-slate-400 mt-1 font-medium">
            Apex Heart & Recovery Institute · Post-Discharge Monitoring Platform
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-white rounded-2xl shadow-xl border border-slate-200 p-6 sm:p-8">

          {/* Mode Switcher: Staff vs Patient */}
          <div className="grid grid-cols-2 p-1 bg-slate-100 rounded-xl mb-6 text-xs font-bold">
            <button
              type="button"
              onClick={() => { setMode('staff'); setPatientView('login'); setErrorMessage(null); }}
              className={`py-2 rounded-lg transition-all ${mode === 'staff' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}
            >
              Clinical Staff
            </button>
            <button
              type="button"
              onClick={() => { setMode('patient'); setPatientView('login'); setErrorMessage(null); }}
              className={`py-2 rounded-lg transition-all ${mode === 'patient' ? 'bg-white text-emerald-700 shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}
            >
              Patient Portal
            </button>
          </div>

          <div className="mb-5">
            <h2 className="text-lg font-bold text-slate-900">
              {mode === 'staff' ? 'Clinical Workstation Sign In' : (patientView === 'register' ? 'Activate Patient Account' : (patientView === 'forgot' ? 'Reset Account Password' : 'Patient Recovery Sign In'))}
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              {mode === 'staff'
                ? 'Authorized attending clinicians, nurses, and hospital administrators'
                : (patientView === 'register' ? 'Link your discharge record using your registered phone' : 'Access your daily check-ins, medication plan, and recovery progress')}
            </p>
          </div>

          {/* Session Expiry or Error Alert */}
          {redirectReason && (
            <div className="mb-4 p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-xs flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <span>Your session has expired. Please sign in again to continue.</span>
            </div>
          )}

          {errorMessage && (
            <div className="mb-4 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-2">
              <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          {successMessage && (
            <div className="mb-4 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-start gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
              <span>{successMessage}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Registered Phone (Only in Patient Register mode) */}
            {mode === 'patient' && patientView === 'register' && (
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Registered Discharge Phone Number
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <Phone className="w-4 h-4" />
                  </div>
                  <input
                    type="tel"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="+919820011223"
                    required
                    disabled={isLoading}
                    className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-hidden focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
                  />
                </div>
                <p className="text-[10px] text-slate-400 mt-1">Must match the contact number recorded during hospital discharge.</p>
              </div>
            )}

            {/* Email Field */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                {mode === 'staff' ? 'Hospital Email Address' : 'Email Address'}
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder={mode === 'staff' ? 'clinician@apexcare.org' : 'patient@example.com'}
                  required
                  disabled={isLoading}
                  className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-hidden focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
                />
              </div>
            </div>

            {/* Password Field */}
            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="block text-xs font-semibold text-slate-700">
                  {patientView === 'forgot' ? 'New Password' : 'Password'}
                </label>
                {mode === 'patient' && patientView === 'login' && (
                  <button
                    type="button"
                    onClick={() => { setPatientView('forgot'); setErrorMessage(null); }}
                    className="text-[11px] font-semibold text-indigo-600 hover:text-indigo-800"
                  >
                    Forgot Password?
                  </button>
                )}
              </div>
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
                  className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-hidden focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
                />
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading}
              className={`w-full mt-2 font-semibold py-2.5 px-4 rounded-xl text-sm shadow-sm transition-all flex items-center justify-center gap-2 text-white ${mode === 'patient' ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-indigo-600 hover:bg-indigo-700'} disabled:opacity-50`}
            >
              {isLoading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Processing...</span>
                </>
              ) : (
                <>
                  <span>
                    {mode === 'staff' ? 'Sign In to Clinical Workstation' : (patientView === 'register' ? 'Complete Activation' : (patientView === 'forgot' ? 'Update Password' : 'Enter Patient Portal'))}
                  </span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Patient Mode Sub-links */}
          {mode === 'patient' && (
            <div className="mt-4 pt-3 border-t border-slate-100 text-center text-xs">
              {patientView === 'login' ? (
                <p className="text-slate-600">
                  First time here?{' '}
                  <button
                    type="button"
                    onClick={() => { setPatientView('register'); setErrorMessage(null); }}
                    className="text-emerald-700 font-bold hover:underline"
                  >
                    Activate Your Patient Account
                  </button>
                </p>
              ) : (
                <button
                  type="button"
                  onClick={() => { setPatientView('login'); setErrorMessage(null); }}
                  className="text-indigo-600 font-bold hover:underline"
                >
                  Back to Patient Sign In
                </button>
              )}
            </div>
          )}

          {/* Quick Demo Credentials */}
          <div className="mt-6 pt-4 border-t border-slate-100">
            <span className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2 text-center">
              Quick 1-Click Demo Sign-in
            </span>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setDemoCredentials('doctor')}
                className="py-1.5 px-2 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-[11px] font-bold transition-colors border border-indigo-200"
              >
                Dr. Neha
              </button>
              <button
                type="button"
                onClick={() => setDemoCredentials('admin')}
                className="py-1.5 px-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-[11px] font-bold transition-colors border border-slate-300"
              >
                Admin
              </button>
              <button
                type="button"
                onClick={() => setDemoCredentials('patient')}
                className="py-1.5 px-2 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-800 text-[11px] font-bold transition-colors border border-emerald-200"
              >
                Ramesh (Patient)
              </button>
            </div>
          </div>

        </div>

        {/* Footer */}
        <p className="text-center text-xs text-slate-500 mt-6">
          Apex Heart & Recovery Institute · ₹0 Verified Clinical Recovery System
        </p>

      </div>
    </div>
  );
};
