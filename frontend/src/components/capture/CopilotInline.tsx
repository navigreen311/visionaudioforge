"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import Link from "next/link";

interface CopilotInlineProps {
  onSendMessage: (message: string) => void;
  responses: string[];
  isLoading?: boolean;
}

export default function CopilotInline({
  onSendMessage,
  responses,
  isLoading = false,
}: CopilotInlineProps) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const lastThree = responses.slice(-3);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lastThree.length]);

  const handleSend = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;
    onSendMessage(trimmed);
    setInput("");
  }, [input, isLoading, onSendMessage]);

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
    <div className="flex flex-col gap-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide">
          Copilot
        </span>
        <Link
          href="/agents"
          className="text-xs text-brand-600 hover:text-brand-700 hover:underline"
        >
          Open full Copilot
        </Link>
      </div>

      {/* Chat bubbles — last 3 responses */}
      {lastThree.length > 0 && (
        <div className="flex flex-col gap-2 max-h-36 overflow-y-auto">
          {lastThree.map((response, index) => (
            <div
              key={index}
              className="px-3 py-2 bg-white rounded-md border border-gray-100 text-xs text-gray-700 leading-relaxed"
            >
              {response}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      )}

      {/* Loading indicator */}
      {isLoading && (
        <div className="flex items-center gap-2 px-3 py-2">
          <div className="flex gap-1">
            <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
            <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
            <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" />
          </div>
          <span className="text-xs text-gray-400">Thinking...</span>
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
          className="flex-1 px-3 py-1.5 text-sm bg-white border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500 disabled:opacity-50 placeholder:text-gray-400"
        />
        <button
          onClick={handleSend}
          disabled={isLoading || !input.trim()}
          className="px-3 py-1.5 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-md text-sm font-medium transition-colors"
        >
          Send
        </button>
      </div>
    </div>
  );
}
