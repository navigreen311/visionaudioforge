"use client";

import { useCallback, useEffect, useState } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ConversationMessage {
  id: string;
  role: "user" | "assistant" | "tool";
  content: string;
  timestamp: string;
  toolName?: string;
  toolInput?: Record<string, unknown>;
  toolResult?: string;
}

interface ConversationSummary {
  id: string;
  summary: string;
  skill_pack: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

interface ConversationDetail {
  id: string;
  summary: string;
  skill_pack: string;
  messages: ConversationMessage[];
  created_at: string;
  updated_at: string;
}

interface ConversationHistoryProps {
  isOpen: boolean;
  onClose: () => void;
  onLoadConversation: (messages: ConversationMessage[]) => void;
  onNewConversation: () => void;
}

// ---------------------------------------------------------------------------
// localStorage helpers
// ---------------------------------------------------------------------------

const STORAGE_KEY = "vaf_current_conversation";

export function saveConversationToStorage(messages: ConversationMessage[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
  } catch {
    // Storage full or unavailable — silently ignore
  }
}

export function loadConversationFromStorage(): ConversationMessage[] | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as ConversationMessage[];
  } catch {
    return null;
  }
}

export function clearConversationStorage(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // noop
  }
}

// ---------------------------------------------------------------------------
// Skill-pack badge color helper
// ---------------------------------------------------------------------------

function skillPackColor(pack: string): string {
  const colors: Record<string, string> = {
    general: "bg-gray-100 text-gray-700",
    investigator: "bg-purple-100 text-purple-700",
    qa_analyst: "bg-blue-100 text-blue-700",
    compliance: "bg-red-100 text-red-700",
    media_editor: "bg-green-100 text-green-700",
    operations: "bg-orange-100 text-orange-700",
    executive: "bg-indigo-100 text-indigo-700",
  };
  return colors[pack] ?? "bg-gray-100 text-gray-700";
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ConversationHistory({
  isOpen,
  onClose,
  onLoadConversation,
  onNewConversation,
}: ConversationHistoryProps) {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // -----------------------------------------------------------------------
  // Fetch conversation list
  // -----------------------------------------------------------------------

  const fetchConversations = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/agents/conversations");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: ConversationSummary[] = await res.json();
      setConversations(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load conversations");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      fetchConversations();
    }
  }, [isOpen, fetchConversations]);

  // -----------------------------------------------------------------------
  // Load a specific conversation
  // -----------------------------------------------------------------------

  const handleLoad = async (id: string) => {
    try {
      const res = await fetch(`/api/agents/conversations/${id}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: ConversationDetail = await res.json();
      onLoadConversation(data.messages);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load conversation");
    }
  };

  // -----------------------------------------------------------------------
  // Delete a conversation
  // -----------------------------------------------------------------------

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    try {
      const res = await fetch(`/api/agents/conversations/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setConversations((prev) => prev.filter((c) => c.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete conversation");
    } finally {
      setDeletingId(null);
    }
  };

  // -----------------------------------------------------------------------
  // New conversation
  // -----------------------------------------------------------------------

  const handleNew = () => {
    onNewConversation();
    onClose();
  };

  // -----------------------------------------------------------------------
  // Format helpers
  // -----------------------------------------------------------------------

  const formatDate = (iso: string): string => {
    try {
      const d = new Date(iso);
      return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
    } catch {
      return iso;
    }
  };

  const truncate = (text: string, max = 80): string =>
    text.length > max ? `${text.slice(0, max)}...` : text;

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/30 z-40 transition-opacity"
          onClick={onClose}
          aria-hidden
        />
      )}

      {/* Slide-over drawer (left) */}
      <div
        className={`fixed inset-y-0 left-0 z-50 w-80 max-w-full bg-white shadow-xl transform transition-transform duration-300 ease-in-out ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
            <h2 className="text-sm font-semibold text-gray-900">Conversation History</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
              aria-label="Close panel"
            >
              &times;
            </button>
          </div>

          {/* New conversation button */}
          <div className="px-4 py-3 border-b border-gray-100">
            <button
              onClick={handleNew}
              className="w-full bg-brand-600 text-white text-sm font-medium rounded-lg py-2 hover:bg-brand-700 transition-colors"
            >
              + New Conversation
            </button>
          </div>

          {/* Conversation list */}
          <div className="flex-1 overflow-y-auto">
            {loading && (
              <div className="flex items-center justify-center py-12">
                <span className="animate-spin inline-block w-5 h-5 border-2 border-brand-400 border-t-transparent rounded-full" />
              </div>
            )}

            {error && (
              <div className="px-4 py-3 text-xs text-red-600 bg-red-50 m-3 rounded-lg">
                {error}
              </div>
            )}

            {!loading && conversations.length === 0 && !error && (
              <p className="text-gray-400 text-xs text-center py-12">
                No past conversations yet.
              </p>
            )}

            <div className="divide-y divide-gray-100">
              {conversations.map((conv) => (
                <div
                  key={conv.id}
                  className="group px-4 py-3 hover:bg-gray-50 cursor-pointer transition-colors"
                  onClick={() => handleLoad(conv.id)}
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm text-gray-800 line-clamp-2 flex-1">
                      {truncate(conv.summary)}
                    </p>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(conv.id);
                      }}
                      disabled={deletingId === conv.id}
                      className="text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity shrink-0 text-lg leading-none disabled:opacity-50"
                      title="Delete conversation"
                    >
                      &times;
                    </button>
                  </div>

                  <div className="flex items-center gap-2 mt-1.5">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${skillPackColor(
                        conv.skill_pack
                      )}`}
                    >
                      {conv.skill_pack}
                    </span>
                    <span className="text-[10px] text-gray-400">
                      {formatDate(conv.created_at)}
                    </span>
                    <span className="text-[10px] text-gray-400">
                      {conv.message_count} msg{conv.message_count !== 1 ? "s" : ""}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
