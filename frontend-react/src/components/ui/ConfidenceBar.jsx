import React from 'react';

/**
 * Confidence bar with color coding:
 *  ≥ 0.75 → green
 *  0.45–0.74 → yellow
 *  < 0.45 → red
 */
export default function ConfidenceBar({ value }) {
  const pct = Math.round((value || 0) * 100);

  let colorClass;
  if (pct >= 75) {
    colorClass = 'bg-green-500';
  } else if (pct >= 45) {
    colorClass = 'bg-yellow-400';
  } else {
    colorClass = 'bg-red-500';
  }

  let textColor;
  if (pct >= 75) {
    textColor = 'text-green-700';
  } else if (pct >= 45) {
    textColor = 'text-yellow-700';
  } else {
    textColor = 'text-red-700';
  }

  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 bg-gray-200 rounded-full h-3 overflow-hidden">
        <div
          className={`${colorClass} h-3 rounded-full transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`text-sm font-semibold ${textColor} w-12 text-right`}>
        {pct}%
      </span>
    </div>
  );
}
