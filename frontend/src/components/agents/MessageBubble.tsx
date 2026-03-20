"use client";

interface MessageBubbleProps {
  role: "user" | "assistant" | "tool";
  content: string;
  timestamp?: string;
  toolName?: string;
}

export default function MessageBubble({
  role,
  content,
  timestamp,
  toolName,
}: MessageBubbleProps) {
  const isUser = role === "user";
  const isTool = role === "tool";

  if (isTool) {
    return (
      <div className="flex justify-center my-2">
        <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-2 max-w-lg text-sm">
          <span className="font-medium text-amber-700">Tool: {toolName}</span>
          <p className="text-amber-600 mt-1 whitespace-pre-wrap">{content}</p>
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
