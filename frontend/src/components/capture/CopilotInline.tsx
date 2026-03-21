"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import Link from "next/link";
import { chatWithCopilot } from "@/lib/api";
import type { ChatMessage } from "@/lib/api";

interface CopilotInlineProps {
  getFrameBase64?: () => string | null;
}

interface DisplayMessage {
  role: "user" | "assistant";
  content: string;
}

export default function CopilotInline({ getFrameBase64 }: CopilotInlineProps) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastFailedMessage, setLastFailedMessage] = useState<string | null>(
    null
  );
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const visibleMessages = messages.slice(-6); // last 3 exchanges (user + assistant)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isLoading) return;

      setError(null);
      setLastFailedMessage(null);

      const userMsg: DisplayMessage = { role: "user", content: trimmed };
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setIsLoading(true);

      try {
        // Build history from existing messages for context
        const history: ChatMessage[] = messages.slice(-6).map((m) => ({
          role: m.role,
          content: m.content,
        }));

        // Append frame context if available
        let messageWithContext = trimmed;
        if (getFrameBase64) {
          const frame = getFrameBase64();
          if (frame) {
            messageWithContext = `[Frame attached: ${frame.slice(0, 50)}...] ${trimmed}`;
          }
        }

        const response = await chatWithCopilot(
          "copilot",
          messageWithContext,
          history
        );
        const assistantMsg: DisplayMessage = {
          role: "assistant",
          content: response.reply,
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } catch (err: unknown) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to get response";
        setError(errorMessage);
        setLastFailedMessage(trimmed);
        // Remove the user message on failure so it can be retried cleanly
        setMessages((prev) => prev.slice(0, -1));
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, messages, getFrameBase64]
  );

  const handleSend = useCallback(() => {
    sendMessage(input);
  }, [input, sendMessage]);

  const handleRetry = useCallback(() => {
    if (lastFailedMessage) {
      sendMessage(lastFailedMessage);
    }
  }, [lastFailedMessage, sendMessage]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  return (
    <div className="flex flex-col gap-3 p-3 bg-gray-900 rounded-lg border border-gray-700">
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
          Copilot
        </span>
        <Link
          href="/agents"
          className="text-xs text-[#185FA5] hover:text-[#1a6dbd] hover:underline transition-colors"
        >
          Open full Copilot
        </Link>
      </div>

      {/* Chat bubbles — last 3 exchanges */}
      {visibleMessages.length > 0 && (
        <div className="flex flex-col gap-1.5 max-h-[200px] overflow-y-auto scrollbar-thin scrollbar-thumb-gray-700">
          {visibleMessages.map((msg, index) => (
            <div
              key={index}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] px-3 py-1.5 rounded-lg text-xs leading-relaxed ${
                  msg.role === "user"
                    ? "bg-[#185FA5] text-white rounded-br-sm"
                    : "bg-gray-800 text-gray-300 border border-gray-700 rounded-bl-sm"
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      )}

      {/* Typing indicator */}
      {isLoading && (
        <div className="flex items-center gap-2 px-3 py-1.5">
          <div className="flex gap-1">
            <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce [animation-delay:-0.3s]" />
            <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce [animation-delay:-0.15s]" />
            <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" />
          </div>
          <span className="text-xs text-gray-500">Thinking...</span>
        </div>
      )}

      {/* Error message with retry */}
      {error && (
        <div className="flex items-center justify-between gap-2 px-3 py-2 bg-red-900/30 border border-red-800/50 rounded-md">
          <span className="text-xs text-red-400 truncate">{error}</span>
          <button
            type="button"
            onClick={handleRetry}
            className="shrink-0 text-xs font-medium text-red-300 hover:text-red-200 underline transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Input */}
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about what's on screen..."
          disabled={isLoading}
          className="flex-1 px-3 py-1.5 text-sm bg-gray-800 text-gray-200 border border-gray-600 rounded-md focus:outline-none focus:ring-1 focus:ring-[#185FA5] focus:border-[#185FA5] disabled:opacity-50 placeholder:text-gray-500"
        />
        <button
          type="button"
          onClick={handleSend}
          disabled={isLoading || !input.trim()}
          className="px-3 py-1.5 bg-[#185FA5] hover:bg-[#14508a] disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-md text-sm font-medium transition-colors"
        >
          Send
        </button>
      </div>
    </div>
  );
}
