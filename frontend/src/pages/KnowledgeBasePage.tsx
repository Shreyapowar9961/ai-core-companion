import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import { KnowledgeArticle, DeclinedQueryLog } from '../types';
import {
  BookOpen,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  FileText,
  Languages,
  ArrowRight
} from 'lucide-react';

export const KnowledgeBasePage: React.FC = () => {
  const { token } = useAuth();
  const [activeTab, setActiveTab] = useState<'approved' | 'declined'>('approved');

  const [articles, setArticles] = useState<KnowledgeArticle[]>([
    {
      id: 'kb-1',
      title: 'Post-CABG Sternal Wound Care & Healing',
      category: 'WOUND_CARE',
      condition_name: 'Post-CABG',
      content_en: 'Keep your sternal incision clean and dry. Shower gently with mild soap; do not scrub the wound. Look out for any redness, warmth, or drainage.',
      content_hi: 'Apne seene ke ghaav ko saaf aur sukha rakhein. Halki saaban se dhoye aur ghaav ko ragde nahi. Lalima ya paani aane par turant doctor se sampark karein.',
      content_mr: 'Chaatiche kshete swachha aani kore theva. Halukawar saban vapra. Lal zalyas kiwa paani aalyas doctoranshi sampark kara.',
      version: 2,
      is_approved: true,
      approved_by: 'Dr. Neha Kulkarni',
      updated_at: '2026-10-20T10:00:00Z'
    },
    {
      id: 'kb-2',
      title: 'Post-Angioplasty Hydration & Rest Guidelines',
      category: 'LIFESTYLE',
      condition_name: 'Post-Angioplasty',
      content_en: 'Drink at least 8 to 10 glasses of water daily to flush the contrast dye used during your stent procedure. Avoid lifting objects over 5kg for the first 7 days.',
      content_hi: 'Stent daalne ke baad rozana kam se kam 8 se 10 gilas paani piyein. Pehle 7 din 5 kilo se bhari wazan na uthayein.',
      content_mr: 'Stent nantar roj 8 te 10 bhande paani pya. Pahile 7 divas 5 kilo peksha jast vajan uchalu naka.',
      version: 1,
      is_approved: true,
      approved_by: 'Dr. Sharma',
      updated_at: '2026-10-18T14:30:00Z'
    },
    {
      id: 'kb-3',
      title: 'Recognizing Cardiac Warning Signs & When to Seek Help',
      category: 'SYMPTOMS',
      condition_name: 'All Cardiac Post-Discharge',
      content_en: 'If you experience severe pressure or squeezing in your chest, pain radiating to your left arm or jaw, or sudden severe breathlessness, call emergency services immediately.',
      content_hi: 'Agar seene mein tezz dabav, bayein haath mein dard ya achanak saas lene mein taklif ho, toh turant emergency number par call karein.',
      content_mr: 'Chaateet asahy vedna, davya hathat tras kiwa achanak dam laglyas tatkal emergency number var call kara.',
      version: 3,
      is_approved: true,
      approved_by: 'Clinical Governance Committee',
      updated_at: '2026-10-22T09:00:00Z'
    }
  ]);

  const [declinedQueries, setDeclinedQueries] = useState<DeclinedQueryLog[]>([
    {
      id: 'dq-1',
      patient_id: 'patient-demo-1',
      query_text: 'Can I increase my dose of Atorvastatin to 40mg to lower my cholesterol faster?',
      query_type: 'DOSAGE',
      routed_to: 'TREATING_DOCTOR (Dr. Neha Kulkarni)',
      standard_response_delivered: 'I cannot advise on changing medication doses. I have queued a call back from Dr. Neha Kulkarni to review your prescription safely.',
      created_at: new Date(Date.now() - 3600000).toISOString()
    },
    {
      id: 'dq-2',
      patient_id: 'patient-demo-2',
      query_text: 'Do you think my chest pain means my stent failed or I am having a heart attack?',
      query_type: 'DIAGNOSIS',
      routed_to: 'ATTENDING_CARDIOLOGY_TEAM',
      standard_response_delivered: 'I cannot provide a diagnosis. For severe or worsening symptoms, please consult your doctor immediately. Emergency callback queued.',
      created_at: new Date(Date.now() - 7200000).toISOString()
    }
  ]);

  useEffect(() => {
    apiClient.getKnowledgeArticles(token)
      .then((data) => {
        if (data && data.length > 0) setArticles(data);
      })
      .catch((err) => console.log('Using default knowledge fallback:', err.message));

    apiClient.getDeclinedQueries(token)
      .then((data) => {
        if (data && data.length > 0) setDeclinedQueries(data);
      })
      .catch((err) => console.log('Using default declined queries fallback:', err.message));
  }, [token]);

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center space-x-2">
          <BookOpen className="w-6 h-6 text-indigo-600" />
          <span>Clinical Knowledge Library & Safety Guardrails (KQ-01 to KQ-05)</span>
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Strict guardrail enforcement: AI answers questions ONLY from approved documentation. Diagnosis, triage, and dosage inquiries are strictly forbidden and routed to clinicians.
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200">
        <nav className="flex space-x-6 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('approved')}
            className={`pb-3 border-b-2 transition-all ${
              activeTab === 'approved'
                ? 'border-indigo-600 text-indigo-600 font-bold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            Approved Clinical Knowledge ({articles.length})
          </button>
          <button
            onClick={() => setActiveTab('declined')}
            className={`pb-3 border-b-2 transition-all ${
              activeTab === 'declined'
                ? 'border-indigo-600 text-indigo-600 font-bold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            Declined & Routed Queries Log (KQ-05) ({declinedQueries.length})
          </button>
        </nav>
      </div>

      {/* Tab 1: Approved Library */}
      {activeTab === 'approved' && (
        <div className="space-y-4">
          <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-center space-x-3 text-xs text-emerald-900">
            <ShieldCheck className="w-5 h-5 text-emerald-600 shrink-0" />
            <div>
              <p className="font-bold">Clinical Governance Mandate (KQ-01 & KQ-04)</p>
              <p className="text-[11px] text-emerald-800">
                All voice conversational responses are strictly grounded in this versioned library. If information is not present, the agent states it is unavailable plainly (KQ-02).
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {articles.map((art) => (
              <div key={art.id} className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-[10px] bg-indigo-50 text-indigo-700 font-bold px-2 py-0.5 rounded-sm">
                      {art.category} · {art.condition_name}
                    </span>
                    <h3 className="font-bold text-sm text-slate-900 mt-1">{art.title}</h3>
                  </div>
                  <span className="text-[10px] bg-slate-100 text-slate-600 font-mono px-2 py-0.5 rounded-md font-semibold">
                    v{art.version}.0
                  </span>
                </div>

                {/* Multilingual Content Tabs */}
                <div className="space-y-2 text-xs">
                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1 flex items-center">
                      <Languages className="w-3 h-3 mr-1 text-indigo-600" />
                      English (en)
                    </p>
                    <p className="text-slate-700 leading-relaxed">{art.content_en}</p>
                  </div>

                  {art.content_hi && (
                    <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1 flex items-center">
                        <Languages className="w-3 h-3 mr-1 text-indigo-600" />
                        Hindi (hi)
                      </p>
                      <p className="text-slate-700 leading-relaxed font-sans">{art.content_hi}</p>
                    </div>
                  )}

                  {art.content_mr && (
                    <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1 flex items-center">
                        <Languages className="w-3 h-3 mr-1 text-indigo-600" />
                        Marathi (mr)
                      </p>
                      <p className="text-slate-700 leading-relaxed font-sans">{art.content_mr}</p>
                    </div>
                  )}
                </div>

                <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400">
                  <span>Approved by: <strong className="text-slate-700">{art.approved_by}</strong></span>
                  <span>{new Date(art.updated_at).toLocaleDateString()}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 2: Declined Queries Log (KQ-05) */}
      {activeTab === 'declined' && (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
          <div className="p-4 border-b border-slate-200">
            <h3 className="font-bold text-sm text-slate-900">Declined Queries & Clinician Routing Stream (KQ-05, MD-07)</h3>
            <p className="text-xs text-slate-500">
              Audit log of all queries where the AI was asked for medical diagnosis or dosage determination.
            </p>
          </div>
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 uppercase tracking-wider font-semibold">
              <tr>
                <th className="px-4 py-3">Timestamp</th>
                <th className="px-4 py-3">Patient ID</th>
                <th className="px-4 py-3">Query Type</th>
                <th className="px-4 py-3">Verbatim Patient Query</th>
                <th className="px-4 py-3">Standard Response Delivered</th>
                <th className="px-4 py-3">Routed Destination</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {declinedQueries.map((q) => (
                <tr key={q.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium text-slate-700">
                    {new Date(q.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </td>
                  <td className="px-4 py-3 font-mono text-slate-800">{q.patient_id}</td>
                  <td className="px-4 py-3">
                    <span className="bg-rose-50 text-rose-700 border border-rose-200 px-2 py-0.5 rounded-sm font-bold text-[10px]">
                      {q.query_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-medium text-slate-900 max-w-xs">"{q.query_text}"</td>
                  <td className="px-4 py-3 text-slate-600 max-w-xs leading-relaxed text-[11px]">
                    {q.standard_response_delivered}
                  </td>
                  <td className="px-4 py-3 font-semibold text-indigo-700">{q.routed_to}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

    </div>
  );
};
