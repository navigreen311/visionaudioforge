"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import Button from "@/components/ui/Button";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CommentData {
  id: string;
  user_id: string;
  content: string;
  parent_id: string | null;
  timestamp: string | null;
  replies: CommentData[];
  reactions?: Record<string, string[]>; // emoji -> user_ids
}

interface CommentsTabProps {
  caseId: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const TEAM_MEMBERS = [
  "Alice Chen",
  "Bob Martinez",
  "Carol Wu",
  "Dan Okafor",
  "Eva Singh",
  "Frank Kim",
  "Grace Liu",
  "Hiro Tanaka",
];

const REACTION_OPTIONS = [
  { emoji: "\uD83D\uDC4D", label: "thumbs up" },
  { emoji: "\u2757", label: "important" },
  { emoji: "\u2713", label: "done" },
];

const API_BASE = "/api/investigate";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getInitials(name: string): string {
  return name
    .split(/\s+/)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("")
    .slice(0, 2);
}

function relativeTime(iso: string | null): string {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function highlightMentions(text: string): React.ReactNode[] {
  const parts = text.split(/(@\w[\w\s]*?\b)/g);
  return parts.map((part, i) => {
    if (part.startsWith("@")) {
      return (
        <span key={i} className="text-blue-600 font-medium">
          {part}
        </span>
      );
    }
    return <span key={i}>{part}</span>;
  });
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ReactionBar({
  reactions,
  onToggle,
}: {
  reactions: Record<string, string[]>;
  onToggle: (emoji: string) => void;
}) {
  return (
    <div className="flex items-center gap-1 mt-1">
      {REACTION_OPTIONS.map(({ emoji }) => {
        const users = reactions[emoji] ?? [];
        const active = users.includes("current-user");
        return (
          <button
            key={emoji}
            onClick={() => onToggle(emoji)}
            className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs border transition-colors ${
              active
                ? "bg-blue-50 border-blue-300 text-blue-700"
                : "bg-gray-50 border-gray-200 text-gray-500 hover:bg-gray-100"
            }`}
          >
            {emoji}
            {users.length > 0 && <span>{users.length}</span>}
          </button>
        );
      })}
    </div>
  );
}

function CommentBubble({
  comment,
  onReply,
  onEdit,
  onDelete,
  onReaction,
  depth,
}: {
  comment: CommentData;
  onReply: (parentId: string) => void;
  onEdit: (commentId: string, newContent: string) => void;
  onDelete: (commentId: string) => void;
  onReaction: (commentId: string, emoji: string) => void;
  depth: number;
}) {
  const [hovered, setHovered] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState(comment.content);

  const handleSaveEdit = () => {
    if (editText.trim() && editText.trim() !== comment.content) {
      onEdit(comment.id, editText.trim());
    }
    setEditing(false);
  };

  const initials = getInitials(comment.user_id);
  const reactions = comment.reactions ?? {};

  return (
    <div className={depth > 0 ? "ml-8 border-l-2 border-gray-100 pl-3" : ""}>
      <div
        className="group relative py-2"
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        <div className="flex items-start gap-3">
          {/* Avatar */}
          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center text-xs font-semibold">
            {initials}
          </div>

          <div className="flex-1 min-w-0">
            {/* Header */}
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-900">
                {comment.user_id}
              </span>
              <span className="text-xs text-gray-400">
                {relativeTime(comment.timestamp)}
              </span>
            </div>

            {/* Content */}
            {editing ? (
              <div className="mt-1 flex gap-2">
                <textarea
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  className="flex-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500 resize-none"
                  rows={2}
                />
                <div className="flex flex-col gap-1">
                  <Button size="sm" onClick={handleSaveEdit}>
                    Save
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setEditing(false);
                      setEditText(comment.content);
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              <p className="text-sm text-gray-700 mt-0.5">
                {highlightMentions(comment.content)}
              </p>
            )}

            {/* Reactions */}
            <ReactionBar
              reactions={reactions}
              onToggle={(emoji) => onReaction(comment.id, emoji)}
            />

            {/* Actions (visible on hover) */}
            {hovered && !editing && (
              <div className="flex items-center gap-2 mt-1">
                {depth === 0 && (
                  <button
                    onClick={() => onReply(comment.id)}
                    className="text-xs text-gray-500 hover:text-brand-600"
                  >
                    Reply
                  </button>
                )}
                <button
                  onClick={() => {
                    setEditing(true);
                    setEditText(comment.content);
                  }}
                  className="text-xs text-gray-500 hover:text-brand-600"
                >
                  Edit
                </button>
                <button
                  onClick={() => onDelete(comment.id)}
                  className="text-xs text-gray-500 hover:text-red-600"
                >
                  Delete
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Replies (1 level) */}
      {comment.replies.map((reply) => (
        <CommentBubble
          key={reply.id}
          comment={reply}
          onReply={onReply}
          onEdit={onEdit}
          onDelete={onDelete}
          onReaction={onReaction}
          depth={depth + 1}
        />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// MentionInput
// ---------------------------------------------------------------------------

function MentionInput({
  value,
  onChange,
  onSubmit,
  placeholder,
}: {
  value: string;
  onChange: (val: string) => void;
  onSubmit: () => void;
  placeholder: string;
}) {
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [cursorIndex, setCursorIndex] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const text = e.target.value;
    onChange(text);

    // Detect @mention
    const cursor = e.target.selectionStart ?? text.length;
    const before = text.slice(0, cursor);
    const atMatch = before.match(/@(\w*)$/);
    if (atMatch) {
      const query = atMatch[1].toLowerCase();
      const filtered = TEAM_MEMBERS.filter((name) =>
        name.toLowerCase().includes(query)
      );
      setSuggestions(filtered);
      setShowSuggestions(filtered.length > 0);
      setCursorIndex(0);
    } else {
      setShowSuggestions(false);
    }
  };

  const insertMention = (name: string) => {
    const cursor = textareaRef.current?.selectionStart ?? value.length;
    const before = value.slice(0, cursor);
    const after = value.slice(cursor);
    const atIndex = before.lastIndexOf("@");
    const newText = before.slice(0, atIndex) + `@${name} ` + after;
    onChange(newText);
    setShowSuggestions(false);
    textareaRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (showSuggestions) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setCursorIndex((prev) => Math.min(prev + 1, suggestions.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setCursorIndex((prev) => Math.max(prev - 1, 0));
      } else if (e.key === "Enter" || e.key === "Tab") {
        e.preventDefault();
        insertMention(suggestions[cursorIndex]);
      } else if (e.key === "Escape") {
        setShowSuggestions(false);
      }
    } else if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSubmit();
    }
  };

  return (
    <div className="relative">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        rows={2}
        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder-gray-400 focus:ring-2 focus:ring-brand-500 focus:border-brand-500 resize-none"
      />
      {showSuggestions && (
        <div className="absolute bottom-full left-0 mb-1 w-56 bg-white border border-gray-200 rounded-lg shadow-lg z-10 max-h-40 overflow-y-auto">
          {suggestions.map((name, i) => (
            <button
              key={name}
              onClick={() => insertMention(name)}
              className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-50 ${
                i === cursorIndex ? "bg-brand-50 text-brand-700" : "text-gray-700"
              }`}
            >
              <span className="inline-flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center text-xs font-semibold">
                  {getInitials(name)}
                </span>
                {name}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function CommentsTab({ caseId }: CommentsTabProps) {
  const [comments, setComments] = useState<CommentData[]>([]);
  const [newComment, setNewComment] = useState("");
  const [replyTo, setReplyTo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [posting, setPosting] = useState(false);
  const threadRef = useRef<HTMLDivElement>(null);

  // Fetch comments
  const fetchComments = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/cases/${caseId}/comments`);
      if (res.ok) {
        const data: CommentData[] = await res.json();
        setComments(data);
      }
    } catch {
      // silently handle network errors
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    fetchComments();
  }, [fetchComments]);

  // Auto-scroll to bottom on new comments
  useEffect(() => {
    if (threadRef.current) {
      threadRef.current.scrollTop = threadRef.current.scrollHeight;
    }
  }, [comments]);

  const handlePost = async () => {
    if (!newComment.trim()) return;
    setPosting(true);
    try {
      const res = await fetch(`${API_BASE}/cases/${caseId}/comments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: "current-user",
          content: newComment.trim(),
          parent_id: replyTo,
        }),
      });
      if (res.ok) {
        setNewComment("");
        setReplyTo(null);
        await fetchComments();
      }
    } catch {
      // silently handle
    } finally {
      setPosting(false);
    }
  };

  const handleEdit = async (commentId: string, newContent: string) => {
    // Optimistic update for local state
    const updateRecursive = (list: CommentData[]): CommentData[] =>
      list.map((c) => ({
        ...c,
        content: c.id === commentId ? newContent : c.content,
        replies: updateRecursive(c.replies),
      }));
    setComments(updateRecursive(comments));
  };

  const handleDelete = async (commentId: string) => {
    const removeRecursive = (list: CommentData[]): CommentData[] =>
      list
        .filter((c) => c.id !== commentId)
        .map((c) => ({ ...c, replies: removeRecursive(c.replies) }));
    setComments(removeRecursive(comments));
  };

  const handleReaction = (commentId: string, emoji: string) => {
    const toggleRecursive = (list: CommentData[]): CommentData[] =>
      list.map((c) => {
        if (c.id === commentId) {
          const reactions = { ...(c.reactions ?? {}) };
          const users = [...(reactions[emoji] ?? [])];
          const idx = users.indexOf("current-user");
          if (idx >= 0) {
            users.splice(idx, 1);
          } else {
            users.push("current-user");
          }
          reactions[emoji] = users;
          return { ...c, reactions };
        }
        return { ...c, replies: toggleRecursive(c.replies) };
      });
    setComments(toggleRecursive(comments));
  };

  return (
    <div className="flex flex-col h-full">
      {/* Thread area */}
      <div ref={threadRef} className="flex-1 overflow-y-auto p-4 space-y-1">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin h-6 w-6 border-2 border-brand-600 border-t-transparent rounded-full" />
          </div>
        ) : comments.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <p className="text-sm text-gray-500">No comments yet</p>
            <p className="text-xs text-gray-400 mt-1">
              Start a discussion about this case
            </p>
          </div>
        ) : (
          comments.map((comment) => (
            <CommentBubble
              key={comment.id}
              comment={comment}
              onReply={(parentId) => setReplyTo(parentId)}
              onEdit={handleEdit}
              onDelete={handleDelete}
              onReaction={handleReaction}
              depth={0}
            />
          ))
        )}
      </div>

      {/* Input area (always visible at bottom) */}
      <div className="border-t border-gray-200 p-4 bg-white">
        {replyTo && (
          <div className="flex items-center justify-between mb-2 px-2 py-1 bg-gray-50 rounded text-xs text-gray-500">
            <span>Replying to comment</span>
            <button
              onClick={() => setReplyTo(null)}
              className="text-gray-400 hover:text-gray-600"
            >
              Cancel
            </button>
          </div>
        )}
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <MentionInput
              value={newComment}
              onChange={setNewComment}
              onSubmit={handlePost}
              placeholder="Write a comment... Use @ to mention someone"
            />
          </div>
          <Button
            size="sm"
            onClick={handlePost}
            loading={posting}
            disabled={!newComment.trim()}
          >
            Post Comment
          </Button>
        </div>
      </div>
    </div>
  );
}
