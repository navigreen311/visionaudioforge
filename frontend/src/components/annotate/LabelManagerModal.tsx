'use client';

import { useState, useCallback, useRef } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AnnotationLabel {
  id: string;
  name: string;
  color: string;
  shortcut?: string;
}

interface LabelManagerModalProps {
  isOpen: boolean;
  onClose: () => void;
  labels: AnnotationLabel[];
  onLabelsChange: (labels: AnnotationLabel[]) => void;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STORAGE_KEY = 'vaf_annotation_labels';

const PRESET_COLORS = [
  '#ef4444', // red
  '#f97316', // orange
  '#eab308', // yellow
  '#22c55e', // green
  '#3b82f6', // blue
  '#8b5cf6', // violet
  '#ec4899', // pink
  '#06b6d4', // cyan
] as const;

const SHORTCUT_KEYS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function generateId(): string {
  return `lbl_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

export function loadLabelsFromStorage(): AnnotationLabel[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (l): l is AnnotationLabel =>
        typeof l === 'object' &&
        l !== null &&
        typeof (l as Record<string, unknown>).id === 'string' &&
        typeof (l as Record<string, unknown>).name === 'string' &&
        typeof (l as Record<string, unknown>).color === 'string',
    );
  } catch {
    return [];
  }
}

export function saveLabelsToStorage(labels: AnnotationLabel[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(labels));
  } catch {
    // Storage full or unavailable — silently ignore
  }
}

function isValidHex(hex: string): boolean {
  return /^#[0-9a-fA-F]{6}$/.test(hex);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function LabelManagerModal({
  isOpen,
  onClose,
  labels,
  onLabelsChange,
}: LabelManagerModalProps) {
  const [newName, setNewName] = useState('');
  const [newColor, setNewColor] = useState<string>(PRESET_COLORS[0]);
  const [hexInput, setHexInput] = useState<string>(PRESET_COLORS[0]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [editColor, setEditColor] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Persist helper
  const updateLabels = useCallback(
    (next: AnnotationLabel[]) => {
      onLabelsChange(next);
      saveLabelsToStorage(next);
    },
    [onLabelsChange],
  );

  // ------ Add ------
  const handleAdd = () => {
    const trimmed = newName.trim();
    if (!trimmed) return;
    if (labels.some((l) => l.name.toLowerCase() === trimmed.toLowerCase())) return;

    const idx = labels.length;
    const shortcut = idx < SHORTCUT_KEYS.length ? SHORTCUT_KEYS[idx] : undefined;

    updateLabels([
      ...labels,
      { id: generateId(), name: trimmed, color: newColor, shortcut },
    ]);
    setNewName('');
  };

  // ------ Delete ------
  const handleDelete = (id: string) => {
    updateLabels(labels.filter((l) => l.id !== id));
  };

  // ------ Edit ------
  const startEdit = (label: AnnotationLabel) => {
    setEditingId(label.id);
    setEditName(label.name);
    setEditColor(label.color);
  };

  const saveEdit = () => {
    if (!editingId) return;
    const trimmed = editName.trim();
    if (!trimmed) return;

    updateLabels(
      labels.map((l) =>
        l.id === editingId ? { ...l, name: trimmed, color: editColor } : l,
      ),
    );
    setEditingId(null);
  };

  const cancelEdit = () => setEditingId(null);

  // ------ Color picking ------
  const selectPresetColor = (color: string) => {
    setNewColor(color);
    setHexInput(color);
  };

  const handleHexChange = (value: string) => {
    setHexInput(value);
    if (isValidHex(value)) {
      setNewColor(value);
    }
  };

  // ------ COCO Import ------
  const handleImportCOCO = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const raw: unknown = JSON.parse(ev.target?.result as string);
        if (
          typeof raw !== 'object' ||
          raw === null ||
          !Array.isArray((raw as Record<string, unknown>).categories)
        ) {
          return;
        }

        const categories = (raw as { categories: unknown[] }).categories;
        const imported: AnnotationLabel[] = [];

        for (const cat of categories) {
          if (typeof cat !== 'object' || cat === null) continue;
          const c = cat as Record<string, unknown>;
          const name = typeof c.name === 'string' ? c.name : String(c.id ?? '');
          if (!name) continue;
          if (labels.some((l) => l.name.toLowerCase() === name.toLowerCase())) continue;

          const idx = labels.length + imported.length;
          imported.push({
            id: generateId(),
            name,
            color: PRESET_COLORS[idx % PRESET_COLORS.length],
            shortcut: idx < SHORTCUT_KEYS.length ? SHORTCUT_KEYS[idx] : undefined,
          });
        }

        if (imported.length > 0) {
          updateLabels([...labels, ...imported]);
        }
      } catch {
        // Invalid JSON — silently ignore
      }
    };
    reader.readAsText(file);

    // Reset input so the same file can be re-imported
    e.target.value = '';
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-lg rounded-xl bg-white shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-6 py-4">
          <h2 className="text-lg font-semibold text-gray-900">Label Manager</h2>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            aria-label="Close"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="max-h-[60vh] overflow-y-auto px-6 py-4">
          {/* Label list */}
          {labels.length === 0 ? (
            <p className="mb-4 text-sm italic text-gray-400">No labels defined yet.</p>
          ) : (
            <ul className="mb-4 flex flex-col gap-2">
              {labels.map((label) => (
                <li
                  key={label.id}
                  className="flex items-center gap-3 rounded-lg border border-gray-200 px-3 py-2"
                >
                  {editingId === label.id ? (
                    <>
                      <input
                        type="color"
                        value={editColor}
                        onChange={(e) => setEditColor(e.target.value)}
                        className="h-6 w-6 cursor-pointer rounded border-0"
                      />
                      <input
                        type="text"
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && saveEdit()}
                        className="flex-1 rounded border border-gray-300 px-2 py-1 text-sm focus:border-brand-500 focus:outline-none"
                        autoFocus
                      />
                      <button
                        onClick={saveEdit}
                        className="text-xs font-medium text-green-600 hover:text-green-800"
                      >
                        Save
                      </button>
                      <button
                        onClick={cancelEdit}
                        className="text-xs font-medium text-gray-400 hover:text-gray-600"
                      >
                        Cancel
                      </button>
                    </>
                  ) : (
                    <>
                      {/* Color swatch */}
                      <span
                        className="inline-block h-5 w-5 flex-shrink-0 rounded"
                        style={{ backgroundColor: label.color }}
                      />
                      {/* Name */}
                      <span className="flex-1 truncate text-sm text-gray-800">
                        {label.name}
                      </span>
                      {/* Shortcut hint */}
                      {label.shortcut && (
                        <kbd className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-500">
                          {label.shortcut}
                        </kbd>
                      )}
                      {/* Edit */}
                      <button
                        onClick={() => startEdit(label)}
                        className="text-gray-400 hover:text-gray-600"
                        title="Edit label"
                      >
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                      {/* Delete */}
                      <button
                        onClick={() => handleDelete(label.id)}
                        className="text-red-400 hover:text-red-600"
                        title="Delete label"
                      >
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </>
                  )}
                </li>
              ))}
            </ul>
          )}

          {/* Add label form */}
          <div className="rounded-lg border border-dashed border-gray-300 p-4">
            <p className="mb-2 text-xs font-medium uppercase tracking-wider text-gray-500">
              Add Label
            </p>

            {/* Name input */}
            <input
              type="text"
              placeholder="Label name..."
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
              className="mb-3 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />

            {/* Color presets */}
            <div className="mb-2 flex flex-wrap items-center gap-2">
              {PRESET_COLORS.map((color) => (
                <button
                  key={color}
                  onClick={() => selectPresetColor(color)}
                  className={`h-7 w-7 rounded-full border-2 transition-transform ${
                    newColor === color
                      ? 'scale-110 border-gray-800'
                      : 'border-transparent hover:scale-105'
                  }`}
                  style={{ backgroundColor: color }}
                  title={color}
                  aria-label={`Select color ${color}`}
                />
              ))}

              {/* Hex input */}
              <input
                type="text"
                value={hexInput}
                onChange={(e) => handleHexChange(e.target.value)}
                placeholder="#000000"
                maxLength={7}
                className={`w-20 rounded border px-2 py-1 text-xs font-mono ${
                  isValidHex(hexInput)
                    ? 'border-gray-300'
                    : 'border-red-300'
                } focus:outline-none`}
              />
            </div>

            {/* Add button */}
            <button
              onClick={handleAdd}
              disabled={!newName.trim()}
              className="w-full rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Add
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t px-6 py-3">
          <button
            onClick={() => fileInputRef.current?.click()}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
          >
            Import from COCO JSON
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            className="hidden"
            onChange={handleImportCOCO}
          />

          <button
            onClick={onClose}
            className="rounded-lg bg-gray-100 px-4 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-200"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
