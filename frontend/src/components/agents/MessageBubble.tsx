"use client";

import { useState } from "react";

interface MessageBubbleProps {
  role: "user" | "assistant" | "tool";
  content: string;
  timestamp?: string;
  toolName?: string;
  toolInput?: Record<string, unknown>;
  toolResult?: string;
}

function ToolResultCard({
  toolName,
  toolInput,
  toolResult,
}: {
  toolName: string;
  toolInput?: Record<string, unknown>;
  toolResult: string;
}) {
  const [expanded, setExpanded] = useState(false);

  let parsedResult: unknown = null;
  try {
    parsedResult = JSON.parse(toolResult);
  } catch {
    parsedResult = toolResult;
  }

  return (
    <div className="mt-2 bg-white border border-amber-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-3 py-2 text-xs font-medium text-amber-700 hover:bg-amber-50 transition-colors"
      >
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 bg-amber-400 rounded-full" />
          {toolName} result
        </span>
        <span className="text-amber-400">{expanded ? "[-]" : "[+]"}</span>
      </button>
      {expanded && (
        <div className="border-t border-amber-100 px-3 py-2">
          {toolInput && (
            <div className="mb-2">
              <span className="text-[10px] font-semibold text-gray-500 uppercase">Input</span>
              <pre className="text-[11px] text-gray-600 mt-0.5 overflow-x-auto whitespace-pre-wrap">
                {JSON.stringify(toolInput, null, 2)}
              </pre>
            </div>
          )}
          <div>
            <span className="text-[10px] font-semibold text-gray-500 uppercase">Output</span>
            <pre className="text-[11px] text-gray-700 mt-0.5 overflow-x-auto whitespace-pre-wrap max-h-48 overflow-y-auto">
              {typeof parsedResult === "object"
                ? JSON.stringify(parsedResult, null, 2)
                : String(parsedResult)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

export default function MessageBubble({
  role,
  content,
  timestamp,
  toolName,
  toolInput,
  toolResult,
}: MessageBubbleProps) {
  const isUser = role === "user";
  const isTool = role === "tool";

  if (isTool) {
    return (
      <div className="flex justify-center my-2">
        <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-2 max-w-lg text-sm w-full">
          <span className="font-medium text-amber-700">Tool: {toolName}</span>
          <p className="text-amber-600 mt-1 whitespace-pre-wrap">{content}</p>
          {toolResult && toolName && (
            <ToolResultCard
              toolName={toolName}
              toolInput={toolInput}
              toolResult={toolResult}
            />
          )}
        </div>
      </div>
    );
  }

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-brand-600 text-white rounded-br-md"
            : "bg-gray-100 text-gray-900 rounded-bl-md"
        }`}
      >
        <p className="whitespace-pre-wrap text-sm leading-relaxed">{content}</p>
        {timestamp && (
          <p
            className={`text-xs mt-1 ${
              isUser ? "text-brand-100" : "text-gray-400"
            }`}
          >
            {timestamp}
          </p>
        )}
      </div>
    </div>
  );
}
