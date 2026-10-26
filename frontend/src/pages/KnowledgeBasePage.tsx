import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import { KnowledgeArticle, DeclinedQueryLog } from '../types';
import {
  BookOpen,
  CheckCircle2,
  AlertCircle,
  FileText
} from 'lucide-react';

export const KnowledgeBasePage: React.FC = () => {
  const { token } = useAuth();
  const [activeTab, setActiveTab] = useState<'approved' | 'declined'>('approved');

  const [articles, setArticles] = useState<KnowledgeArticle[]>([]);
  const [declinedQueries, setDeclinedQueries] = useState<DeclinedQueryLog[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    if (!token) return;
    setIsLoading(true);

    Promise.all([
      apiClient.getKnowledgeArticles(token).catch(() => []),
      apiClient.getDeclinedQueries(token).catch(() => [])
    ])
      .then(([arts, dqs]) => {
        setArticles(arts || []);
        setDeclinedQueries(dqs || []);
      })
      .finally(() => setIsLoading(false));
  }, [token]);

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Approved Clinical Knowledge & Guardrails</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            BRD KQ-01 to KQ-05: Strict clinical guidance library and audit log of out-of-scope patient inquiries.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setActiveTab('approved')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              activeTab === 'approved'
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            Approved Documentation ({articles.length})
          </button>
          <button
            onClick={() => setActiveTab('declined')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              activeTab === 'declined'
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            Declined Inquiries ({declinedQueries.length})
          </button>
        </div>
      </div>

      {/* Content Section */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
            <div className="w-4 h-4 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            <span>Fetching clinical knowledge from database...</span>
          </div>
        ) : activeTab === 'approved' ? (
          articles.length === 0 ? (
            <div className="p-12 text-center text-slate-500 text-xs">
              <BookOpen className="w-8 h-8 text-slate-400 mx-auto mb-2" />
              <p className="font-semibold text-slate-700 text-sm">No Knowledge Articles Registered</p>
              <p className="mt-1 text-slate-400">All responses to patients will default to standard clinical escalation.</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {articles.map((art) => (
                <div key={art.id} className="p-5 hover:bg-slate-50/70 transition-colors space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-indigo-600" />
                      <span className="font-bold text-sm text-slate-900">{art.title}</span>
                      <span className="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-mono">
                        {art.category}
                      </span>
                      <span className="text-xs text-slate-400 font-medium">· v{art.version}</span>
                    </div>
                    {art.is_approved && (
                      <span className="text-xs text-emerald-700 font-semibold flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                        Approved by {art.approved_by || 'Clinical Committee'}
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                    <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                      <span className="font-semibold text-[11px] text-slate-600">English:</span>
                      <p className="text-slate-700">{art.content_en}</p>
                    </div>
                    <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                      <span className="font-semibold text-[11px] text-slate-600">Hindi:</span>
                      <p className="text-slate-700">{art.content_hi || '—'}</p>
                    </div>
                    <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                      <span className="font-semibold text-[11px] text-slate-600">Marathi:</span>
                      <p className="text-slate-700">{art.content_mr || '—'}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )
        ) : (
          declinedQueries.length === 0 ? (
            <div className="p-12 text-center text-slate-500 text-xs">
              <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
              <p className="font-semibold text-slate-700 text-sm">No Declined Inquiries Logged</p>
              <p className="mt-1 text-slate-400">All patient questions fell within approved recovery guidance.</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {declinedQueries.map((dq) => (
                <div key={dq.id} className="p-5 hover:bg-slate-50/70 transition-colors space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="w-4 h-4 text-rose-600" />
                      <span className="font-bold text-xs text-rose-700 px-2 py-0.5 rounded bg-rose-50 border border-rose-200">
                        {dq.query_type} Query Blocked
                      </span>
                      <span className="text-xs text-slate-400 font-mono">({dq.patient_id})</span>
                    </div>
                    <span className="text-xs font-semibold text-slate-600">
                      Routed to: {dq.routed_to}
                    </span>
                  </div>

                  <p className="text-xs font-medium text-slate-800">
                    Patient Question: <span className="italic font-normal">"{dq.query_text}"</span>
                  </p>
                  <p className="text-xs text-slate-600 bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                    Standard Response Delivered: <span className="text-slate-700">{dq.standard_response_delivered}</span>
                  </p>
                </div>
              ))}
            </div>
          )
        )}
      </div>

    </div>
  );
};
