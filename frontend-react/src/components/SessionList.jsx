import React from 'react';
import { MessageSquare } from 'lucide-react';

export default function SessionList({ sessions, activeSessionId, onSelectSession }) {
  if (!sessions || sessions.length === 0) {
    return (
      <p className="text-xs text-gray-500 italic px-2 py-2">
        No sessions yet. Create one above.
      </p>
    );
  }

  return (
    <div className="space-y-1 max-h-60 overflow-y-auto pr-1">
      {sessions.map((session) => {
        const isActive = session.id === activeSessionId;
        return (
          <button
            key={session.id}
            onClick={() => onSelectSession(session.id, session.name)}
            className={`w-full text-left flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm transition-colors ${
              isActive
                ? 'bg-blue-600 text-white'
                : 'text-gray-300 hover:bg-gray-700 hover:text-white'
            }`}
          >
            <MessageSquare size={14} className="flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="font-medium truncate">{session.name || 'Unnamed Session'}</p>
              <p className={`text-xs truncate ${isActive ? 'text-blue-200' : 'text-gray-500'}`}>
                {session.id}
              </p>
            </div>
          </button>
        );
      })}
    </div>
  );
}
