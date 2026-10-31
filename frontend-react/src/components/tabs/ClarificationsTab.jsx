import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, List, MessageSquare, AlertCircle } from 'lucide-react';
import { getClarifications } from '../../api.js';

function parseJsonField(val) {
  if (!val) return [];
  if (Array.isArray(val)) return val;
  try {
    return JSON.parse(val);
  } catch {
    return [];
  }
}

export default function ClarificationsTab({ sessionId }) {
  const [clarifications, setClarifications] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchClarifications = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getClarifications(sessionId);
      setClarifications(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchClarifications();
  }, [fetchClarifications]);

  if (!sessionId) return null;

  const openCount = clarifications.filter(
    (c) =>
      !(c.status || '').toLowerCase().includes('resolved') &&
      !(c.status || '').toLowerCase().includes('closed')
  ).length;

  return (
    <div className="space-y-4">
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-5">
        <div className="flex items-center gap-2 mb-1">
          <AlertCircle size={18} className="text-amber-600" />
          <h3 className="text-lg font-bold">Clarifications</h3>
        </div>
        <p className="text-sm text-gray-600">
          Items the agent could not answer confidently and needs the Sales
          Engineer or client to clarify.
        </p>
        <div className="mt-3 flex items-center gap-2">
          <span
            className={`text-xs font-semibold px-2 py-1 rounded-full ${
              openCount > 0
                ? 'bg-amber-100 text-amber-800'
                : 'bg-green-100 text-green-800'
            }`}
          >
            {openCount} open · {clarifications.length} total
          </span>
        </div>
        {error && (
          <div className="mt-3 rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-800">
            {error}
          </div>
        )}
      </div>

      <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="py-12 text-center text-gray-400 flex items-center justify-center gap-2">
            <RefreshCw size={16} className="animate-spin" /> Loading clarifications…
          </div>
        ) : clarifications.length === 0 ? (
          <div className="py-12 text-center text-gray-400">
            <MessageSquare size={32} className="mx-auto mb-3 text-gray-300" />
            <p>No clarifications.</p>
            <p className="text-xs text-gray-400 mt-1">
              All questions have been answered or none extracted yet.
            </p>
          </div>
        ) : (
          <table className="w-full text-sm divide-y divide-gray-100">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                  #
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                  Clarification
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                  Reason
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                  Linked Questions
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                  Created
                </th>
              </tr>
            </thead>
            <tbody>
              {clarifications.map((c, i) => {
                const linked = parseJsonField(c.linked_question_ids_json);
                const resolved =
                  (c.status || '').toLowerCase().includes('resolved') ||
                  (c.status || '').toLowerCase().includes('closed');
                return (
                  <tr key={c.id || i} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-500 font-mono text-xs">
                      {c.id}
                    </td>
                    <td className="px-4 py-3 text-gray-800">{c.text}</td>
                    <td className="px-4 py-3 text-gray-600">{c.reason}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${
                          resolved
                            ? 'bg-green-100 text-green-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}
                      >
                        {c.status || 'Open'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {linked.length > 0 ? linked.join(', ') : '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">
                      {c.created_at
                        ? new Date(c.created_at).toLocaleString()
                        : '—'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
