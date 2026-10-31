import React, { useState } from 'react';
import { ChevronDown, ChevronRight, FileText } from 'lucide-react';

/**
 * Displays a single citation with chunk_id, document name, source_type, and snippet.
 */
export function CitationCard({ citation }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden text-sm">
      <button
        className="w-full flex items-center gap-2 px-3 py-2 bg-gray-50 hover:bg-gray-100 text-left"
        onClick={() => setExpanded(v => !v)}
      >
        <FileText size={14} className="text-indigo-500 flex-shrink-0" />
        <span className="flex-1 font-medium text-gray-700 truncate">
          {citation.document_name || citation.chunk_id || 'Citation'}
        </span>
        {citation.source_type && (
          <span className="text-xs text-gray-500 bg-gray-200 px-1.5 py-0.5 rounded">
            {citation.source_type}
          </span>
        )}
        {expanded ? (
          <ChevronDown size={14} className="text-gray-400 flex-shrink-0" />
        ) : (
          <ChevronRight size={14} className="text-gray-400 flex-shrink-0" />
        )}
      </button>

      {expanded && (
        <div className="px-3 py-2 bg-white border-t border-gray-100">
          {citation.chunk_id && (
            <p className="text-xs text-gray-400 mb-1">
              Chunk: <code className="bg-gray-100 px-1 rounded">{citation.chunk_id}</code>
            </p>
          )}
          {citation.snippet && (
            <p className="text-gray-600 text-xs italic leading-relaxed">
              "{citation.snippet}"
            </p>
          )}
          {!citation.snippet && (
            <p className="text-gray-400 text-xs">No snippet available.</p>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Renders a list of citation cards.
 */
export default function CitationList({ citations }) {
  if (!citations || citations.length === 0) {
    return (
      <p className="text-sm text-gray-400 italic">No citations available.</p>
    );
  }

  return (
    <div className="space-y-2">
      {citations.map((c, i) => (
        <CitationCard key={c.chunk_id || i} citation={c} />
      ))}
    </div>
  );
}
