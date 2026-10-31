import React, { useState, useCallback } from 'react';
import {
  LayoutDashboard,
  MessageSquare,
  FileText,
  List,
  ShieldAlert,
  Download,
} from 'lucide-react';
import Sidebar from './components/Sidebar.jsx';
import ChatTab from './components/tabs/ChatTab.jsx';
import QuestionsTab from './components/tabs/QuestionsTab.jsx';
import FormatRulesTab from './components/tabs/FormatRulesTab.jsx';
import ClarificationsTab from './components/tabs/ClarificationsTab.jsx';
import ExportTab from './components/tabs/ExportTab.jsx';

const TABS = [
  { key: 'chat', label: 'Chat', Icon: MessageSquare },
  { key: 'questions', label: 'RFP Questions', Icon: List },
  { key: 'format', label: 'Format Rules', Icon: FileText },
  { key: 'clarifications', label: 'Clarifications', Icon: ShieldAlert },
  { key: 'export', label: 'Export', Icon: Download },
];

const TAB_LABELS = {
  chat: 'Chat',
  questions: 'RFP Questions',
  format: 'Format Rules',
  clarifications: 'Clarifications',
  export: 'Export Response',
};

export default function App() {
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [activeSessionName, setActiveSessionName] = useState(null);
  const [activeTab, setActiveTab] = useState('chat');

  const onSelectSession = useCallback((id, name) => {
    setActiveSessionId(id);
    setActiveSessionName(name);
    setActiveTab('chat');
  }, []);

  return (
    <div className="flex h-screen bg-gray-50 text-gray-900 overflow-hidden selection:bg-indigo-200">
      {/* Sidebar */}
      <Sidebar
        activeSessionId={activeSessionId}
        onSelectSession={onSelectSession}
      />

      {/* Main content */}
      <main className="flex-1 flex flex-col overflow-hidden ml-72 relative">
        {/* Top bar */}
        <div className="sticky top-0 z-20 flex items-center justify-between px-6 py-4 bg-white/80 backdrop-blur-md border-b border-gray-200 flex-shrink-0">
          <div className="flex items-center gap-4">
            {activeSessionId ? (
              <div>
                <h2 className="text-lg font-bold">{activeSessionName || 'Session'}</h2>
                <p className="text-xs text-gray-500">
                  Session #{activeSessionId} · {TAB_LABELS[activeTab] || activeTab}
                </p>
              </div>
            ) : (
              <div>
                <h2 className="text-lg font-bold">RFP Agent</h2>
                <p className="text-xs text-gray-500">
                  Azentio Islamic Banking · SAMPLE DATA ONLY
                </p>
              </div>
            )}
          </div>

          <div className="flex items-center gap-2">
            {TABS.map((tab) => {
              const isActive = activeTab === tab.key;
              return (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-colors border ${
                    isActive
                      ? 'bg-blue-600 text-white border-blue-600 shadow-sm shadow-blue-900/20'
                      : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900 border-transparent'
                  }`}
                >
                  <tab.Icon size={16} />
                  {tab.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Tab panels */}
        <div className="flex-1 overflow-y-auto bg-gray-50 p-6">
          {!activeSessionId ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="bg-gray-200 rounded-full p-4 mb-4">
                <LayoutDashboard size={48} className="text-gray-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-800 mb-2">
                No session selected
              </h3>
              <p className="text-gray-500 text-sm max-w-sm mb-6">
                Create or select a session from the sidebar to upload an RFP,
                chat with the agent, review questions, and export the response.
              </p>
            </div>
          ) : activeTab === 'chat' ? (
            <ChatTab sessionId={activeSessionId} />
          ) : activeTab === 'questions' ? (
            <QuestionsTab sessionId={activeSessionId} />
          ) : activeTab === 'format' ? (
            <FormatRulesTab sessionId={activeSessionId} />
          ) : activeTab === 'clarifications' ? (
            <ClarificationsTab sessionId={activeSessionId} />
          ) : (
            <ExportTab sessionId={activeSessionId} />
          )}
        </div>
      </main>
    </div>
  );
}
