import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  RefreshCw,
  Search,
  Users,
  FileText,
  ArrowRight,
} from 'lucide-react';
import { getGaps, regenerateGaps } from '../../api.js';

const GAP_TYPE_LABELS = {
  functionality: 'Functionality Gap',
  integration: 'Integration Dependency',
  security: 'Security Concern',
  documentation: 'Missing Documentation',
};

const GAP_TYPE_COLORS = {
  functionality: 'text-red-700 bg-red-50 border-red-200',
  integration: 'text-amber-700 bg-amber-50 border-amber-200',
  security: 'text-indigo-700 bg-indigo-50 border-indigo-200',
  documentation: 'text-blue-700 bg-blue-50 border-blue-200',
};

const OWNER_LABELS = {
  product: 'Product Management',
  engineering: 'Engineering',
  architecture: 'Solution Architecture',
};

export default function GapAnalysisTab({ sessionId }) {
  const [gaps, setGaps] = useState([]);
  const [loading, setLoading] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [filterType, setFilterType] = useState('');
  const [filterSeverity, setFilterSeverity] = useState('');
  const [filterOwner, setFilterOwner] = useState('');

  const fetchGaps = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    try {
      const data = await getGaps(sessionId);
      setGaps(Array.isArray(data?.gaps) ? data.gaps : []);
    } catch (e) {
      console.error('GapAnalysis fetch error:', e);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchGaps();
  }, [fetchGaps]);

  const handleRegenerate = async () => {
    setRegenerating(true);
    try {
      const data = await regenerateGaps(sessionId);
      if (data) setGaps(Array.isArray(data.gaps) ? data.gaps : []);
    } catch (e) {
      console.error('regenerateGaps error:', e);
    } finally {
      setRegenerating(false);
    }
  };

  const filtered = useMemo(() => {
    return gaps.filter((g) => {
      if (filterType && g.gap_type !== filterType) return false;
      if (filterSeverity && g.severity !== filterSeverity) return false;
      if (filterOwner && g.recommended_owner !== filterOwner) return false;
      return true;
    });
  }, [gaps, filterType, filterSeverity, filterOwner]);

  const typeOptions = useMemo(
    () => [...new Set(gaps.map((g) => g.gap_type))],
    [gaps]
  );

  const highCount = gaps.filter((g) => g.severity === 'High').length;
  const confirmedCount = gaps.filter((g) => g.confirmed_gap).length;
  const knowledgeCount = gaps.filter((g) => !g.confirmed_gap).length;

  if (loading)
    return (
      <div className="py-12 flex flex-col items-center justify-center text-gray-400">
        <RefreshCw size={24} className="animate-spin mb-2" />
        <p>Running gap analysis…</p>
      </div>
    );

  return (
    <div className="space-y-4">
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-5">
        <div className="flex items-center gap-2 mb-2">
          <Search size={20} className="text-indigo-600" />
          <h3 className="text-lg font-bold">AI-Driven Gap Analysis</h3>
        </div>
        <p className="text-sm text-gray-600">
          Compares customer requirements against available product capabilities.
          Distinguishes confirmed product gaps from knowledge gaps and recommends
          the internal team best placed to resolve each.
        </p>
        <div className="mt-3 flex items-center gap-3">
          <button
            onClick={handleRegenerate}
            disabled={regenerating}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium py-1.5 px-3 rounded-lg transition-colors"
          >
            <RefreshCw size={14} className={regenerating ? 'animate-spin' : ''} />
            {regenerating ? 'Regenerating…' : '🔄 Re-run Gap Analysis'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white border border-gray-200 rounded-xl p-4 text-center shadow-sm">
          <p className="text-2xl font-bold text-red-600">{highCount}</p>
          <p className="text-xs text-gray-500 mt-1">High Severity</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-4 text-center shadow-sm">
          <p className="text-2xl font-bold text-indigo-600">{confirmedCount}</p>
          <p className="text-xs text-gray-500 mt-1">Confirmed Product Gaps</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-4 text-center shadow-sm">
          <p className="text-2xl font-bold text-blue-600">{knowledgeCount}</p>
          <p className="text-xs text-gray-500 mt-1">Knowledge Gaps</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-4 text-center shadow-sm">
          <p className="text-2xl font-bold text-amber-600">{gaps.length}</p>
          <p className="text-xs text-gray-500 mt-1">Total Gaps</p>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm flex flex-wrap gap-3 items-center">
        <span className="text-xs font-semibold text-gray-500">Filter:</span>
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-2 py-1.5 text-gray-700 focus:outline-none focus:border-indigo-400"
        >
          <option value="">All Types</option>
          {typeOptions.map((t) => (
            <option key={t} value={t}>
              {GAP_TYPE_LABELS[t] || t}
            </option>
          ))}
        </select>
        <select
          value={filterSeverity}
          onChange={(e) => setFilterSeverity(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-2 py-1.5 text-gray-700 focus:outline-none focus:border-indigo-400"
        >
          <option value="">All Severities</option>
          <option value="High">High</option>
          <option value="Medium">Medium</option>
          <option value="Low">Low</option>
        </select>
        <select
          value={filterOwner}
          onChange={(e) => setFilterOwner(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-2 py-1.5 text-gray-700 focus:outline-none focus:border-indigo-400"
        >
          <option value="">All Owners</option>
          {Object.entries(OWNER_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
      </div>

      {/* Gap list */}
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
        {filtered.length === 0 ? (
          <div className="py-12 text-center text-gray-400">
            <FileText size={32} className="mx-auto mb-3 opacity-50" />
            <p>No gaps identified.</p>
            <p className="text-xs mt-1 text-gray-400">
              All requirements appear addressed or none extracted yet.
            </p>
          </div>
        ) : (
          <table className="w-full text-sm divide-y divide-gray-100">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                  Req #</th>
                <th className="px-3 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                  Requirement</th>
                <th className="px-3 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                  Gap Type</th>
                <th className="px-3 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                  Category</th>
                <th className="px-3 py-3 text-center text-xs font-semibold text-gray-600 uppercase">
                  Severity</th>
                <th className="px-3 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                  Recommended Owner</th>
                <th className="px-3 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                  Confidence</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((g) => (
                <tr key={g.id} className="hover:bg-gray-50">
                  <td className="px-3 py-3 font-mono text-xs text-gray-500">
                    {g.number}
                  </td>
                  <td className="px-3 py-3 text-gray-800 max-w-xs truncate" title={g.requirement}>
                    {g.requirement}
                  </td>
                  <td className="px-3 py-3">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border ${
                        GAP_TYPE_COLORS[g.gap_type]
                      }`}
                    >
                      {g.confirmed_gap ? '● ' : '○ '}
                      {GAP_TYPE_LABELS[g.gap_type] || g.gap_type}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-gray-600 capitalize whitespace-nowrap">
                    {g.category || '—'}
                  </td>
                  <td className="px-3 py-3 text-center">
                    <span
                      className={`text-xs font-medium ${
                        g.severity === 'High'
                          ? 'text-red-700'
                          : g.severity === 'Medium'
                          ? 'text-amber-700'
                          : 'text-blue-700'
                      }`}
                    >
                      {g.severity}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-gray-700">
                    <span className="flex items-center gap-1">
                      <Users size={12} className="text-gray-400 flex-shrink-0" />
                      {OWNER_LABELS[g.recommended_owner] || g.recommended_owner}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-gray-600">
                    {(g.confidence * 100).toFixed(0)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Guidance */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <h4 className="text-sm font-semibold text-gray-800 mb-2 flex items-center gap-2">
          <ArrowRight size={14} className="text-gray-500 flex-shrink-0" />
          How to read the analysis
        </h4>
        <ul className="text-sm text-gray-700 space-y-1 list-disc pl-5">
          <li>
            <strong>Confirmed product gap (●):</strong> the capability is not
            supported or confidence is very low — recommend Product Management
            input.
          </li>
          <li>
            <strong>Knowledge gap (○):</strong> the answer exists but evidence is
            stale or confidence is moderate — recommend Engineering or Solution
            Architecture review.
          </li>
          <li>
            <strong>Severity "High":</strong> mandatory requirement without an
            approved answer, or confidence below 45%.
          </li>
        </ul>
      </div>
    </div>
  );
}
