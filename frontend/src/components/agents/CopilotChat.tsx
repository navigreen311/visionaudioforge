"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import MessageBubble from "./MessageBubble";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Message {
  id: string;
  role: "user" | "assistant" | "tool";
  content: string;
  timestamp: string;
  toolName?: string;
  toolInput?: Record<string, unknown>;
  toolResult?: string;
}

interface CopilotChatProps {
  agentId: string;
  skillPack: string;
  /** WebSocket URL — used for WS-based streaming (legacy). */
  wsUrl: string;
  /** HTTP endpoint for SSE streaming (preferred). Defaults to /api/agents/chat/stream */
  httpStreamUrl?: string;
  /** If set, this message is auto-filled and submitted on mount. */
  initialMessage?: string;
  /** Preferred transport. Defaults to "http". */
  transport?: "http" | "ws";
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function generateId(): string {
  return crypto.randomUUID();
}

function timestamp(): string {
  return new Date().toLocaleTimeString();
}

// ---------------------------------------------------------------------------
// Typing Indicator
// ---------------------------------------------------------------------------

function TypingIndicator() {
  return (
    <div className="flex items-center gap-2 py-2 px-4">
      <div className="flex items-center gap-1">
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
      </div>
      <span className="text-sm text-gray-400">Copilot is thinking...</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function CopilotChat({
  agentId,
  skillPack,
  wsUrl,
  httpStreamUrl = "/api/agents/chat/stream",
  initialMessage,
  transport = "http",
}: CopilotChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeTool, setActiveTool] = useState<string | null>(null);

  // Refs
  const wsRef = useRef<WebSocket | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const streamBufferRef = useRef("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // -----------------------------------------------------------------------
  // Auto-scroll
  // -----------------------------------------------------------------------

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // -----------------------------------------------------------------------
  // Cleanup AbortController on unmount
  // -----------------------------------------------------------------------

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
      wsRef.current?.close();
    };
  }, []);

  // -----------------------------------------------------------------------
  // Stop generating
  // -----------------------------------------------------------------------

  const stopGenerating = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    wsRef.current?.close();
    setIsStreaming(false);
    setActiveTool(null);
    streamBufferRef.current = "";
  }, []);

  // -----------------------------------------------------------------------
  // HTTP SSE streaming via fetch + ReadableStream
  // -----------------------------------------------------------------------

  const sendViaHttp = useCallback(
    async (messageText: string) => {
      const controller = new AbortController();
      abortRef.current = controller;
      streamBufferRef.current = "";

      try {
        const res = await fetch(httpStreamUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: messageText,
            agent_id: agentId,
            skill_pack: skillPack,
          }),
          signal: controller.signal,
        });

        if (!res.ok || !res.body) {
          throw new Error(`HTTP ${res.status}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let partialLine = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          partialLine += chunk;

          // Split by newlines to process SSE lines
          const lines = partialLine.split("\n");
          // Keep the last incomplete line for the next iteration
          partialLine = lines.pop() ?? "";

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || !trimmed.startsWith("data: ")) continue;

            const payload = trimmed.slice(6); // Remove "data: "

            // End signal
            if (payload === "[DONE]") {
              setIsStreaming(false);
              setActiveTool(null);
              streamBufferRef.current = "";
              return;
            }

            try {
              const data = JSON.parse(payload) as {
                type: string;
                content?: string;
                tool?: string;
                input?: Record<string, unknown>;
                result?: unknown;
              };

              if (data.type === "token" && data.content) {
                streamBufferRef.current += data.content;
                const buffered = streamBufferRef.current;
                setMessages((prev) => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  if (last && last.role === "assistant") {
                    updated[updated.length - 1] = { ...last, content: buffered };
                  } else {
                    updated.push({
                      id: generateId(),
                      role: "assistant",
                      content: buffered,
                      timestamp: timestamp(),
                    });
                  }
                  return updated;
                });
              } else if (data.type === "tool_use" || data.type === "tool_use_start") {
                setActiveTool(data.tool ?? null);
                setMessages((prev) => [
                  ...prev,
                  {
                    id: generateId(),
                    role: "tool",
                    content: `Using tool: ${data.tool}...`,
                    timestamp: timestamp(),
                    toolName: data.tool,
                  },
                ]);
              } else if (data.type === "tool_result") {
                setActiveTool(null);
                setMessages((prev) => {
                  const updated = [...prev];
                  for (let i = updated.length - 1; i >= 0; i--) {
                    if (
                      updated[i].role === "tool" &&
                      updated[i].toolName === data.tool &&
                      !updated[i].toolResult
                    ) {
                      updated[i] = {
                        ...updated[i],
                        content: `Tool: ${data.tool} - completed`,
                        toolInput: data.input,
                        toolResult:
                          typeof data.result === "string"
                            ? data.result
                            : JSON.stringify(data.result),
                      };
                      break;
                    }
                  }
                  return updated;
                });
              } else if (data.type === "error") {
                setMessages((prev) => [
                  ...prev,
                  {
                    id: generateId(),
                    role: "assistant",
                    content: `Error: ${data.content ?? "Unknown error"}`,
                    timestamp: timestamp(),
                  },
                ]);
              }
            } catch {
              // Skip malformed JSON lines
            }
          }
        }

        // Stream ended without [DONE]
        setIsStreaming(false);
        setActiveTool(null);
        streamBufferRef.current = "";
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === "AbortError") {
          // User cancelled — no error message needed
          return;
        }
        setMessages((prev) => [
          ...prev,
          {
            id: generateId(),
            role: "assistant",
            content: `Connection error: ${err instanceof Error ? err.message : "Unknown error"}`,
            timestamp: timestamp(),
          },
        ]);
        setIsStreaming(false);
        setActiveTool(null);
        streamBufferRef.current = "";
      }
    },
    [httpStreamUrl, agentId, skillPack],
  );

  // -----------------------------------------------------------------------
  // WebSocket transport (legacy)
  // -----------------------------------------------------------------------

  const connectWs = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return wsRef.current;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "token") {
        streamBufferRef.current += data.content;
        const buffered = streamBufferRef.current;
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last && last.role === "assistant") {
            updated[updated.length - 1] = { ...last, content: buffered };
          } else {
            updated.push({
              id: generateId(),
              role: "assistant",
              content: buffered,
              timestamp: timestamp(),
            });
          }
          return updated;
        });
      } else if (data.type === "tool_use" || data.type === "tool_use_start") {
        setActiveTool(data.tool);
        setMessages((prev) => [
          ...prev,
          {
            id: generateId(),
            role: "tool",
            content: `Using tool: ${data.tool}...`,
            timestamp: timestamp(),
            toolName: data.tool,
          },
        ]);
      } else if (data.type === "tool_result") {
        setActiveTool(null);
        setMessages((prev) => {
          const updated = [...prev];
          for (let i = updated.length - 1; i >= 0; i--) {
            if (
              updated[i].role === "tool" &&
              updated[i].toolName === data.tool &&
              !updated[i].toolResult
            ) {
              updated[i] = {
                ...updated[i],
                content: `Tool: ${data.tool} - completed`,
                toolInput: data.input,
                toolResult:
                  typeof data.result === "string"
                    ? data.result
                    : JSON.stringify(data.result),
              };
              break;
            }
          }
          return updated;
        });
      } else if (data.type === "done") {
        setIsStreaming(false);
        setActiveTool(null);
        streamBufferRef.current = "";
      } else if (data.type === "error") {
        setIsStreaming(false);
        setActiveTool(null);
        streamBufferRef.current = "";
        setMessages((prev) => [
          ...prev,
          {
            id: generateId(),
            role: "assistant",
            content: `Error: ${data.content}`,
            timestamp: timestamp(),
          },
        ]);
      }
    };

    ws.onclose = () => {
      setIsStreaming(false);
      setActiveTool(null);
    };

    return ws;
  }, [wsUrl]);

  // -----------------------------------------------------------------------
  // Send message (dispatch to transport)
  // -----------------------------------------------------------------------

  const sendMessage = useCallback(
    (overrideText?: string) => {
      const text = overrideText ?? input.trim();
      if (!text || isStreaming) return;

      const userMsg: Message = {
        id: generateId(),
        role: "user",
        content: text,
        timestamp: timestamp(),
      };
      setMessages((prev) => [...prev, userMsg]);
      if (!overrideText) setInput("");
      setIsStreaming(true);
      streamBufferRef.current = "";

      if (transport === "http") {
        sendViaHttp(text);
      } else {
        const ws = connectWs();
        const sendPayload = () => {
          ws!.send(
            JSON.stringify({
              message: text,
              agent_id: agentId,
              skill_pack: skillPack,
            }),
          );
        };
        if (ws!.readyState === WebSocket.OPEN) {
          sendPayload();
        } else {
          ws!.onopen = sendPayload;
        }
      }
    },
    [input, isStreaming, agentId, skillPack, transport, sendViaHttp, connectWs],
  );

  // -----------------------------------------------------------------------
  // Regenerate: re-send the last user message
  // -----------------------------------------------------------------------

  const handleRegenerate = useCallback(() => {
    if (isStreaming) return;
    // Find the last user message
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "user") {
        // Remove messages after the user message, then re-send
        setMessages((prev) => prev.slice(0, i + 1));
        setIsStreaming(true);
        streamBufferRef.current = "";
        if (transport === "http") {
          sendViaHttp(messages[i].content);
        }
        return;
      }
    }
  }, [isStreaming, messages, transport, sendViaHttp]);

  // -----------------------------------------------------------------------
  // Auto-submit initialMessage on mount
  // -----------------------------------------------------------------------

  const initialSubmittedRef = useRef(false);

  useEffect(() => {
    if (initialMessage && !initialSubmittedRef.current) {
      initialSubmittedRef.current = true;
      setInput(initialMessage);
    }
  }, [initialMessage]);

  useEffect(() => {
    if (
      initialSubmittedRef.current &&
      input === initialMessage &&
      input.trim() &&
      !isStreaming &&
      messages.length === 0
    ) {
      sendMessage();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [input]);

  // -----------------------------------------------------------------------
  // Key handler
  // -----------------------------------------------------------------------

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------

  const showTypingIndicator =
    isStreaming &&
    !activeTool &&
    messages[messages.length - 1]?.role !== "assistant";

  return (
    <div className="flex flex-col h-full bg-white rounded-xl border border-gray-200">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-1">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-gray-400">
              <div className="w-16 h-16 bg-brand-50 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl text-brand-600 font-bold">C</span>
              </div>
              <p className="font-medium text-gray-600">Media Copilot</p>
              <p className="text-sm mt-1">
                Ask me anything about your media, events, or system status.
              </p>
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            role={msg.role}
            content={msg.content}
            timestamp={msg.timestamp}
            toolName={msg.toolName}
            toolInput={msg.toolInput}
            toolResult={msg.toolResult}
            messageId={msg.id}
            agentId={agentId}
            onRegenerate={handleRegenerate}
          />
        ))}

        {/* Tool indicator */}
        {isStreaming && activeTool && (
          <div className="flex items-center gap-2 text-sm text-amber-600 py-2 px-4">
            <span className="animate-spin inline-block w-4 h-4 border-2 border-amber-400 border-t-transparent rounded-full" />
            Using tool: {activeTool}
          </div>
        )}

        {/* Typing indicator */}
        {showTypingIndicator && <TypingIndicator />}

        <div ref={messagesEndRef} />
      </div>

      {/* Input bar */}
      <div className="border-t border-gray-200 p-4">
        {/* Stop generating button */}
        {isStreaming && (
          <div className="flex justify-center mb-3">
            <button
              onClick={stopGenerating}
              className="flex items-center gap-2 px-4 py-1.5 rounded-full border border-gray-300 text-sm text-gray-600 hover:bg-gray-50 hover:border-gray-400 transition-colors"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <rect x="6" y="6" width="12" height="12" rx="2" />
              </svg>
              Stop generating
            </button>
          </div>
        )}

        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask the copilot..."
            rows={1}
            className="flex-1 resize-none rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
            disabled={isStreaming}
          />
          <button
            onClick={() => sendMessage()}
            disabled={isStreaming || !input.trim()}
            className="bg-brand-600 text-white px-4 py-2.5 rounded-lg text-sm font-medium hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
