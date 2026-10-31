import React, { useState } from 'react';
import { apiClient } from '../api/client';
import {
  FileText, Upload, CheckCircle2, AlertCircle, Plus, Trash2,
  FileCheck, ShieldCheck, X, Eye
} from 'lucide-react';
import { PrescriptionUpload } from '../types';

interface PrescriptionVerificationModalProps {
  isOpen: boolean;
  onClose: () => void;
  patientId: string;
  patientName: string;
  token?: string | null;
  onVerificationComplete: () => void;
}

export const PrescriptionVerificationModal: React.FC<PrescriptionVerificationModalProps> = ({
  isOpen,
  onClose,
  patientId,
  patientName,
  token,
  onVerificationComplete
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadResult, setUploadResult] = useState<PrescriptionUpload | null>(null);
  const [editableMeds, setEditableMeds] = useState<any[]>([]);
  const [clinicianNotes, setClinicianNotes] = useState<string>('');
  const [isVerifying, setIsVerifying] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setStatusMessage(null);
    }
  };

  const handleUploadAndOCR = async () => {
    if (!file || !token) return;
    setIsUploading(true);
    setStatusMessage(null);
    try {
      const res = await apiClient.uploadPrescription(token, patientId, file);
      setUploadResult(res);
      setEditableMeds(res.extracted_medications || []);
      setStatusMessage({
        type: 'success',
        text: `Prescription processed via local OCR. ${res.extracted_medications?.length || 0} medications extracted for review.`
      });
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Prescription OCR failed.' });
    } finally {
      setIsUploading(false);
    }
  };

  const handleUpdateMedField = (index: number, field: string, value: any) => {
    const updated = [...editableMeds];
    updated[index] = { ...updated[index], [field]: value };
    setEditableMeds(updated);
  };

  const handleAddMed = () => {
    setEditableMeds([
      ...editableMeds,
      {
        medicine_name: 'New Medication',
        dosage: '1 tablet',
        frequency: 'Once daily',
        dose_times: ['09:00'],
        instructions: 'Take after meals with water',
        status: 'UNVERIFIED'
      }
    ]);
  };

  const handleRemoveMed = (index: number) => {
    setEditableMeds(editableMeds.filter((_, i) => i !== index));
  };

  const handleVerifyAndApprove = async () => {
    if (!uploadResult || !token) return;
    if (editableMeds.length === 0) {
      setStatusMessage({ type: 'error', text: 'At least one verified medication is required to activate schedule.' });
      return;
    }
    setIsVerifying(true);
    setStatusMessage(null);
    try {
      await apiClient.verifyPrescription(token, uploadResult.id, {
        verified_medications: editableMeds,
        clinician_notes: clinicianNotes || 'Clinician verified discharge prescription.'
      });
      setStatusMessage({
        type: 'success',
        text: `Prescription verified! ${editableMeds.length} active medication schedules activated.`
      });
      setTimeout(() => {
        onVerificationComplete();
        onClose();
      }, 1500);
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Verification approval failed.' });
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl max-w-3xl w-full p-6 sm:p-8 shadow-2xl border border-slate-200 my-8">
        
        {/* Modal Header */}
        <div className="flex items-start justify-between border-b border-slate-100 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-2 rounded-xl bg-indigo-50 text-indigo-600">
                <FileCheck className="w-5 h-5" />
              </span>
              <h3 className="text-lg font-bold text-slate-900">
                Prescription Upload & Clinician Verification
              </h3>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Patient: <strong>{patientName}</strong> · Free Local Tesseract OCR (₹0 External Cost)
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Status Notification */}
        {statusMessage && (
          <div className={`mt-4 p-3 rounded-xl border text-xs font-semibold flex items-center gap-2 ${statusMessage.type === 'success' ? 'bg-emerald-50 border-emerald-200 text-emerald-800' : 'bg-rose-50 border-rose-200 text-rose-800'}`}>
            {statusMessage.type === 'success' ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
            <span>{statusMessage.text}</span>
          </div>
        )}

        {/* Step 1: File Upload */}
        {!uploadResult && (
          <div className="mt-6 space-y-4">
            <div className="border-2 border-dashed border-slate-300 rounded-2xl p-8 text-center hover:border-indigo-500 transition-colors bg-slate-50/50">
              <Upload className="w-10 h-10 text-indigo-500 mx-auto mb-3" />
              <label className="cursor-pointer block">
                <span className="text-xs font-bold text-indigo-600 hover:text-indigo-800">
                  Click to select prescription image or PDF
                </span>
                <span className="block text-[11px] text-slate-400 mt-1">
                  Supports PNG, JPG, JPEG, and PDF documents (Max 10MB)
                </span>
                <input
                  type="file"
                  accept=".png,.jpg,.jpeg,.pdf"
                  onChange={handleFileChange}
                  className="hidden"
                />
              </label>
              {file && (
                <div className="mt-3 inline-flex items-center gap-2 text-xs font-semibold text-slate-800 bg-white px-3 py-1.5 rounded-lg border border-slate-200 shadow-xs">
                  <FileText className="w-4 h-4 text-indigo-600" />
                  <span>{file.name}</span> ({(file.size / 1024).toFixed(1)} KB)
                </div>
              )}
            </div>

            <button
              type="button"
              onClick={handleUploadAndOCR}
              disabled={!file || isUploading}
              className="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs shadow-md transition-all disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isUploading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Executing Local OCR Engine...</span>
                </>
              ) : (
                <>
                  <FileCheck className="w-4 h-4" />
                  <span>Run OCR Extraction</span>
                </>
              )}
            </button>
          </div>
        )}

        {/* Step 2: Clinician Review & Verification Form */}
        {uploadResult && (
          <div className="mt-6 space-y-6">
            {/* Raw OCR Text Accordion / Preview */}
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
              <span className="text-xs font-bold text-slate-700 block mb-1">
                Raw Extracted OCR Text (Unverified)
              </span>
              <pre className="text-[11px] font-mono text-slate-600 max-h-24 overflow-y-auto whitespace-pre-wrap bg-white p-2 rounded-lg border border-slate-200">
                {uploadResult.raw_ocr_text || 'No text extracted.'}
              </pre>
            </div>

            {/* Structured Medications Verification Table */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  Medications Extracted for Doctor Approval ({editableMeds.length})
                </span>
                <button
                  type="button"
                  onClick={handleAddMed}
                  className="inline-flex items-center gap-1 text-xs font-bold text-indigo-600 hover:text-indigo-800 bg-indigo-50 px-2.5 py-1 rounded-lg"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add Drug</span>
                </button>
              </div>

              <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
                {editableMeds.map((med, idx) => (
                  <div key={idx} className="p-3 rounded-xl border border-slate-200 bg-white shadow-xs flex flex-col gap-2">
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                      <div>
                        <label className="block text-[10px] font-bold text-slate-500 uppercase">Medicine Name</label>
                        <input
                          type="text"
                          value={med.medicine_name}
                          onChange={(e) => handleUpdateMedField(idx, 'medicine_name', e.target.value)}
                          className="w-full text-xs font-semibold px-2 py-1 rounded border border-slate-300"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] font-bold text-slate-500 uppercase">Dosage</label>
                        <input
                          type="text"
                          value={med.dosage}
                          onChange={(e) => handleUpdateMedField(idx, 'dosage', e.target.value)}
                          className="w-full text-xs font-semibold px-2 py-1 rounded border border-slate-300"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] font-bold text-slate-500 uppercase">Frequency</label>
                        <input
                          type="text"
                          value={med.frequency}
                          onChange={(e) => handleUpdateMedField(idx, 'frequency', e.target.value)}
                          className="w-full text-xs font-semibold px-2 py-1 rounded border border-slate-300"
                        />
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <div className="flex-1">
                        <label className="block text-[10px] font-bold text-slate-500 uppercase">Instructions</label>
                        <input
                          type="text"
                          value={med.instructions || ''}
                          onChange={(e) => handleUpdateMedField(idx, 'instructions', e.target.value)}
                          className="w-full text-xs font-medium px-2 py-1 rounded border border-slate-300"
                        />
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRemoveMed(idx)}
                        className="p-1 text-slate-400 hover:text-rose-600 mt-3"
                        title="Remove Drug"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Clinician Notes */}
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Clinical Approval Notes
              </label>
              <textarea
                rows={2}
                value={clinicianNotes}
                onChange={(e) => setClinicianNotes(e.target.value)}
                placeholder="Discharge regimen verified against cardiology protocol..."
                className="w-full text-xs p-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              />
            </div>

            {/* Actions */}
            <div className="flex items-center gap-3 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setUploadResult(null)}
                className="px-4 py-2 rounded-xl border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-50"
              >
                Upload Another File
              </button>
              <button
                type="button"
                onClick={handleVerifyAndApprove}
                disabled={isVerifying}
                className="flex-1 py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-md transition-all flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {isVerifying ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Activating Medication Schedules...</span>
                  </>
                ) : (
                  <>
                    <ShieldCheck className="w-4 h-4" />
                    <span>Approve & Activate Medication Schedule (Phase 4)</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};
