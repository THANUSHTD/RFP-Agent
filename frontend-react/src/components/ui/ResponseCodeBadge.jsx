import React from 'react';

/**
 * Response code badge for the compliance matrix.
 * Codes: S Standard | C Configuration | D Development | T Third-party | N Not available
 */
const CODE_INFO = {
  S: { label: 'Standard', color: 'text-green-700', bg: 'bg-green-100', border: 'border-green-200' },
  C: { label: 'Configuration', color: 'text-blue-700', bg: 'bg-blue-100', border: 'border-blue-200' },
  D: { label: 'Development', color: 'text-amber-700', bg: 'bg-amber-100', border: 'border-amber-200' },
  T: { label: 'Third-party', color: 'text-indigo-700', bg: 'bg-indigo-100', border: 'border-indigo-200' },
  N: { label: 'Not available', color: 'text-red-700', bg: 'bg-red-100', border: 'border-red-200' },
};

export default function ResponseCodeBadge({ code, editable = false, onChange }) {
  const info = CODE_INFO[code] || CODE_INFO.S;

  if (!editable) {
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium border ${info.bg} ${info.color} ${info.border}`}>
        {code} · {info.label}
      </span>
    );
  }

  return (
    <select
      value={code}
      onChange={(e) => onChange(e.target.value)}
      className={`text-xs font-medium border rounded px-2 py-0.5 ${info.bg} ${info.color} ${info.border} focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-transparent`}
    >
      {Object.entries(CODE_INFO).map(([c, info]) => (
        <option key={c} value={c}>
          {c} · {info.label}
        </option>
      ))}
    </select>
  );
}
