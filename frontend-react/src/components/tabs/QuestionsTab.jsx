import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, ChevronDown, ChevronUp, AlertTriangle, Check, Save } from 'lucide-react';
import { getQuestions, getAnswer, patchAnswer, approveAnswer, getResponseCodes, putResponseCode } from '../../api.js';
import Badge from '../ui/Badge.jsx';
import ConfidenceBar from '../ui/ConfidenceBar.jsx';
import CitationList from '../ui/CitationCard.jsx';
import ResponseCodeBadge from '../ui/ResponseCodeBadge.jsx';

function parseJsonField(val) {
  if (!val) return [];
  if (Array.isArray(val)) return val;
  try {
    return JSON.parse(val);
  } catch {
    return [];
  }
}

function statusVariant(status) {
  const s = (status || '').toLowerCase();
  if (s.includes('approved')) return 'approved';
  if (s.includes('flagged')) return 'flagged_owner';
  if (s.includes('clarification')) return 'clarification';
  if (s.includes('pending')) return 'pending';
  return 'draft';
}

function MetricCard({ label, value, color = 'indigo' }) {
  const colorMap = {
    indigo: 'text-indigo-600',
    yellow: 'text-yellow-600',
    red: 'text-red-600',
    green: 'text-green-600',
  };
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm text-center">
      <p className={`text-3xl font-bold ${colorMap[color] || colorMap.indigo}`}>{value}</p>
      <p className="text-xs text-gray-500 mt-1">{label}</p>
    </div>
  );
}

export default function QuestionsTab({ sessionId }) {
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedQuestion, setSelectedQuestion] = useState(null);
  const [answer, setAnswer] = useState(null);
  const [answerLoading, setAnswerLoading] = useState(false);
  const [editText, setEditText] = useState('');
  const [saving, setSaving] = useState(false);
  const [approving, setApproving] = useState(false);
  const [citationsExpanded, setCitationsExpanded] = useState(false);

  // Response codes (S/C/D/T/N) persisted server-side per session
  const [responseCodes, setResponseCodes] = useState({});
  const [codesLoading, setCodesLoading] = useState(false);

  const fetchResponseCodes = useCallback(async () => {
    if (!sessionId) return;
    setCodesLoading(true);
    try {
      const data = await getResponseCodes(sessionId);
      const map = {};
      (Array.isArray(data) ? data : []).forEach((rc) => {
        map[rc.question_id] = rc.code;
      });
      setResponseCodes(map);
    } catch (e) {
      console.error('fetchResponseCodes error:', e);
    } finally {
      setCodesLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchResponseCodes();
  }, [fetchResponseCodes]);

  const handleResponseCodeChange = async (questionId, code) => {
    setResponseCodes((prev) => ({ ...prev, [questionId]: code }));
    await putResponseCode(sessionId, questionId, {
      code,
      explanation: '',
      validated_by_se: false,
    });
    await fetchResponseCodes();
  };

  // Filters
  const [filterCategory, setFilterCategory] = useState('');
  const [filterOwner, setFilterOwner] = useState('');
  const [filterStatus, setFilterStatus] = useState('');

  // Sort
  const [sortField, setSortField] = useState('req_number');
  const [sortDir, setSortDir] = useState('asc');

  const fetchQuestions = useCallback(async () => {
    setLoading(true);
    const data = await getQuestions(sessionId);
    setQuestions(Array.isArray(data) ? data : []);
    setLoading(false);
  }, [sessionId]);

  useEffect(() => {
    fetchQuestions();
  }, [fetchQuestions]);

  const fetchAnswer = useCallback(async (questionId) => {
    setAnswerLoading(true);
    const data = await getAnswer(questionId);
    setAnswer(data);
    setEditText(data?.text || '');
    setAnswerLoading(false);
  }, []);

  const handleSelectQuestion = (q) => {
    setSelectedQuestion(q);
    setCitationsExpanded(false);
    fetchAnswer(q.id);
  };

  const handleSave = async () => {
    if (!selectedQuestion) return;
    setSaving(true);
    const updated = await patchAnswer(selectedQuestion.id, editText);
    if (updated) setAnswer(updated);
    await fetchQuestions();
    setSaving(false);
  };

  const handleApprove = async () => {
    if (!selectedQuestion) return;
    setApproving(true);
    const updated = await approveAnswer(selectedQuestion.id);
    if (updated) setAnswer(updated);
    await fetchQuestions();
    setApproving(false);
  };

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDir('asc');
    }
  };

  // Unique filter options
  const categories = [...new Set(questions.map(q => q.category).filter(Boolean))];
  const owners = [...new Set(questions.map(q => q.owner).filter(Boolean))];
  const statuses = [...new Set(questions.map(q => q.status).filter(Boolean))];

  // Filter
  const filtered = questions.filter(q => {
    if (filterCategory && q.category !== filterCategory) return false;
    if (filterOwner && q.owner !== filterOwner) return false;
    if (filterStatus && q.status !== filterStatus) return false;
    return true;
  });

  // Sort
  const sorted = [...filtered].sort((a, b) => {
    let av = a[sortField];
    let bv = b[sortField];
    if (typeof av === 'string') av = av.toLowerCase();
    if (typeof bv === 'string') bv = bv.toLowerCase();
    if (av < bv) return sortDir === 'asc' ? -1 : 1;
    if (av > bv) return sortDir === 'asc' ? 1 : -1;
    return 0;
  });

  // Metrics
  const total = questions.length;
  const flagged = questions.filter(q => (q.status || '').toLowerCase().includes('flagged')).length;
  const pending = questions.filter(q => (q.status || '').toLowerCase().includes('pending')).length;
  const approved = questions.filter(q => (q.status || '').toLowerCase().includes('approved')).length;

  const SortIcon = ({ field }) => {
    if (sortField !== field) return <span className="text-gray-300 ml-1">↕</span>;
    return <span className="text-blue-500 ml-1">{sortDir === 'asc' ? '↑' : '↓'}</span>;
  };

  const citations = parseJsonField(answer?.citations_json);
  const staleWarnings = parseJsonField(answer?.stale_warnings_json);
  const isApproved = (answer?.status || '').toLowerCase().includes('approved');
  // Backend AnswerOut uses `confidence`; older drafts may use `confidence_score`.
  const confidence = answer?.confidence_score ?? answer?.confidence;

  return (
    <div className="space-y-4">
      {/* Metrics */}
      <div className="grid grid-cols-4 gap-4">
        <MetricCard label="Total Questions" value={total} color="indigo" />
        <MetricCard label="🏷️ Flagged to Owner" value={flagged} color="indigo" />
        <MetricCard label="⏳ Pending" value={pending} color="yellow" />
        <MetricCard label="✅ Approved" value={approved} color="green" />
      </div>

      {/* Filter bar */}
      <div className="bg-white border border-gray-200 rounded-xl p-3 shadow-sm flex gap-3 flex-wrap items-center">
        <span className="text-xs font-medium text-gray-500">Filter:</span>
        <select
          value={filterCategory}
          onChange={e => setFilterCategory(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-2 py-1.5 text-gray-700 focus:outline-none focus:border-blue-400"
        >
          <option value="">All Categories</option>
          {categories.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <select
          value={filterOwner}
          onChange={e => setFilterOwner(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-2 py-1.5 text-gray-700 focus:outline-none focus:border-blue-400"
        >
          <option value="">All Owners</option>
          {owners.map(o => <option key={o} value={o}>{o}</option>)}
        </select>
        <select
          value={filterStatus}
          onChange={e => setFilterStatus(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-2 py-1.5 text-gray-700 focus:outline-none focus:border-blue-400"
        >
          <option value="">All Statuses</option>
          {statuses.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <button
          onClick={() => { setFilterCategory(''); setFilterOwner(''); setFilterStatus(''); }}
          className="text-xs text-gray-400 hover:text-gray-600 underline ml-auto"
        >
          Clear
        </button>
      </div>

      {/* Questions table */}
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="py-12 text-center text-gray-400 flex items-center justify-center gap-2">
            <RefreshCw size={16} className="animate-spin" /> Loading questions…
          </div>
        ) : sorted.length === 0 ? (
          <div className="py-12 text-center text-gray-400 text-sm">
            No questions found. Upload and analyze an RFP to generate questions.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {[
                    { key: 'req_number', label: 'No.' },
                    { key: 'category', label: 'Category' },
                    { key: 'owner', label: 'Owner' },
                    { key: 'status', label: 'Status' },
                    { key: 'mandatory', label: 'Mandatory' },
                    { key: 'response_code', label: 'Response Code' },
                    { key: 'question_text', label: 'Question' },
                  ].map(col => (
                    <th
                      key={col.key}
                      onClick={() => handleSort(col.key)}
                      className="px-3 py-2.5 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider cursor-pointer hover:bg-gray-100 whitespace-nowrap"
                    >
                      {col.label}<SortIcon field={col.key} />
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {sorted.map((q, i) => {
                  const isSelected = selectedQuestion?.id === q.id;
                  return (
                    <tr
                      key={q.id || i}
                      onClick={() => handleSelectQuestion(q)}
                      className={`cursor-pointer transition-colors ${
                        isSelected
                          ? 'bg-blue-50 border-l-2 border-l-blue-500'
                          : 'hover:bg-gray-50'
                      }`}
                    >
                      <td className="px-3 py-2.5 font-mono text-xs text-gray-500 whitespace-nowrap">
                        {(q.req_number ?? q.number) || q.id?.toString().slice(0, 8) || i + 1}
                      </td>
                      <td className="px-3 py-2.5 whitespace-nowrap">
                        {q.category ? (
                          <Badge label={q.category} variant="info" />
                        ) : '—'}
                      </td>
                      <td className="px-3 py-2.5 text-gray-600 whitespace-nowrap">{q.owner || '—'}</td>
                      <td className="px-3 py-2.5 whitespace-nowrap">
                        <Badge label={q.status || 'Unknown'} variant={statusVariant(q.status)} />
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        {q.mandatory ? (
                          <Badge label="Yes" variant="mandatory" />
                        ) : (
                          <span className="text-gray-300 text-xs">—</span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        <ResponseCodeBadge
                          code={responseCodes[q.id] || ''}
                          editable
                          onChange={(c) => handleResponseCodeChange(q.id, c)}
                        />
                      </td>
                      <td className="px-3 py-2.5 text-gray-700 max-w-xs">
                        <span className="block truncate" title={q.question_text ?? q.text}>
                          {(q.question_text ?? q.text) || '—'}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Question Inspector */}
      {selectedQuestion && (
        <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-5 space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                <span className="text-xs font-mono text-gray-400">
                  {selectedQuestion.req_number || selectedQuestion.id}
                </span>
                {selectedQuestion.category && (
                  <Badge label={selectedQuestion.category} variant="info" />
                )}
                {selectedQuestion.mandatory && (
                  <Badge label="Mandatory" variant="mandatory" />
                )}
              </div>
              <div className="bg-blue-50 border border-blue-100 rounded-lg p-3 text-sm text-gray-700 leading-relaxed">
                {selectedQuestion.question_text}
              </div>
            </div>
          </div>

          {/* Confidence bar */}
          {answerLoading ? (
            <div className="text-sm text-gray-400 flex items-center gap-2">
              <RefreshCw size={14} className="animate-spin" /> Loading answer…
            </div>
          ) : answer && (
            <div className="space-y-3">
              {/* Confidence */}
              {confidence != null && (
                <div>
                  <p className="text-xs font-semibold text-gray-500 mb-1.5">Confidence Score</p>
                  <ConfidenceBar value={confidence} />
                </div>
              )}

              {/* Status + version */}
              <div className="flex items-center gap-2 flex-wrap">
                <Badge label={answer.status || selectedQuestion.status || 'Unknown'} variant={statusVariant(answer.status)} />
                {answer.version && (
                  <Badge label={`v${answer.version}`} variant="draft" />
                )}
              </div>

              {/* Stale warnings */}
              {staleWarnings.map((w, i) => (
                <div key={i} className="flex items-start gap-2 bg-yellow-50 border border-yellow-200 text-yellow-800 px-3 py-2 rounded-lg text-xs">
                  <AlertTriangle size={13} className="flex-shrink-0 mt-0.5" />
                  {typeof w === 'string' ? w : JSON.stringify(w)}
                </div>
              ))}

              {/* Editable draft answer */}
              <div>
                <label className="text-xs font-semibold text-gray-500 mb-1.5 block">
                  Draft Answer
                </label>
                <textarea
                  value={editText}
                  onChange={e => setEditText(e.target.value)}
                  rows={8}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700 focus:outline-none focus:border-blue-400 resize-y"
                  placeholder="Enter draft answer here…"
                />
              </div>

              {/* Action buttons */}
              <div className="flex gap-3">
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="flex items-center gap-2 bg-gray-700 hover:bg-gray-800 disabled:opacity-50 text-white text-sm font-medium py-2 px-4 rounded-lg transition-colors"
                >
                  {saving ? <RefreshCw size={14} className="animate-spin" /> : <Save size={14} />}
                  {saving ? 'Saving…' : '💾 Save Edits (New Version)'}
                </button>

                {isApproved ? (
                  <div className="flex items-center gap-2 bg-green-100 border border-green-200 text-green-700 text-sm font-medium py-2 px-4 rounded-lg">
                    <Check size={14} />
                    Approved on {answer.approved_at
                      ? new Date(answer.approved_at).toLocaleDateString()
                      : '—'}
                  </div>
                ) : (
                  <button
                    onClick={handleApprove}
                    disabled={approving}
                    className="flex items-center gap-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white text-sm font-medium py-2 px-4 rounded-lg transition-colors"
                  >
                    {approving ? <RefreshCw size={14} className="animate-spin" /> : <Check size={14} />}
                    {approving ? 'Approving…' : '✅ Approve Answer'}
                  </button>
                )}
              </div>

              {/* Citations */}
              <div>
                <button
                  className="flex items-center gap-1.5 text-xs font-semibold text-gray-500 hover:text-gray-700"
                  onClick={() => setCitationsExpanded(v => !v)}
                >
                  {citationsExpanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                  Citations ({citations.length})
                </button>
                {citationsExpanded && (
                  <div className="mt-2">
                    <CitationList citations={citations} />
                  </div>
                )}
              </div>
            </div>
          )}

          {!answerLoading && !answer && (
            <p className="text-sm text-gray-400 italic">No answer generated yet.</p>
          )}
        </div>
      )}
    </div>
  );
}
