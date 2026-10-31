import React, { useState, useCallback } from 'react';
import {
  Download,
  RefreshCw,
  FileText,
  FileSpreadsheet,
  Clock,
} from 'lucide-react';
import {
  triggerExport,
  downloadExportDocx,
  downloadExportXlsx,
} from '../../api.js';

export default function ExportTab({ sessionId }) {
  const [pkg, setPkg] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [downloadingDocx, setDownloadingDocx] = useState(false);
  const [downloadingXlsx, setDownloadingXlsx] = useState(false);
  const [error, setError] = useState(null);
  const [lastGenerated, setLastGenerated] = useState(null);

  const handleGenerate = useCallback(async () => {
    if (!sessionId) return;
    setGenerating(true);
    setError(null);
    try {
      const data = await triggerExport(sessionId);
      setPkg(data);
      setLastGenerated(new Date());
    } catch (e) {
      setError(e.message);
    } finally {
      setGenerating(false);
    }
  }, [sessionId]);

  const handleDownloadDocx = () =>
    downloadExportDocx(sessionId, pkg?.docx_filename);
  const handleDownloadXlsx = () =>
    downloadExportXlsx(sessionId, pkg?.xlsx_filename);

  if (!sessionId) return null;

  return (
    <div className="space-y-4">
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-5">
        <div className="flex items-center gap-2 mb-1">
          <Download size={18} className="text-indigo-600" />
          <h3 className="text-lg font-bold">Export Response Package</h3>
        </div>
        <p className="text-sm text-gray-600">
          Generate the formal DOCX proposal and the Section 7 XLSX compliance
          matrix for this session.
        </p>
        {error && (
          <div className="mt-3 rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-800">
            {error}
          </div>
        )}
      </div>

      <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-5">
        <div className="flex items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-2">
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium py-2 px-4 rounded-lg transition-colors"
            >
              {generating ? (
                <RefreshCw size={14} className="animate-spin" />
              ) : (
                <Download size={14} />
              )}
              {generating ? 'Generating…' : '📦 Generate Export Package'}
            </button>
            <p className="text-xs text-gray-500 ml-3">
              Generates both DOCX proposal and XLSX matrix (30–60s).
            </p>
          </div>
          {lastGenerated && (
            <span className="text-xs text-gray-500 flex items-center gap-1">
              <Clock size={12} />
              Generated {lastGenerated.toLocaleTimeString()}
            </span>
          )}
        </div>

        {pkg ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="border border-gray-200 rounded-lg p-4 flex flex-col">
              <div className="flex items-center gap-2 mb-2">
                <FileText size={16} className="text-blue-500" />
                <span className="font-medium text-gray-800">DOCX Proposal</span>
              </div>
              <p className="text-sm text-gray-600 truncate" title={pkg.docx_filename}>
                {pkg.docx_filename}
              </p>
              <p className="text-xs text-gray-400 mt-1">{pkg.session_name}</p>
              <button
                onClick={handleDownloadDocx}
                disabled={downloadingDocx}
                className="mt-auto flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium py-2 px-4 rounded-lg transition-colors"
              >
                {downloadingDocx ? (
                  <RefreshCw size={13} className="animate-spin" />
                ) : (
                  <Download size={13} />
                )}
                Download DOCX
              </button>
            </div>
            <div className="border border-gray-200 rounded-lg p-4 flex flex-col">
              <div className="flex items-center gap-2 mb-2">
                <FileSpreadsheet size={16} className="text-green-500" />
                <span className="font-medium text-gray-800">
                  XLSX Compliance Matrix
                </span>
              </div>
              <p className="text-sm text-gray-600 truncate" title={pkg.xlsx_filename}>
                {pkg.xlsx_filename}
              </p>
              <p className="text-xs text-gray-400 mt-1">
                Section 7 compliance matrix
              </p>
              <button
                onClick={handleDownloadXlsx}
                disabled={downloadingXlsx}
                className="mt-auto flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white text-sm font-medium py-2 px-4 rounded-lg transition-colors"
              >
                {downloadingXlsx ? (
                  <RefreshCw size={13} className="animate-spin" />
                ) : (
                  <Download size={13} />
                )}
                Download XLSX
              </button>
            </div>
          </div>
        ) : (
          <div className="text-center py-10 text-gray-400">
            <Clock size={32} className="mx-auto mb-3 opacity-50" />
            <p>No export package yet.</p>
            <p className="text-xs mt-1">
              Click "Generate Export Package" to create the DOCX and XLSX files.
            </p>
          </div>
        )}

        {pkg && (
          <div className="mt-4 grid grid-cols-2 gap-4">
            <div className="bg-gray-50 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-indigo-600">
                {pkg.total_questions ?? '—'}
              </p>
              <p className="text-xs text-gray-500">Total Questions</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-green-600">
                {pkg.approved_count ?? '—'}
              </p>
              <p className="text-xs text-gray-500">Approved Answers</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
