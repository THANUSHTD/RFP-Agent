import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  RefreshCw,
  ShieldAlert,
} from 'lucide-react';
import { getValidation, regenerateValidation } from '../../api.js';

const ISSUE_LABELS = {
  unsupported_claim: 'Unsupported Claim',
  outdated_info: 'Outdated Information',
  contradiction: 'Contradiction',
  missing_mandatory: 'Missing Mandatory Response',
  low_confidence: 'Not Yet Approved',
};

export default function ResponseValidationTab({ sessionId }) {
  const [validation, setValidation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [regenerating, setRegenerating] = useState(false);

  const fetchValidation = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    try {
      const data = await getValidation(sessionId);
      setValidation(data);
    } catch (e) {
      console.error('Validation fetch error:', e);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchValidation();
  }, [fetchValidation]);

  const handleRegenerate = async () => {
    setRegenerating(true);
    try {
      const data = await regenerateValidation(sessionId);
      if (data) setValidation(data);
    } catch (e) {
      console.error('regenerateValidation error:', e);
    } finally {
      setRegenerating(false);
    }
  };

  const issues = validation?.issues ?? [];
  const highCount = issues.filter((i) => i.severity === 'High').length;
  const mediumCount = issues.filter((i) => i.severity === 'Medium').length;

  function issueColor(issueType) {
    switch (issueType) {
      case 'unsupported_claim':
        return 'text-red-700 bg-red-100 border-red-200';
      case 'outdated_info':
        return 'text-amber-700 bg-amber-100 border-amber-200';
      case 'contradiction':
        return 'text-indigo-700 bg-indigo-100 border-indigo-200';
      case 'missing_mandatory':
        return 'text-red-700 bg-red-100 border-red-200';
      case 'low_confidence':
        return 'text-orange-700 bg-orange-50 border-orange-200';
      default:
        return 'text-gray-700 bg-gray-100 border-gray-200';
    }
  }

  if (loading)
    return (
      <div className="py-12 flex flex-col items-center justify-center text-gray-400">
        <RefreshCw size={24} className="animate-spin mb-2" />
        <p>Running response validation…</p>
      </div>
    );

  if (!validation)
    return (
      <div className="py-12 text-center text-gray-400">
        <p>Unable to load validation results.</p>
      </div>
    );

  return (
    <div className="space-y-4">
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-5">
        <div className="flex items-center gap-2 mb-2">
          <ShieldAlert size={20} className="text-indigo-600" />
          <h3 className="text-lg font-bold">Intelligent Response Validation</h3>
        </div>
        <p className="text-sm text-gray-600">
          Cross-checks drafted answers against source documentation. Flags
          unsupported claims, outdated information, contradictions across
          requirements, and missing mandatory responses before submission.
        </p>
        <div className="mt-3 flex items-center gap-3">
          <button
            onClick={handleRegenerate}
            disabled={regenerating}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium py-1.5 px-3 rounded-lg transition-colors"
          >
            <RefreshCw size={14} className={regenerating ? 'animate-spin' : ''} />
            {regenerating ? 'Regenerating…' : '🔄 Re-run Validation'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white border border-gray-200 rounded-xl p-4 text-center shadow-sm">
          <p className="text-2xl font-bold text-red-600">{highCount}</p>
          <p className="text-xs text-gray-500 mt-1">High Severity</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-4 text-center shadow-sm">
          <p className="text-2xl font-bold text-amber-600">{mediumCount}</p>
          <p className="text-xs text-gray-500 mt-1">Medium Severity</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-4 text-center shadow-sm">
          <p className="text-2xl font-bold text-gray-600">{issues.length}</p>
          <p className="text-xs text-gray-500 mt-1">Total Issues</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-4 text-center shadow-sm">
          <p className="text-2xl font-bold text-green-600">
            {validation.total - issues.filter((i) => i.issue_type === 'missing_mandatory').length}
          </p>
          <p className="text-xs text-gray-500 mt-1">Requirements Reviewed</p>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
        {issues.length === 0 ? (
          <div className="p-12 text-center text-gray-400">
            <p>No validation issues detected.</p>
            <p className="text-xs mt-1 text-gray-400">
              All drafted answers appear consistent and complete.
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
                  Issue</th>
                <th className="px-3 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                  Detail</th>
                <th className="px-3 py-3 text-center text-xs font-semibold text-gray-600 uppercase">
                  Severity</th>
              </tr>
            </thead>
            <tbody>
              {issues.map((issue) => (
                <tr key={issue.id} className="hover:bg-gray-50">
                  <td className="px-3 py-3 font-mono text-xs text-gray-500">
                    {issue.number}
                  </td>
                  <td className="px-3 py-3 text-gray-800 max-w-xs truncate" title={issue.requirement}>
                    {issue.requirement}
                  </td>
                  <td className="px-3 py-3">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border ${issueColor(issue.issue_type)}`}
                    >
                      {ISSUE_LABELS[issue.issue_type]}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-gray-700 max-w-xs">
                    <span className="break-words truncate" title={issue.detail}>
                      {issue.detail}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-center">
                    <span
                      className={`text-xs font-medium ${
                        issue.severity === 'High'
                          ? 'text-red-700'
                          : issue.severity === 'Medium'
                          ? 'text-amber-700'
                          : 'text-blue-700'
                      }`}
                    >
                      {issue.severity}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <p className="text-sm text-gray-600">
          Validation is derived from answer confidence, staleness warnings, and
          cross-requirement consistency. Resolve high-severity issues before
          proceeding to export.
        </p>
      </div>
    </div>
  );
}
