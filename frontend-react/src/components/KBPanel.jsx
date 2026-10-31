import React, { useState, useEffect, useCallback } from 'react';
import { ChevronDown, ChevronUp, Database, RefreshCw, Lock, BookOpen } from 'lucide-react';
import { getKBDocuments, ingestKB } from '../api.js';

export default function KBPanel() {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [expandedDocs, setExpandedDocs] = useState(false);

  const fetchDocs = useCallback(async () => {
    setLoading(true);
    const data = await getKBDocuments();
    setDocs(Array.isArray(data) ? data : (data?.documents || []));
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchDocs();
  }, [fetchDocs]);

  const handleIngest = async () => {
    setIngesting(true);
    await ingestKB();
    await fetchDocs();
    setIngesting(false);
  };

  // Compute metrics
  const totalDocs = docs.length;
  const totalChunks = docs.reduce((sum, d) => sum + (d.chunk_count || 0), 0);

  const bySourceType = docs.reduce((acc, d) => {
    const key = d.source_type || 'unknown';
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="mt-4 border-t border-gray-700 pt-4">
      <button
        className="w-full flex items-center justify-between text-sm font-semibold text-gray-300 hover:text-white mb-2"
        onClick={() => setExpanded(v => !v)}
      >
        <span className="flex items-center gap-1.5">
          <Database size={14} />
          Knowledge Base
        </span>
        {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>

      {expanded && (
        <div className="space-y-2">
          {/* Metrics */}
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-gray-800 rounded-lg p-2 text-center">
              <p className="text-lg font-bold text-white">{totalDocs}</p>
              <p className="text-xs text-gray-400">Documents</p>
            </div>
            <div className="bg-gray-800 rounded-lg p-2 text-center">
              <p className="text-lg font-bold text-white">{totalChunks}</p>
              <p className="text-xs text-gray-400">Chunks</p>
            </div>
          </div>

          {/* Source type breakdown */}
          {Object.keys(bySourceType).length > 0 && (
            <div className="bg-gray-800 rounded-lg p-2">
              <p className="text-xs text-gray-400 mb-1.5 font-medium">By Source Type</p>
              {Object.entries(bySourceType).map(([type, count]) => (
                <div key={type} className="flex justify-between items-center text-xs py-0.5">
                  <span className="text-gray-300 capitalize">{type}</span>
                  <span className="text-gray-400">{count}</span>
                </div>
              ))}
            </div>
          )}

          {/* Document list toggle */}
          <button
            className="w-full text-left text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
            onClick={() => setExpandedDocs(v => !v)}
          >
            {expandedDocs ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            {expandedDocs ? 'Hide' : 'Show'} documents ({totalDocs})
          </button>

          {expandedDocs && (
            <div className="space-y-1 max-h-48 overflow-y-auto pr-1">
              {loading && (
                <p className="text-xs text-gray-400 text-center py-2">Loading...</p>
              )}
              {!loading && docs.length === 0 && (
                <p className="text-xs text-gray-400 text-center py-2">No documents indexed.</p>
              )}
              {docs.map((doc, i) => (
                <div key={doc.id || i} className="bg-gray-800 rounded p-2 text-xs">
                  <div className="flex items-center gap-1.5">
                    {doc.redacted ? (
                      <Lock size={11} className="text-red-400 flex-shrink-0" />
                    ) : (
                      <BookOpen size={11} className="text-green-400 flex-shrink-0" />
                    )}
                    <span className="text-gray-200 font-medium truncate flex-1" title={doc.name || doc.filename}>
                      {doc.name || doc.filename || 'Unnamed'}
                    </span>
                  </div>
                  <div className="flex justify-between mt-0.5 text-gray-400">
                    <span className="capitalize">{doc.source_type || '—'}</span>
                    <span>{doc.chunk_count ?? '?'} chunks</span>
                  </div>
                  {doc.version && (
                    <span className="text-gray-500">v{doc.version}</span>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Ingest button */}
          <button
            onClick={handleIngest}
            disabled={ingesting}
            className="w-full flex items-center justify-center gap-1.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-medium py-1.5 px-3 rounded-lg transition-colors"
          >
            <RefreshCw size={13} className={ingesting ? 'animate-spin' : ''} />
            {ingesting ? 'Ingesting...' : '🔄 Ingest / Refresh KB'}
          </button>
        </div>
      )}
    </div>
  );
}
