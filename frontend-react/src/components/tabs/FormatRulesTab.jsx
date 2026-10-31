import React, { useState, useEffect, useCallback } from 'react';
import {
  Save,
  FileText,
  RefreshCw,
  Check,
  AlertTriangle,
  Code2,
} from 'lucide-react';
import { getFormatRules, putFormatRules } from '../../api.js';

export default function FormatRulesTab({ sessionId }) {
  const [rules, setRules] = useState(null);
  const [rulesText, setRulesText] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [lastSaved, setLastSaved] = useState(null);

  const parseRulesJson = (raw) => {
    if (!raw) return {};
    if (typeof raw === 'object') return raw;
    try {
      return JSON.parse(raw);
    } catch {
      return {};
    }
  };

  const fetchRules = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getFormatRules(sessionId);
      setRules(data);
      setRulesText(JSON.stringify(parseRulesJson(data?.rules_json), null, 2));
      setConfirmed(!!data?.confirmed_by_se);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchRules();
  }, [fetchRules]);

  const handleSave = async () => {
    let parsed;
    try {
      parsed = JSON.parse(rulesText || '{}');
    } catch {
      setError('Invalid JSON — please fix the editor before saving.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const updated = await putFormatRules(sessionId, parsed, true);
      setRules(updated);
      setConfirmed(true);
      setLastSaved(new Date());
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const rulesObj = parseRulesJson(rules?.rules_json);

  if (!sessionId) return null;

  return (
    <div className="space-y-4">
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-5">
        <div className="flex items-center gap-2 mb-1">
          <FileText size={18} className="text-indigo-600" />
          <h3 className="text-lg font-bold">Format Rules</h3>
        </div>
        <p className="text-sm text-gray-600">
          Extracted document formatting requirements (fonts, margins, sections,
          page size). Review, adjust if needed, and confirm as the Sales
          Engineer.
        </p>
        {error && (
          <div className="mt-3 rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-800">
            {error}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Editor */}
        <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-5 flex flex-col">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-semibold text-gray-700">Rules (JSON)</span>
            <button
              onClick={() =>
                setRulesText(
                  rules ? JSON.stringify(rulesObj, null, 2) : '{}'
                )
              }
              className="text-xs text-gray-500 hover:text-gray-700 underline"
            >
              Reset
            </button>
          </div>
          <textarea
            value={rulesText}
            onChange={(e) => setRulesText(e.target.value)}
            rows={14}
            className="flex-1 w-full font-mono text-sm text-gray-800 bg-gray-50 border border-gray-200 rounded-lg p-3 focus:outline-none focus:border-indigo-400 resize-none"
            spellCheck={false}
          />
          <div className="mt-3 flex items-center gap-3">
            <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-700 select-none">
              <input
                type="checkbox"
                checked={confirmed}
                onChange={(e) => setConfirmed(e.target.checked)}
                className="rounded text-indigo-600 focus:ring-indigo-500"
              />
              <span>Confirmed by Sales Engineer</span>
            </label>
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium py-2 px-4 rounded-lg transition-colors"
            >
              {saving ? (
                <RefreshCw size={14} className="animate-spin" />
              ) : (
                <Save size={14} />
              )}
              {saving ? 'Saving…' : '💾 Save Format Rules'}
            </button>
          </div>
          {lastSaved && (
            <p className="mt-2 text-xs text-gray-500 flex items-center gap-1">
              <Check size={12} className="text-green-500" />
              Saved {lastSaved.toLocaleTimeString()}
            </p>
          )}
        </div>

        {/* Preview */}
        <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-5 flex flex-col">
          <div className="flex items-center gap-2 mb-3">
            <Code2 size={16} className="text-gray-400" />
            <span className="text-sm font-semibold text-gray-700">Preview</span>
          </div>
          {loading ? (
            <div className="flex-1 flex items-center justify-center text-gray-400">
              <RefreshCw size={16} className="animate-spin" /> Loading…
            </div>
          ) : !rules || Object.keys(rulesObj).length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-gray-400">
              <p>No format rules extracted yet.</p>
              <p className="text-xs text-gray-400 mt-1">
                Upload and analyze an RFP first.
              </p>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto space-y-2">
              {Object.entries(rulesObj).map(([key, value]) => (
                <div key={key} className="border border-gray-100 rounded-lg p-3">
                  <div className="flex justify-between items-start mb-1">
                    <span className="text-xs font-medium text-indigo-700 truncate max-w-xs">
                      {key}
                    </span>
                    <span className="text-xs text-gray-400">
                      {Array.isArray(value) ? 'array' : typeof value}
                    </span>
                  </div>
                  <div className="text-sm text-gray-700 break-words">
                    {Array.isArray(value)
                      ? value.join(', ')
                      : String(value)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
