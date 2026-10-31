import React, { useState, useEffect, useCallback } from 'react';
import {
  ClipboardList,
  RefreshCw,
} from 'lucide-react';
import {
  getComplianceMatrix,
  putResponseCode,
} from '../../api.js';
import ResponseCodeBadge from '../ui/ResponseCodeBadge.jsx';

const CODE_INFO = {
  S: { label: 'Standard', color: 'text-green-700', bg: 'bg-green-100', border: 'border-green-200' },
  C: { label: 'Configuration', color: 'text-blue-700', bg: 'bg-blue-100', border: 'border-blue-200' },
  D: { label: 'Development', color: 'text-amber-700', bg: 'bg-amber-100', border: 'border-amber-200' },
  T: { label: 'Third-party', color: 'text-indigo-700', bg: 'bg-indigo-100', border: 'border-indigo-200' },
  N: { label: 'Not available', color: 'text-red-700', bg: 'bg-red-100', border: 'border-red-200' },
};

const CODE_LABELS = {
  S: 'Standard capability',
  C: 'Configuration required',
  D: 'Development required',
  T: 'Third-party dependency',
  N: 'Not available',
};

export default function ComplianceMatrixTab({ sessionId }) {
  const [matrix, setMatrix] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState({});
  const [savedCodes, setSavedCodes] = useState({});

  const fetchMatrix = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    try {
      const data = await getComplianceMatrix(sessionId);
      setMatrix(data);
      if (data) {
        setSavedCodes(
          data.rows.reduce((acc, r) => ({ ...acc, [r.question_id]: r.code }), {})
        );
      }
    } catch (e) {
      console.error('ComplianceMatrix fetch error:', e);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchMatrix();
  }, [fetchMatrix]);

  const handleCodeChange = async (questionId, code) => {
    // Optimistically update UI
    setMatrix((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        rows: prev.rows.map((r) =>
          r.question_id === questionId ? { ...r, code } : r
        ),
      };
    });
    setSaving((p) => ({ ...p, [questionId]: true }));

    // Determine if code requires an explanation
    const requiresNote = ['C', 'D', 'T', 'N'].includes(code);
    const row = matrix?.rows.find((r) => r.question_id === questionId);
    const explanation = row?.explanation || '';

    const updated = await putResponseCode(sessionId, questionId, {
      code,
      explanation,
      validated_by_se: false,
    });

    if (updated) {
      setSavedCodes((prev) => ({ ...prev, [questionId]: code }));
      // Refresh matrix to reflect any server-side changes
      await fetchMatrix();
    }
    setSaving((p) => { const { [questionId]: _, ...rest } = p; return rest; });
  };

  if (loading)
    return (
      <div className="py-12 flex flex-col items-center justify-center text-gray-400">
        <RefreshCw size={24} className="animate-spin mb-2" />
        <p>Loading compliance matrix…</p>
      </div>
    );

  if (!matrix)
    return (
      <div className="py-12 text-center text-gray-400">
        <p>Unable to load compliance matrix.</p>
      </div>
    );

  const { total, coded, flagged, not_available, rows } = matrix;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-5">
        <div className="flex items-center gap-2 mb-2">
          <ClipboardList size={20} className="text-indigo-600" />
          <h3 className="text-lg font-bold">Intelligent Compliance Matrix</h3>
        </div>
        <p className="text-sm text-gray-600">
          Requirement-by-requirement compliance classification. Assign a response
          code (S/C/D/T/N) to each capability. Codes C, D, T and N require a
          supporting explanation, estimate, or attachment.
        </p>
        <div className="mt-3 flex flex-wrap gap-3 text-xs">
          {Object.entries(CODE_LABELS).map(([code, label]) => (
            <span
              key={code}
              className={`inline-flex items-center gap-1 px-2 py-1 rounded border ${
                CODE_INFO[code].bg
              } ${CODE_INFO[code].color} ${CODE_INFO[code].border}`}
            >
              <span className="font-bold">{code}</span> {label}
            </span>
          ))}
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white border border-gray-200 rounded-xl p-4 text-center shadow-sm">
          <p className="text-2xl font-bold text-indigo-600">{total}</p>
          <p className="text-xs text-gray-500 mt-1">Requirements</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-4 text-center shadow-sm">
          <p className="text-2xl font-bold text-blue-600">{coded}</p>
          <p className="text-xs text-gray-500 mt-1">Codes Assigned</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-4 text-center shadow-sm">
          <p className="text-2xl font-bold text-amber-600">{flagged}</p>
          <p className="text-xs text-gray-500 mt-1">Needs Attention</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-4 text-center shadow-sm">
          <p className="text-2xl font-bold text-red-600">{not_available}</p>
          <p className="text-xs text-gray-500 mt-1">Not Available</p>
        </div>
      </div>

      {/* Matrix table */}
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 sticky top-0 z-10">
              <tr>
                <th className="px-3 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                  Req #</th>
                <th className="px-3 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                  Requirement</th>
                <th className="px-3 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                  Category</th>
                <th className="px-3 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                  Mandatory</th>
                <th className="px-3 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                  Response Code</th>
                <th className="px-3 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                  Confidence</th>
                <th className="px-3 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                  Compliance</th>
                <th className="px-3 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                  Explanation / Estimate</th>
                <th className="px-3 py-3 text-right text-xs font-semibold text-gray-600 uppercase">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.map((row) => {
                const requiresNote = row.requires_explanation && !row.explanation;
                const isSaving = saving[row.question_id];
                const isSaved = savedCodes[row.question_id] === row.code && !!row.code;
                return (
                  <tr key={row.question_id} className="hover:bg-gray-50 group">
                    <td className="px-3 py-3 font-mono text-xs text-gray-500">
                      {row.number || row.question_id}
                    </td>
                    <td className="px-3 py-3 text-gray-800 max-w-xs truncate" title={row.text}>
                      {row.text}
                    </td>
                    <td className="px-3 py-3 text-gray-600 capitalize whitespace-nowrap">
                      {row.category || 'other'}
                    </td>
                    <td className="px-3 py-3 text-center">
                      {row.mandatory ? (
                        <span className="text-xs font-medium text-red-600">Yes</span>
                      ) : (
                        <span className="text-xs text-gray-400">—</span>
                      )}
                    </td>
                    <td className="px-3 py-3">
                      <ResponseCodeBadge
                        code={row.code}
                        editable
                        onChange={(c) => handleCodeChange(row.question_id, c)}
                      />
                      {requiresNote && (
                        <span className="ml-2 text-[10px] font-bold text-red-500">
                          ⚠ note required
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-3 text-gray-600">
                      {(row.confidence * 100).toFixed(0)}%
                    </td>
                    <td className="px-3 py-3">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border ${row.complianceClass} bg-gray-50`}
                      >
                        {row.compliance}
                      </span>
                    </td>
                    <td className="px-3 py-3">
                      {requiresNote ? (
                        <span className="text-xs text-gray-400 italic">Add explanation</span>
                      ) : (
                        <span className="text-xs text-gray-400 italic">Not required</span>
                      )}
                    </td>
                    <td className="px-3 py-3 text-right">
                      {isSaving ? (
                        <RefreshCw size={12} className="animate-spin" />
                      ) : isSaved ? (
                        <span className="text-xs text-green-500">✓ Saved</span>
                      ) : (
                        <span className="text-xs text-gray-400">Set code</span>
                      )}
                    </td>
                  </tr>
                );
              })}
              {rows.length === 0 && (
                <tr>
                  <td colSpan="9" className="px-3 py-12 text-center text-gray-400">
                    No requirements extracted yet. Upload and analyze an RFP first.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Legend / guidance */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
        <h4 className="text-sm font-semibold text-amber-800 mb-2 flex items-center gap-2">
          How to use response codes
        </h4>
        <ul className="text-sm text-amber-700 space-y-1 list-disc pl-5">
          <li>
            <strong>S (Standard):</strong> capability available out of the box.
          </li>
          <li>
            <strong>C (Configuration):</strong> requires product configuration —
            explanation required.
          </li>
          <li>
            <strong>D (Development):</strong> requires custom development —
            explanation and estimate required.
          </li>
          <li>
            <strong>T (Third-party):</strong> relies on a third-party component
            — explanation and attachment required.
          </li>
          <li>
            <strong>N (Not available):</strong> capability not offered —
            explanation required.
          </li>
        </ul>
      </div>
    </div>
  );
}
