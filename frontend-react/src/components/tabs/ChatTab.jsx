import React, { useState, useEffect, useRef, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import { Send, Upload, Search, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react';
import { getMessages, sendChat, uploadRFP, analyzeRFP } from '../../api.js';

const QUICK_CHIPS = [
  { label: '📋 List All Questions', text: 'List all RFP questions with their current status' },
  { label: '🚩 Flagged to Pricing', text: 'Show all questions flagged to pricing owner' },
  { label: '🔍 Search KB: Murabaha', text: 'Search knowledge base for Murabaha related content' },
  { label: '📊 RFP Status Summary', text: 'Give me a complete RFP status summary' },
];

function formatTime(ts) {
  if (!ts) return '';
  try {
    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

export default function ChatTab({ sessionId }) {
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [sending, setSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadResult, setUploadResult] = useState(null);
  const [analyzeResult, setAnalyzeResult] = useState(null);
  const [uploadExpanded, setUploadExpanded] = useState(true);
  const [dragOver, setDragOver] = useState(false);

  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const textareaRef = useRef(null);

  const fetchMessages = useCallback(async () => {
    const data = await getMessages(sessionId);
    setMessages(Array.isArray(data) ? data : []);
  }, [sessionId]);

  useEffect(() => {
    fetchMessages();
  }, [fetchMessages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (text) => {
    const content = (text || inputText).trim();
    if (!content || sending) return;

    // Optimistically add user message
    const userMsg = {
      role: 'user',
      content,
      created_at: new Date().toISOString(),
      _optimistic: true,
    };
    setMessages(prev => [...prev, userMsg]);
    setInputText('');
    setSending(true);

    await sendChat(sessionId, content);
    await fetchMessages();
    setSending(false);
  };

  const handleChip = (chip) => {
    handleSend(chip.text);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) setSelectedFile(file);
  };

  const handleFileChange = (e) => {
    setSelectedFile(e.target.files[0] || null);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    setUploadResult(null);
    const result = await uploadRFP(sessionId, selectedFile);
    setUploadResult(result);
    setUploading(false);
  };

  const handleAnalyze = async () => {
    setAnalyzing(true);
    setAnalyzeResult(null);
    const result = await analyzeRFP(sessionId);
    setAnalyzeResult(result);
    await fetchMessages();
    setAnalyzing(false);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Upload RFP Card */}
      <div className="bg-white border border-gray-200 rounded-xl mb-4 shadow-sm flex-shrink-0">
        <button
          className="w-full flex items-center justify-between px-4 py-3 text-sm font-semibold text-gray-700 hover:text-gray-900"
          onClick={() => setUploadExpanded(v => !v)}
        >
          <span className="flex items-center gap-2">
            <Upload size={16} className="text-indigo-500" />
            Upload RFP Document
          </span>
          {uploadExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>

        {uploadExpanded && (
          <div className="px-4 pb-4 space-y-3 border-t border-gray-100">
            {/* Drop zone */}
            <div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleFileDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`mt-3 border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
                dragOver
                  ? 'border-blue-400 bg-blue-50'
                  : selectedFile
                  ? 'border-green-400 bg-green-50'
                  : 'border-gray-300 bg-gray-50 hover:border-gray-400'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx"
                className="hidden"
                onChange={handleFileChange}
              />
              {selectedFile ? (
                <div>
                  <p className="text-sm font-medium text-green-700">📄 {selectedFile.name}</p>
                  <p className="text-xs text-gray-400 mt-1">
                    {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
              ) : (
                <div>
                  <p className="text-sm text-gray-500">
                    Drag & drop PDF or DOCX here
                  </p>
                  <p className="text-xs text-gray-400 mt-1">or click to browse (max 50MB)</p>
                </div>
              )}
            </div>

            {/* Buttons */}
            <div className="flex gap-2">
              <button
                onClick={handleUpload}
                disabled={!selectedFile || uploading}
                className="flex-1 flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium py-2 px-4 rounded-lg transition-colors"
              >
                {uploading ? (
                  <RefreshCw size={14} className="animate-spin" />
                ) : (
                  <Upload size={14} />
                )}
                {uploading ? 'Uploading...' : 'Upload & Save'}
              </button>

              <button
                onClick={handleAnalyze}
                disabled={analyzing}
                className="flex-1 flex items-center justify-center gap-2 bg-orange-500 hover:bg-orange-600 disabled:opacity-50 text-white text-sm font-medium py-2 px-4 rounded-lg transition-colors"
              >
                {analyzing ? (
                  <RefreshCw size={14} className="animate-spin" />
                ) : (
                  <Search size={14} />
                )}
                {analyzing ? 'Analyzing… (30-60s)' : '🔍 Analyze RFP'}
              </button>
            </div>

            {/* Status messages */}
            {uploadResult && (
              <div className="text-xs text-green-700 bg-green-50 border border-green-200 rounded-lg px-3 py-2">
                ✅ Uploaded: {uploadResult.filename || 'file saved'}
              </div>
            )}
            {analyzeResult && (
              <div className="text-xs text-blue-700 bg-blue-50 border border-blue-200 rounded-lg px-3 py-2">
                ✅ {analyzeResult.message || 'Analysis complete'}
              </div>
            )}
            {analyzing && (
              <div className="text-xs text-orange-700 bg-orange-50 border border-orange-200 rounded-lg px-3 py-2 flex items-center gap-2">
                <RefreshCw size={12} className="animate-spin" />
                Agent is analyzing the RFP… this can take 30–60 seconds, please wait.
              </div>
            )}
          </div>
        )}
      </div>

      {/* Chat history */}
      <div className="flex-1 overflow-y-auto bg-white border border-gray-200 rounded-xl shadow-sm p-4 space-y-4 mb-4">
        {messages.length === 0 && !sending && (
          <div className="h-full flex items-center justify-center">
            <p className="text-gray-400 text-sm italic">
              No messages yet. Use the input below or a quick command to start.
            </p>
          </div>
        )}

        {messages.map((msg, i) => {
          const isUser = msg.role === 'user';
          return (
            <div key={msg.id || i} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
                <div
                  className={`px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
                    isUser
                      ? 'bg-blue-600 text-white rounded-br-sm'
                      : 'bg-gray-100 text-gray-800 rounded-bl-sm'
                  }`}
                >
                  {isUser ? (
                    <span>{msg.content}</span>
                  ) : (
                    <div className="prose">
                      <ReactMarkdown>{msg.content || ''}</ReactMarkdown>
                    </div>
                  )}
                </div>
                <span className="text-xs text-gray-400 mt-1 px-1">
                  {formatTime(msg.created_at)}
                </span>
              </div>
            </div>
          );
        })}

        {sending && (
          <div className="flex justify-start">
            <div className="bg-gray-100 text-gray-500 px-4 py-2.5 rounded-2xl rounded-bl-sm text-sm flex items-center gap-2">
              <RefreshCw size={13} className="animate-spin" />
              Agent thinking…
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick chip buttons */}
      <div className="flex flex-wrap gap-2 mb-3 flex-shrink-0">
        {QUICK_CHIPS.map((chip) => (
          <button
            key={chip.label}
            onClick={() => handleChip(chip)}
            disabled={sending}
            className="text-xs bg-white border border-gray-300 text-gray-600 hover:bg-gray-50 hover:border-gray-400 disabled:opacity-50 px-3 py-1.5 rounded-full transition-colors"
          >
            {chip.label}
          </button>
        ))}
      </div>

      {/* Input area */}
      <div className="flex-shrink-0 bg-white border border-gray-200 rounded-xl shadow-sm p-3 flex gap-3 items-end">
        <textarea
          ref={textareaRef}
          value={inputText}
          onChange={e => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message… (Enter to send, Shift+Enter for newline)"
          rows={2}
          className="flex-1 resize-none text-sm text-gray-800 placeholder-gray-400 focus:outline-none bg-transparent"
        />
        <button
          onClick={() => handleSend()}
          disabled={!inputText.trim() || sending}
          className="flex-shrink-0 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white p-2.5 rounded-xl transition-colors"
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  );
}
