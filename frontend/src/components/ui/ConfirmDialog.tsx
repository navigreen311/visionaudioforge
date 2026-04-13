'use client';

import React, { useCallback, useEffect, useState } from 'react';
import type { ConfirmOptions } from '@/providers/ConfirmProvider';

interface ConfirmDialogProps {
  options: ConfirmOptions;
  onConfirm: () => void;
  onCancel: () => void;
}

const variantColors: Record<string, string> = {
  danger: '#A32D2D',
  warning: '#854F0B',
  info: '#185FA5',
};

export default function ConfirmDialog({ options, onConfirm, onCancel }: ConfirmDialogProps) {
  const { title, message, confirmLabel = 'Confirm', cancelLabel = 'Cancel', variant = 'info', requireTyping } = options;
  const [typedValue, setTypedValue] = useState('');

  const isConfirmDisabled = requireTyping ? typedValue !== requireTyping : false;

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onCancel();
      }
    },
    [onCancel],
  );

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  return (
    <div
      className="fixed inset-0 bg-black/50 z-[200] flex items-center justify-center"
      onClick={onCancel}
    >
      <div
        className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4 p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold text-gray-900 mb-2">{title}</h2>
        <p className="text-sm text-gray-600 mb-4">{message}</p>

        {requireTyping && (
          <div className="mb-4">
            <p className="text-xs text-gray-500 mb-1">
              Type <span className="font-mono font-semibold">{requireTyping}</span> to confirm
            </p>
            <input
              type="text"
              value={typedValue}
              onChange={(e) => setTypedValue(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              autoFocus
            />
          </div>
        )}

        <div className="flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-200 rounded hover:bg-gray-300 transition-colors"
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            disabled={isConfirmDisabled}
            className="px-4 py-2 text-sm font-medium text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ backgroundColor: isConfirmDisabled ? undefined : variantColors[variant] }}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
