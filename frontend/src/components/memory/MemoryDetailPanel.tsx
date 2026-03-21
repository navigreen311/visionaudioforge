'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import Badge from '../ui/Badge';
import Button from '../ui/Button';
import LoadingSpinner from '../ui/LoadingSpinner';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface MemoryItem {
  id: string;
  content: string;
  category: string;
  importance: number;
  importance_score: number;
  freshness_score: number;
  scope: 'workspace' | 'user' | 'global';
  is_private: boolean;
  source: string | null;
  source_type: string;
  tags: string[];
  access_count: number;
  confidence: number;
  created_at: string;
  updated_at: string;
  last_accessed: string | null;
  archived: boolean;
  metadata: Record<string, unknown>;
}

export interface RelatedMemory {
  id: string;
  content: string;
  similarity: number;
  category: string;
}

interface DecayEvent {
  timestamp: string;
  importance_before: number;
  importance_after: number;
  trigger: string;
}

interface DecayHistory {
  created_at: string;
  initial_importance: number;
  events: DecayEvent[];
  current_importance: number;
}

interface MemoryDetailPanelProps {
  memory: MemoryItem | null;
  isOpen: boolean;
  onClose: () => void;
  onUpdate: (updated: MemoryItem) => void;
  onDelete: (id: string) => void;
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '';

async function patchMemory(
  id: string,
  patch: Partial<MemoryItem>,
): Promise<MemoryItem> {
  const res = await fetch(`${API_BASE}/api/memory/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  });
  if (!res.ok) throw new Error(`PATCH /api/memory/${id} failed: ${res.status}`);
  return res.json() as Promise<MemoryItem>;
}

async function fetchRelated(id: string): Promise<RelatedMemory[]> {
  const res = await fetch(`${API_BASE}/api/memory/${id}/related`);
  if (!res.ok) return [];
  const data = (await res.json()) as { related: RelatedMemory[] };
  return data.related;
}

async function fetchDecayHistory(id: string): Promise<DecayHistory | null> {
  const res = await fetch(`${API_BASE}/api/memory/${id}/decay-history`);
  if (!res.ok) return null;
  return res.json() as Promise<DecayHistory>;
}

async function postDecay(id: string): Promise<MemoryItem> {
  const res = await fetch(`${API_BASE}/api/memory/${id}/decay`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`POST /api/memory/${id}/decay failed`);
  return res.json() as Promise<MemoryItem>;
}

async function postPromote(id: string): Promise<MemoryItem> {
  const res = await fetch(`${API_BASE}/api/memory/${id}/promote`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`POST /api/memory/${id}/promote failed`);
  return res.json() as Promise<MemoryItem>;
}

async function deleteMemory(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/memory/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`DELETE /api/memory/${id} failed`);
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">
      {children}
    </h3>
  );
}

function MetadataField({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-sm text-gray-500">{label}</span>
      <div className="text-sm text-gray-900">{children}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Editable metadata helpers
// ---------------------------------------------------------------------------

function EditableSelect({
  value,
  options,
  onChange,
}: {
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="rounded border border-gray-300 bg-white px-2 py-0.5 text-sm text-gray-900 focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
    >
      {options.map((opt) => (
        <option key={opt} value={opt}>
          {opt}
        </option>
      ))}
    </select>
  );
}

function EditableNumber({
  value,
  min,
  max,
  step,
  onChange,
}: {
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
}) {
  return (
    <input
      type="number"
      value={value}
      min={min}
      max={max}
      step={step}
      onChange={(e) => onChange(parseFloat(e.target.value))}
      onBlur={(e) => onChange(parseFloat(e.target.value))}
      className="w-20 rounded border border-gray-300 px-2 py-0.5 text-sm text-gray-900 focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
    />
  );
}

function Toggle({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ${
        checked ? 'bg-brand-600' : 'bg-gray-200'
      }`}
    >
      <span
        className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition-transform ${
          checked ? 'translate-x-4' : 'translate-x-0'
        }`}
      />
    </button>
  );
}

function TagEditor({
  tags,
  onChange,
}: {
  tags: string[];
  onChange: (tags: string[]) => void;
}) {
  const [input, setInput] = useState('');

  const addTag = () => {
    const tag = input.trim();
    if (tag && !tags.includes(tag)) {
      onChange([...tags, tag]);
    }
    setInput('');
  };

  const removeTag = (tag: string) => {
    onChange(tags.filter((t) => t !== tag));
  };

  return (
    <div className="space-y-1">
      <div className="flex flex-wrap gap-1">
        {tags.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-2 py-0.5 text-xs text-brand-700"
          >
            {tag}
            <button
              onClick={() => removeTag(tag)}
              className="hover:text-red-600"
              aria-label={`Remove tag ${tag}`}
            >
              x
            </button>
          </span>
        ))}
      </div>
      <div className="flex gap-1">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              addTag();
            }
          }}
          placeholder="Add tag..."
          className="flex-1 rounded border border-gray-300 px-2 py-0.5 text-xs focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
        />
        <button
          onClick={addTag}
          className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600 hover:bg-gray-200"
        >
          Add
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Decay timeline
// ---------------------------------------------------------------------------

function DecayTimeline({ history }: { history: DecayHistory | null }) {
  if (!history) {
    return <p className="text-xs text-gray-400 italic">No decay history available.</p>;
  }

  const formatDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return iso;
    }
  };

  return (
    <div className="relative space-y-3 pl-4 border-l-2 border-gray-200">
      {/* Created */}
      <div className="relative">
        <div className="absolute -left-[1.3rem] top-1 h-2.5 w-2.5 rounded-full bg-green-500" />
        <p className="text-xs text-gray-700">
          <span className="font-medium">Created</span>{' '}
          <span className="text-gray-400">{formatDate(history.created_at)}</span>
        </p>
        <p className="text-xs text-gray-500">
          Importance: {history.initial_importance.toFixed(2)}
        </p>
      </div>

      {/* Decay events */}
      {history.events.map((evt, idx) => (
        <div key={idx} className="relative">
          <div className="absolute -left-[1.3rem] top-1 h-2.5 w-2.5 rounded-full bg-yellow-400" />
          <p className="text-xs text-gray-700">
            <span className="font-medium">{evt.trigger}</span>{' '}
            <span className="text-gray-400">{formatDate(evt.timestamp)}</span>
          </p>
          <p className="text-xs text-gray-500">
            {evt.importance_before.toFixed(2)} &rarr; {evt.importance_after.toFixed(2)}
          </p>
        </div>
      ))}

      {/* Current */}
      <div className="relative">
        <div className="absolute -left-[1.3rem] top-1 h-2.5 w-2.5 rounded-full bg-brand-600" />
        <p className="text-xs text-gray-700">
          <span className="font-medium">Current</span>
        </p>
        <p className="text-xs text-gray-500">
          Importance: {history.current_importance.toFixed(2)}
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Related memories
// ---------------------------------------------------------------------------

function RelatedMemories({
  related,
  loading,
  onView,
}: {
  related: RelatedMemory[];
  loading: boolean;
  onView: (id: string) => void;
}) {
  if (loading) return <LoadingSpinner size="sm" />;
  if (related.length === 0) {
    return <p className="text-xs text-gray-400 italic">No related memories found.</p>;
  }

  return (
    <ul className="space-y-2">
      {related.slice(0, 3).map((rm) => (
        <li
          key={rm.id}
          className="flex items-start justify-between rounded border border-gray-100 p-2"
        >
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm text-gray-800">{rm.content}</p>
            <div className="mt-0.5 flex gap-2 text-xs text-gray-400">
              <span>{rm.category}</span>
              <span>{(rm.similarity * 100).toFixed(0)}% similar</span>
            </div>
          </div>
          <button
            onClick={() => onView(rm.id)}
            className="ml-2 shrink-0 rounded bg-gray-100 px-2 py-1 text-xs text-gray-600 hover:bg-gray-200"
          >
            View
          </button>
        </li>
      ))}
    </ul>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function MemoryDetailPanel({
  memory,
  isOpen,
  onClose,
  onUpdate,
  onDelete,
}: MemoryDetailPanelProps) {
  // -- Local editable state --
  const [content, setContent] = useState('');
  const [category, setCategory] = useState('');
  const [importance, setImportance] = useState(0.5);
  const [scope, setScope] = useState<'workspace' | 'user' | 'global'>('workspace');
  const [isPrivate, setIsPrivate] = useState(false);
  const [source, setSource] = useState('');
  const [tags, setTags] = useState<string[]>([]);

  // -- Async data --
  const [related, setRelated] = useState<RelatedMemory[]>([]);
  const [relatedLoading, setRelatedLoading] = useState(false);
  const [decayHistory, setDecayHistory] = useState<DecayHistory | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');

  const panelRef = useRef<HTMLDivElement>(null);

  // -- Sync local state when memory prop changes --
  useEffect(() => {
    if (!memory) return;
    setContent(memory.content);
    setCategory(memory.category);
    setImportance(memory.importance);
    setScope(memory.scope);
    setIsPrivate(memory.is_private);
    setSource(memory.source ?? '');
    setTags(memory.tags ?? []);
    setSaveStatus('idle');
  }, [memory]);

  // -- Load related memories + decay history --
  useEffect(() => {
    if (!memory || !isOpen) return;
    setRelatedLoading(true);
    fetchRelated(memory.id)
      .then(setRelated)
      .catch(() => setRelated([]))
      .finally(() => setRelatedLoading(false));

    fetchDecayHistory(memory.id)
      .then(setDecayHistory)
      .catch(() => setDecayHistory(null));
  }, [memory, isOpen]);

  // -- Escape to close --
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [isOpen, onClose]);

  // -- Lock body scroll --
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  // -- Auto-save on blur (content) --
  const handleContentBlur = useCallback(async () => {
    if (!memory || content === memory.content) return;
    setSaveStatus('saving');
    try {
      const updated = await patchMemory(memory.id, { content });
      onUpdate(updated);
      setSaveStatus('saved');
    } catch {
      setSaveStatus('error');
    }
  }, [memory, content, onUpdate]);

  // -- Save metadata field --
  const saveField = useCallback(
    async (patch: Partial<MemoryItem>) => {
      if (!memory) return;
      setSaveStatus('saving');
      try {
        const updated = await patchMemory(memory.id, patch);
        onUpdate(updated);
        setSaveStatus('saved');
      } catch {
        setSaveStatus('error');
      }
    },
    [memory, onUpdate],
  );

  // -- Actions --
  const handleDecay = async () => {
    if (!memory) return;
    setActionLoading('decay');
    try {
      const updated = await postDecay(memory.id);
      onUpdate(updated);
    } catch {
      /* swallow — toast in production */
    } finally {
      setActionLoading(null);
    }
  };

  const handlePromote = async () => {
    if (!memory) return;
    setActionLoading('promote');
    try {
      const updated = await postPromote(memory.id);
      onUpdate(updated);
    } catch {
      /* swallow */
    } finally {
      setActionLoading(null);
    }
  };

  const handleArchive = async () => {
    if (!memory) return;
    setActionLoading('archive');
    try {
      const updated = await patchMemory(memory.id, { archived: true } as Partial<MemoryItem>);
      onUpdate(updated);
    } catch {
      /* swallow */
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async () => {
    if (!memory) return;
    setActionLoading('delete');
    try {
      await deleteMemory(memory.id);
      onDelete(memory.id);
      onClose();
    } catch {
      /* swallow */
    } finally {
      setActionLoading(null);
    }
  };

  // -- View related memory --
  const handleViewRelated = (_id: string) => {
    // In a full implementation this would navigate or swap the panel content.
    // For now we do nothing — the parent can handle routing.
  };

  if (!isOpen || !memory) return null;

  const scopeBadgeVariant: Record<string, string> = {
    workspace: 'info',
    user: 'warning',
    global: 'success',
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/30 transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Slide-over panel */}
      <div
        ref={panelRef}
        className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col bg-white shadow-xl transition-transform"
        role="dialog"
        aria-modal="true"
        aria-label="Memory detail"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold text-gray-900">Memory Detail</h2>
            <Badge variant={scopeBadgeVariant[memory.scope] ?? 'neutral'}>
              {memory.scope}
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            {saveStatus === 'saving' && (
              <span className="text-xs text-gray-400">Saving...</span>
            )}
            {saveStatus === 'saved' && (
              <span className="text-xs text-green-600">Saved</span>
            )}
            {saveStatus === 'error' && (
              <span className="text-xs text-red-600">Error</span>
            )}
            <button
              onClick={onClose}
              className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
              aria-label="Close panel"
            >
              <svg
                className="h-5 w-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
          {/* A. Full content — editable */}
          <section>
            <SectionHeading>Content</SectionHeading>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              onBlur={handleContentBlur}
              rows={6}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 resize-y"
              placeholder="Memory content..."
            />
          </section>

          {/* B. Metadata */}
          <section>
            <SectionHeading>Metadata</SectionHeading>
            <div className="divide-y divide-gray-100">
              <MetadataField label="Category">
                <EditableSelect
                  value={category}
                  options={[
                    'general',
                    'preference',
                    'fact',
                    'procedure',
                    'context',
                    'feedback',
                  ]}
                  onChange={(v) => {
                    setCategory(v);
                    saveField({ category: v });
                  }}
                />
              </MetadataField>

              <MetadataField label="Importance">
                <EditableNumber
                  value={importance}
                  min={0}
                  max={1}
                  step={0.05}
                  onChange={(v) => {
                    setImportance(v);
                    saveField({ importance: v });
                  }}
                />
              </MetadataField>

              <MetadataField label="Scope">
                <EditableSelect
                  value={scope}
                  options={['workspace', 'user', 'global']}
                  onChange={(v) => {
                    const s = v as 'workspace' | 'user' | 'global';
                    setScope(s);
                    saveField({ scope: s });
                  }}
                />
              </MetadataField>

              <MetadataField label="Private">
                <Toggle
                  checked={isPrivate}
                  onChange={(v) => {
                    setIsPrivate(v);
                    saveField({ is_private: v });
                  }}
                />
              </MetadataField>

              <MetadataField label="Source">
                <input
                  type="text"
                  value={source}
                  onChange={(e) => setSource(e.target.value)}
                  onBlur={() => {
                    if (source !== (memory.source ?? '')) {
                      saveField({ source: source || null });
                    }
                  }}
                  className="w-32 rounded border border-gray-300 px-2 py-0.5 text-sm text-right focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
                  placeholder="—"
                />
              </MetadataField>

              <div className="py-2">
                <p className="text-sm text-gray-500 mb-1">Tags</p>
                <TagEditor
                  tags={tags}
                  onChange={(newTags) => {
                    setTags(newTags);
                    saveField({ tags: newTags });
                  }}
                />
              </div>
            </div>
          </section>

          {/* C. Decay history mini timeline */}
          <section>
            <SectionHeading>Decay History</SectionHeading>
            <DecayTimeline history={decayHistory} />
          </section>

          {/* D. Related memories */}
          <section>
            <SectionHeading>Related Memories</SectionHeading>
            <RelatedMemories
              related={related}
              loading={relatedLoading}
              onView={handleViewRelated}
            />
          </section>
        </div>

        {/* E. Actions footer */}
        <div className="border-t border-gray-200 bg-gray-50 px-6 py-3">
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              size="sm"
              loading={actionLoading === 'decay'}
              onClick={handleDecay}
            >
              Decay Now
            </Button>
            <Button
              variant="primary"
              size="sm"
              loading={actionLoading === 'promote'}
              onClick={handlePromote}
            >
              Promote
            </Button>
            <Button
              variant="secondary"
              size="sm"
              loading={actionLoading === 'archive'}
              onClick={handleArchive}
            >
              Archive
            </Button>
            <div className="flex-1" />
            <Button
              variant="danger"
              size="sm"
              loading={actionLoading === 'delete'}
              onClick={handleDelete}
            >
              Delete
            </Button>
          </div>
        </div>
      </div>
    </>
  );
}
