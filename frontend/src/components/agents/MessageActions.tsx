"use client";

import { useCallback, useRef, useState } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SaveToMemoryPayload {
  content: string;
  category: string;
  importance: number;
}

interface MessageActionsProps {
  messageText: string;
  messageId: string;
  onRegenerate: () => void;
  agentId?: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MEMORY_CATEGORIES = [
  "general",
  "instruction",
  "preference",
  "context",
  "fact",
  "correction",
] as const;

type MemoryCategory = (typeof MEMORY_CATEGORIES)[number];

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for non-secure contexts
      const textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [text]);

  return (
    <button
      onClick={handleCopy}
      title="Copy to clipboard"
      className="p-1.5 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
    >
      {copied ? (
        <svg className="w-4 h-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      ) : (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
      )}
    </button>
  );
}

function ThumbButton({
  direction,
  messageId,
  agentId,
}: {
  direction: "up" | "down";
  messageId: string;
  agentId: string;
}) {
  const [submitted, setSubmitted] = useState(false);

  const handleClick = useCallback(async () => {
    if (submitted) return;
    try {
      await fetch("/api/agents/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message_id: messageId,
          agent_id: agentId,
          rating: direction,
        }),
      });
      setSubmitted(true);
    } catch {
      // Silently fail — feedback is non-critical
    }
  }, [messageId, agentId, direction, submitted]);

  const isUp = direction === "up";

  return (
    <button
      onClick={handleClick}
      title={isUp ? "Good response" : "Bad response"}
      disabled={submitted}
      className={`p-1.5 rounded-md transition-colors ${
        submitted
          ? isUp
            ? "text-green-500"
            : "text-red-500"
          : "text-gray-400 hover:text-gray-600 hover:bg-gray-100"
      }`}
    >
      {isUp ? (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
        </svg>
      ) : (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
        </svg>
      )}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Save to Memory Popover
// ---------------------------------------------------------------------------

function SaveToMemoryPopover({
  messageText,
  agentId,
  onClose,
}: {
  messageText: string;
  agentId: string;
  onClose: () => void;
}) {
  const [content, setContent] = useState(messageText.slice(0, 500));
  const [category, setCategory] = useState<MemoryCategory>("general");
  const [importance, setImportance] = useState(5);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const handleSave = useCallback(async () => {
    if (!content.trim() || saving) return;
    setSaving(true);
    try {
      const payload: SaveToMemoryPayload = {
        content: content.trim(),
        category,
        importance,
      };
      const res = await fetch("/api/agents/memory", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          agent_id: agentId,
          ...payload,
        }),
      });
      if (res.ok) {
        setSaved(true);
        setTimeout(onClose, 1200);
      }
    } catch {
      // Allow retry on failure
    } finally {
      setSaving(false);
    }
  }, [content, category, importance, agentId, saving, onClose]);

  return (
    <div className="absolute bottom-full right-0 mb-2 w-80 bg-white border border-gray-200 rounded-xl shadow-xl z-50 p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-gray-700">Save to Memory</h4>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 text-lg leading-none"
        >
          &times;
        </button>
      </div>

      {/* Content */}
      <label className="block text-xs font-medium text-gray-500 mb-1">Content</label>
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        rows={3}
        className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
      />

      {/* Category */}
      <label className="block text-xs font-medium text-gray-500 mt-3 mb-1">Category</label>
      <select
        value={category}
        onChange={(e) => setCategory(e.target.value as MemoryCategory)}
        className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
      >
        {MEMORY_CATEGORIES.map((cat) => (
          <option key={cat} value={cat}>
            {cat.charAt(0).toUpperCase() + cat.slice(1)}
          </option>
        ))}
      </select>

      {/* Importance Slider */}
      <label className="block text-xs font-medium text-gray-500 mt-3 mb-1">
        Importance: {importance}/10
      </label>
      <input
        type="range"
        min={1}
        max={10}
        value={importance}
        onChange={(e) => setImportance(Number(e.target.value))}
        className="w-full accent-brand-600"
      />

      {/* Save */}
      <button
        onClick={handleSave}
        disabled={saving || saved || !content.trim()}
        className={`mt-3 w-full py-2 rounded-lg text-sm font-medium transition-colors ${
          saved
            ? "bg-green-500 text-white"
            : "bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed"
        }`}
      >
        {saved ? "Saved!" : saving ? "Saving..." : "Save Memory"}
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function MessageActions({
  messageText,
  messageId,
  onRegenerate,
  agentId = "default",
}: MessageActionsProps) {
  const [showMemoryPopover, setShowMemoryPopover] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  return (
    <div className="relative flex items-center gap-0.5 bg-white border border-gray-200 rounded-lg shadow-sm px-1 py-0.5">
      {/* Copy */}
      <CopyButton text={messageText} />

      {/* Regenerate */}
      <button
        onClick={onRegenerate}
        title="Regenerate response"
        className="p-1.5 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
      </button>

      {/* Save to Memory */}
      <div className="relative" ref={popoverRef}>
        <button
          onClick={() => setShowMemoryPopover((v) => !v)}
          title="Save to memory"
          className={`p-1.5 rounded-md transition-colors ${
            showMemoryPopover
              ? "text-brand-600 bg-brand-50"
              : "text-gray-400 hover:text-gray-600 hover:bg-gray-100"
          }`}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
          </svg>
        </button>
        {showMemoryPopover && (
          <SaveToMemoryPopover
            messageText={messageText}
            agentId={agentId}
            onClose={() => setShowMemoryPopover(false)}
          />
        )}
      </div>

      {/* Thumbs up */}
      <ThumbButton direction="up" messageId={messageId} agentId={agentId} />

      {/* Thumbs down */}
      <ThumbButton direction="down" messageId={messageId} agentId={agentId} />
    </div>
  );
}
