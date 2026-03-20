"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import MessageBubble from "./MessageBubble";

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
  wsUrl: string;
}

export default function CopilotChat({
  agentId,
  skillPack,
  wsUrl,
}: CopilotChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeTool, setActiveTool] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const streamBufferRef = useRef("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const connectWs = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return wsRef.current;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "token") {
        streamBufferRef.current += data.content;
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last && last.role === "assistant") {
            updated[updated.length - 1] = {
              ...last,
              content: streamBufferRef.current,
            };
          } else {
            updated.push({
              id: crypto.randomUUID(),
              role: "assistant",
              content: streamBufferRef.current,
              timestamp: new Date().toLocaleTimeString(),
            });
          }
          return updated;
        });
      } else if (data.type === "tool_use" || data.type === "tool_use_start") {
        setActiveTool(data.tool);
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "tool",
            content: `Using tool: ${data.tool}...`,
            timestamp: new Date().toLocaleTimeString(),
            toolName: data.tool,
          },
        ]);
      } else if (data.type === "tool_result") {
        setActiveTool(null);
        // Show tool result inline
        setMessages((prev) => {
          const updated = [...prev];
          // Find the last tool message and update it with result
          for (let i = updated.length - 1; i >= 0; i--) {
            if (updated[i].role === "tool" && updated[i].toolName === data.tool && !updated[i].toolResult) {
              updated[i] = {
                ...updated[i],
                content: `Tool: ${data.tool} - completed`,
                toolInput: data.input,
                toolResult: typeof data.result === "string" ? data.result : JSON.stringify(data.result),
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
            id: crypto.randomUUID(),
            role: "assistant",
            content: `Error: ${data.content}`,
            timestamp: new Date().toLocaleTimeString(),
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

  const sendMessage = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
      timestamp: new Date().toLocaleTimeString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsStreaming(true);
    streamBufferRef.current = "";

    const ws = connectWs();
    const sendPayload = () => {
      ws!.send(
        JSON.stringify({
          message: trimmed,
          agent_id: agentId,
          skill_pack: skillPack,
        })
      );
    };

    if (ws!.readyState === WebSocket.OPEN) {
      sendPayload();
    } else {
      ws!.onopen = sendPayload;
    }
  }, [input, isStreaming, agentId, skillPack, connectWs]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

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
          />
        ))}

        {/* Streaming / tool indicator */}
        {isStreaming && activeTool && (
          <div className="flex items-center gap-2 text-sm text-amber-600 py-2 px-4">
            <span className="animate-spin inline-block w-4 h-4 border-2 border-amber-400 border-t-transparent rounded-full" />
            Using tool: {activeTool}
          </div>
        )}
        {isStreaming && !activeTool && messages[messages.length - 1]?.role !== "assistant" && (
          <div className="flex items-center gap-2 text-sm text-gray-400 py-2 px-4">
            <span className="animate-pulse">Thinking...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input bar */}
      <div className="border-t border-gray-200 p-4">
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
            onClick={sendMessage}
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
