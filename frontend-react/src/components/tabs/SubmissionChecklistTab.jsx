import React, { useState, useEffect, useCallback } from 'react';
import {
  ClipboardList,
  Check,
  AlertTriangle,
  RefreshCw,
  Calendar,
} from 'lucide-react';
import {
  getChecklist,
  putChecklistItem,
  regenerateChecklist,
} from '../../api.js';

export default function SubmissionChecklistTab({ sessionId }) {
  const [checklist, setChecklist] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState({});

  const fetchChecklist = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    try {
      const data = await getChecklist(sessionId);
      setChecklist(data);
    } catch (e) {
      console.error('Checklist fetch error:', e);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchChecklist();
  }, [fetchChecklist]);

  const handleRegenerate = async () => {
    try {
      const data = await regenerateChecklist(sessionId);
      if (data) setChecklist(data);
    } catch (e) {
      console.error('regenerateChecklist error:', e);
    }
  };

  const handleToggle = async (itemKey, currentStatus) => {
    const newStatus = currentStatus === 'done' ? 'pending' : 'done';
    setSaving((p) => ({ ...p, [itemKey]: true }));
    const updated = await putChecklistItem(sessionId, itemKey, {
      status: newStatus,
      done_by: 'Sales Engineer',
    });
    if (updated) {
      setChecklist((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          items: prev.items.map((i) =>
            i.item_key === itemKey
              ? { ...i, status: newStatus, done_by: updated.done_by, done_at: updated.done_at }
              : i
          ),
          done: prev.done + (newStatus === 'done' ? 1 : -1),
          pending: prev.pending + (newStatus === 'done' ? -1 : 1),
          percent: prev.total
            ? Math.round(
                ((prev.done + (newStatus === 'done' ? 1 : -1)) / prev.total) *
                  100
              )
            : 0,
        };
      });
    }
    setSaving((p) => { const { [itemKey]: _, ...rest } = p; return rest; });
  };

  if (loading)
    return (
      <div className="py-12 flex flex-col items-center justify-center text-gray-400">
        <RefreshCw size={24} className="animate-spin mb-2" />
        <p>Loading submission checklist…</p>
      </div>
    );

  if (!checklist)
    return (
      <div className="py-12 text-center text-gray-400">
        <p>Unable to load submission checklist.</p>
      </div>
    );

  const { total, done, pending, percent, items } = checklist;

  return (
    <div className="space-y-4">
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-5">
        <div className="flex items-center gap-2 mb-2 flex-wrap">
          <ClipboardList size={20} className="text-indigo-600" />
          <h3 className="text-lg font-bold">Submission Checklist</h3>
          <button
            onClick={handleRegenerate}
            className="ml-auto flex items-center gap-1.5 text-xs text-indigo-600 hover:text-indigo-800 underline"
          >
            <RefreshCw size={12} /> Regenerate
          </button>
        </div>
        <p className="text-sm text-gray-600">
          Track completion of customer-specific formatting and response
          requirements before final submission. Preserve section numbering and
          requirement references from the RFP.
        </p>
        <div className="mt-4 w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
          <div
            className="h-2.5 bg-indigo-600 rounded-full transition-all duration-500"
            style={{ width: `${percent}%` }}
          />
        </div>
        <div className="mt-2 flex justify-between text-xs text-gray-500">
          <span>{done} / {total} completed</span>
          <span>{percent}% complete</span>
        </div>
      </div>

      {/* Checklist */}
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
        <table className="w-full text-sm divide-y divide-gray-100">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                Item</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase">
                Status</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-800">{item.label}</td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={() => handleToggle(item.item_key, item.status)}
                    disabled={saving[item.id]}
                    className={`flex items-center gap-1.5 text-xs font-medium ${
                      item.status === 'done'
                        ? 'text-green-600'
                        : 'text-amber-600'
                    } disabled:opacity-50`}
                  >
                    {saving[item.id] ? (
                      <RefreshCw size={12} className="animate-spin" />
                    ) : item.status === 'done' ? (
                      <>
                        <Check size={14} />
                        <span>Done</span>
                      </>
                    ) : (
                      <>
                        <AlertTriangle size={14} />
                        <span>Pending</span>
                      </>
                    )}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Format rules editor */}
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-5">
        <div className="flex items-center gap-2 mb-3">
          <Calendar size={18} className="text-indigo-600" />
          <h4 className="text-base font-bold">Customer Format Rules</h4>
        </div>
        <p className="text-sm text-gray-600 mb-3">
          Interpret RFP instructions regarding document structure, response codes,
          answer lengths, annexures, and mandatory fields.
        </p>
        <p className="text-xs text-gray-500 mb-3">
          Format rules are managed on the <strong>Format Rules</strong> tab and
          reflected here once confirmed by the Sales Engineer.
        </p>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-800">
        <p className="font-semibold mb-1 flex items-center gap-2">
          <Calendar size={14} className="flex-shrink-0" />
          Customer-specific formatting notes
        </p>
        <ul className="list-disc pl-5 space-y-1">
          <li>Preserve section numbering and requirement references from the RFP.</li>
          <li>Apply customer-defined response codes where provided.</li>
          <li>Observe answer length limits and mandatory fields.</li>
          <li>Include all required annexures in the final submission.</li>
        </ul>
      </div>
    </div>
  );
}
