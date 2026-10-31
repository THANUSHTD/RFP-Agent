import React, { useState, useEffect, useCallback } from 'react';
import { ChevronDown, ChevronUp, Plus, X } from 'lucide-react';
import { getHealth, getSessions, createSession } from '../api.js';
import SessionList from './SessionList.jsx';
import KBPanel from './KBPanel.jsx';

export default function Sidebar({ activeSessionId, onSelectSession }) {
  const [health, setHealth] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [newSessionName, setNewSessionName] = useState('');
  const [creating, setCreating] = useState(false);
  const [showNewForm, setShowNewForm] = useState(false);

  const fetchHealth = useCallback(async () => {
    const data = await getHealth();
    setHealth(data);
  }, []);

  const fetchSessions = useCallback(async () => {
    const data = await getSessions();
    setSessions(Array.isArray(data) ? data : []);
  }, []);

  useEffect(() => {
    fetchHealth();
    fetchSessions();
    // Poll health every 30s
    const healthInterval = setInterval(fetchHealth, 30000);
    return () => clearInterval(healthInterval);
  }, [fetchHealth, fetchSessions]);

  const handleCreateSession = async (e) => {
    e.preventDefault();
    if (!newSessionName.trim()) return;
    setCreating(true);
    const session = await createSession(newSessionName.trim());
    if (session) {
      setNewSessionName('');
      setShowNewForm(false);
      await fetchSessions();
      onSelectSession(session.id, session.name);
    }
    setCreating(false);
  };

  const isHealthy = health !== null;

  // Extract model info from health
  const modelInfo = health
    ? [health.model, health.smart_model].filter(Boolean).join(' / ')
    : null;

  return (
    <div className="w-72 bg-gray-900 text-white h-screen fixed left-0 top-0 flex flex-col overflow-hidden z-10">
      {/* Header */}
      <div className="px-4 pt-5 pb-4 border-b border-gray-700 flex-shrink-0">
        <h1 className="text-lg font-bold tracking-tight">📋 RFP Agent</h1>
        <p className="text-xs text-gray-400 mt-0.5">
          Azentio Islamic Banking · SAMPLE DATA ONLY
        </p>

        {/* Health badge */}
        <div className="mt-3">
          {isHealthy ? (
            <div className="flex items-center gap-1.5 text-xs bg-green-900 border border-green-700 text-green-300 px-2.5 py-1.5 rounded-lg">
              <span className="w-2 h-2 rounded-full bg-green-400 flex-shrink-0" />
              <span className="font-medium">
                ✅ Backend connected
                {modelInfo && ` | ${modelInfo}`}
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-xs bg-red-900 border border-red-700 text-red-300 px-2.5 py-1.5 rounded-lg">
              <span className="w-2 h-2 rounded-full bg-red-400 flex-shrink-0" />
              <span className="font-medium">❌ Backend not reachable</span>
            </div>
          )}
        </div>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {/* New Session */}
        <div>
          <button
            onClick={() => setShowNewForm(v => !v)}
            className="w-full flex items-center justify-between text-sm font-semibold text-gray-300 hover:text-white mb-2"
          >
            <span className="flex items-center gap-1.5">
              <Plus size={14} />
              New Session
            </span>
            {showNewForm ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>

          {showNewForm && (
            <form onSubmit={handleCreateSession} className="space-y-2">
              <input
                type="text"
                value={newSessionName}
                onChange={e => setNewSessionName(e.target.value)}
                placeholder="Session name..."
                className="w-full bg-gray-800 border border-gray-600 text-white text-sm rounded-lg px-3 py-2 placeholder-gray-500 focus:outline-none focus:border-blue-500"
              />
              <div className="flex gap-2">
                <button
                  type="submit"
                  disabled={creating || !newSessionName.trim()}
                  className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium py-1.5 px-3 rounded-lg transition-colors"
                >
                  {creating ? 'Creating...' : 'Create Session'}
                </button>
                <button
                  type="button"
                  onClick={() => { setShowNewForm(false); setNewSessionName(''); }}
                  className="p-1.5 text-gray-400 hover:text-white rounded-lg hover:bg-gray-700"
                >
                  <X size={16} />
                </button>
              </div>
            </form>
          )}
        </div>

        {/* Sessions list */}
        <div>
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
            Sessions
          </p>
          <SessionList
            sessions={sessions}
            activeSessionId={activeSessionId}
            onSelectSession={onSelectSession}
          />
        </div>

        {/* KB Panel */}
        <KBPanel />
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-gray-700 flex-shrink-0">
        <p className="text-xs text-gray-500 text-center">
          ⚠️ SYNTHETIC / MOCK DATA ONLY
        </p>
      </div>
    </div>
  );
}
