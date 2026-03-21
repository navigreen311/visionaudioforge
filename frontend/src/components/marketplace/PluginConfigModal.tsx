'use client';

import { useState } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PluginSummary {
  id: string;
  name: string;
  config: Record<string, string | number | boolean>;
}

interface PluginConfigModalProps {
  plugin: PluginSummary;
  onSave: (config: Record<string, string | number | boolean>) => void;
  onClose: () => void;
}

interface ConfigEntry {
  key: string;
  value: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function toEntries(config: Record<string, string | number | boolean>): ConfigEntry[] {
  return Object.entries(config).map(([key, value]) => ({
    key,
    value: String(value),
  }));
}

function fromEntries(entries: ConfigEntry[]): Record<string, string | number | boolean> {
  const result: Record<string, string | number | boolean> = {};
  for (const { key, value } of entries) {
    if (!key.trim()) continue;
    // Attempt numeric / boolean coercion
    if (value === 'true') {
      result[key] = true;
    } else if (value === 'false') {
      result[key] = false;
    } else if (value !== '' && !isNaN(Number(value))) {
      result[key] = Number(value);
    } else {
      result[key] = value;
    }
  }
  return result;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function PluginConfigModal({ plugin, onSave, onClose }: PluginConfigModalProps) {
  const [entries, setEntries] = useState<ConfigEntry[]>(() => {
    const initial = toEntries(plugin.config);
    return initial.length > 0 ? initial : [{ key: '', value: '' }];
  });

  const updateEntry = (index: number, field: 'key' | 'value', val: string) => {
    setEntries((prev) =>
      prev.map((e, i) => (i === index ? { ...e, [field]: val } : e)),
    );
  };

  const addEntry = () => {
    setEntries((prev) => [...prev, { key: '', value: '' }]);
  };

  const removeEntry = (index: number) => {
    setEntries((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSave = () => {
    onSave(fromEntries(entries));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">
            Configure {plugin.name}
          </h3>
          <button
            onClick={onClose}
            className="rounded p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
            aria-label="Close"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <p className="mt-1 text-xs text-gray-500">
          Edit key-value configuration entries for this plugin.
        </p>

        {/* Entries */}
        <div className="mt-4 max-h-72 space-y-2 overflow-y-auto pr-1">
          {entries.map((entry, idx) => (
            <div key={idx} className="flex items-center gap-2">
              <input
                type="text"
                placeholder="Key"
                value={entry.key}
                onChange={(e) => updateEntry(idx, 'key', e.target.value)}
                className="w-1/3 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
              <input
                type="text"
                placeholder="Value"
                value={entry.value}
                onChange={(e) => updateEntry(idx, 'value', e.target.value)}
                className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
              <button
                onClick={() => removeEntry(idx)}
                className="rounded p-1.5 text-gray-400 transition-colors hover:bg-red-50 hover:text-red-500"
                aria-label="Remove entry"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
              </button>
            </div>
          ))}
        </div>

        {/* Add row */}
        <button
          onClick={addEntry}
          className="mt-2 flex items-center gap-1 text-xs font-medium text-brand-600 transition-colors hover:text-brand-700"
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add Entry
        </button>

        {/* Footer */}
        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 transition-colors hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700"
          >
            Save Configuration
          </button>
        </div>
      </div>
    </div>
  );
}
