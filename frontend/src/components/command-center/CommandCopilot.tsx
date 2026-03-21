"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import api from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface CopilotContext {
  active_streams: number;
  open_incidents: number;
  current_zone: string;
  kpis: Record<string, number | string> | null;
}

interface CommandCopilotProps {
  context?: CopilotContext;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MAX_HISTORY = 5;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function CommandCopilot({ context }: CommandCopilotProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isStreaming]);

  const handleClear = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setMessages([]);
    setInput("");
    setIsStreaming(false);
  }, []);

  const handleSend = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;

    const userMessage: ChatMessage = { role: "user", content: trimmed };
    const updatedMessages = [...messages, userMessage].slice(-MAX_HISTORY * 2);

    setMessages(updatedMessages);
    setInput("");
    setIsStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await api.post(
        "/api/agents/chat",
        {
          message: trimmed,
          history: updatedMessages.slice(0, -1),
          context: context ?? null,
        },
        {
          signal: controller.signal,
          responseType: "text",
          headers: { Accept: "text/event-stream" },
        },
      );

      // Handle streamed or non-streamed response
      const text =
        typeof response.data === "string"
          ? response.data
          : JSON.stringify(response.data);

      const assistantMessage: ChatMessage = {
        role: "assistant",
        content: text,
      };

      setMessages((prev) => [...prev, assistantMessage].slice(-MAX_HISTORY * 2));
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "CanceledError") return;

      const fallback: ChatMessage = {
        role: "assistant",
        content: "Sorry, I could not process your request. Please try again.",
      };
      setMessages((prev) => [...prev, fallback].slice(-MAX_HISTORY * 2));
    } finally {
      setIsStreaming(false);
      abortRef.current = null;
    }
  }, [input, isStreaming, messages, context]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900">Copilot</h3>
        {messages.length > 0 && (
          <button
            onClick={handleClear}
            className="rounded px-2 py-0.5 text-[11px] text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          >
            Clear
          </button>
        )}
      </div>

      {/* Scrollable response area */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-3 py-2 space-y-3"
        style={{ minHeight: 120, maxHeight: 300 }}
      >
        {messages.length === 0 && !isStreaming && (
          <div className="flex flex-col items-center justify-center py-8 text-gray-400">
            <svg
              className="h-6 w-6 mb-2"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
              />
            </svg>
            <span className="text-xs">Ask Copilot anything about your operations</span>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] rounded-lg px-3 py-2 text-xs leading-relaxed whitespace-pre-wrap ${
                msg.role === "user"
                  ? "bg-brand-600 text-white"
                  : "bg-gray-100 text-gray-800"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {isStreaming && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg px-3 py-2 flex items-center gap-1">
              <span className="block h-1.5 w-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:0ms]" />
              <span className="block h-1.5 w-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:150ms]" />
              <span className="block h-1.5 w-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:300ms]" />
            </div>
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="border-t border-gray-200 px-3 py-2">
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about operations..."
            disabled={isStreaming}
            className="flex-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={isStreaming || !input.trim()}
            className="flex-shrink-0 rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50 transition-colors"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
