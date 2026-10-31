import React from 'react';

/**
 * Status/category badge component
 * Supported variants: approved, pending, open, resolved, flagged_owner, low_confidence, draft, clarification, info
 */
export default function Badge({ label, variant = 'info' }) {
  const variantClasses = {
    approved:       'bg-green-100 text-green-800 border border-green-200',
    pending:        'bg-yellow-100 text-yellow-800 border border-yellow-200',
    open:           'bg-orange-100 text-orange-800 border border-orange-200',
    resolved:       'bg-green-100 text-green-800 border border-green-200',
    flagged_owner:  'bg-blue-100 text-blue-800 border border-blue-200',
    low_confidence: 'bg-red-100 text-red-800 border border-red-200',
    draft:          'bg-gray-100 text-gray-700 border border-gray-200',
    clarification:  'bg-red-100 text-red-800 border border-red-200',
    info:           'bg-indigo-100 text-indigo-800 border border-indigo-200',
    mandatory:      'bg-purple-100 text-purple-800 border border-purple-200',
  };

  const cls = variantClasses[variant] || variantClasses.info;

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${cls}`}>
      {label}
    </span>
  );
}
