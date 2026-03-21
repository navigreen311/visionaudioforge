"use client";

import { useState } from "react";

interface StarterPrompt {
  icon: string;
  title: string;
  subtitle: string;
  prompt: string;
}

const STARTER_PROMPTS: StarterPrompt[] = [
  {
    icon: "📡",
    title: "Stream Activity",
    subtitle: "What's happening on my streams?",
    prompt: "What's happening on my streams?",
  },
  {
    icon: "📋",
    title: "Alert Summary",
    subtitle: "Summarize last 24h alerts",
    prompt: "Summarize last 24h alerts",
  },
  {
    icon: "🔍",
    title: "Zone Search",
    subtitle: "Find clips where person entered Zone B",
    prompt: "Find clips where person entered Zone B",
  },
  {
    icon: "🕐",
    title: "Morning Events",
    subtitle: "Show all events from this morning",
    prompt: "Show all events from this morning",
  },
  {
    icon: "🩺",
    title: "Pipeline Health",
    subtitle: "Health status of pipelines?",
    prompt: "Health status of pipelines?",
  },
  {
    icon: "🤖",
    title: "Model Status",
    subtitle: "Which models in production?",
    prompt: "Which models in production?",
  },
  {
    icon: "🖼️",
    title: "Image Analysis",
    subtitle: "Analyze last uploaded image",
    prompt: "Analyze last uploaded image",
  },
  {
    icon: "🎙️",
    title: "Audio Transcription",
    subtitle: "Transcribe most recent audio",
    prompt: "Transcribe most recent audio",
  },
];

interface StarterPromptsProps {
  onSelect: (prompt: string) => void;
  visible: boolean;
}

export default function StarterPrompts({ onSelect, visible }: StarterPromptsProps) {
  const [fadingOut, setFadingOut] = useState(false);

  if (!visible && !fadingOut) return null;

  const handleClick = (prompt: string) => {
    setFadingOut(true);
    onSelect(prompt);
  };

  return (
    <div
      className={`transition-opacity duration-500 ${
        fadingOut ? "opacity-0 pointer-events-none" : "opacity-100"
      }`}
      onTransitionEnd={() => {
        if (fadingOut) setFadingOut(false);
      }}
    >
      <div className="grid grid-cols-2 gap-3 max-w-2xl mx-auto px-4">
        {STARTER_PROMPTS.map((item) => (
          <button
            key={item.title}
            onClick={() => handleClick(item.prompt)}
            className="flex items-start gap-3 rounded-xl border border-gray-200 bg-white p-4 text-left hover:border-brand-300 hover:bg-brand-50 transition-colors group"
          >
            <span className="text-xl flex-shrink-0 mt-0.5">{item.icon}</span>
            <div className="min-w-0">
              <p className="text-sm font-medium text-gray-900 group-hover:text-brand-700 truncate">
                {item.title}
              </p>
              <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">
                {item.subtitle}
              </p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
