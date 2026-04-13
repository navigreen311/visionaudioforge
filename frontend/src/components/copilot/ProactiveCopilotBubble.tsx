"use client";

import { useRouter } from "next/navigation";
import { useProactiveSuggestions } from "@/hooks/useProactiveSuggestions";

export default function ProactiveCopilotBubble() {
  const router = useRouter();
  const { suggestion, dismiss } = useProactiveSuggestions();

  if (!suggestion) return null;

  return (
    <div
      className="fixed left-4 bottom-20 z-[50] max-w-xs animate-slide-in-left bg-white shadow-lg rounded-lg border p-4"
      style={{
        animation: "slideInLeft 0.35s ease-out forwards",
      }}
    >
      <style jsx>{`
        @keyframes slideInLeft {
          from {
            transform: translateX(-100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
      `}</style>

      <div className="flex items-start gap-2">
        <div className="flex-1">
          <p className="text-sm text-gray-700">{suggestion}</p>
          <button
            onClick={() =>
              router.push(
                `/agents?suggestion=${encodeURIComponent(suggestion)}`
              )
            }
            className="mt-2 text-sm font-medium text-blue-600 hover:text-blue-800"
          >
            Ask Copilot
          </button>
        </div>
        <button
          onClick={dismiss}
          className="text-gray-400 hover:text-gray-600 text-lg leading-none"
          aria-label="Dismiss"
        >
          &times;
        </button>
      </div>
    </div>
  );
}
