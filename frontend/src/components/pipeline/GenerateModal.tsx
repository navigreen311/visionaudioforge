"use client";

import { useState } from "react";

import api from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface GeneratedPipeline {
  nodes: Array<Record<string, unknown>>;
  edges: Array<Record<string, unknown>>;
}

interface GenerateModalProps {
  isOpen: boolean;
  onClose: () => void;
  onGenerated: (pipeline: GeneratedPipeline) => void;
}

// ---------------------------------------------------------------------------
// Example chips
// ---------------------------------------------------------------------------

const EXAMPLE_PROMPTS = [
  "Detect objects in camera feed and send alert",
  "Extract text from screen captures every 5 seconds",
  "Monitor audio for gunshots and trigger webhook",
  "Capture video, resize frames, export as MP4",
  "Aggregate daily metrics and email a report",
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function GenerateModal({
  isOpen,
  onClose,
  onGenerated,
}: GenerateModalProps) {
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleGenerate = async () => {
    const trimmed = description.trim();
    if (!trimmed) return;

    setLoading(true);
    setError(null);

    try {
      const { data } = await api.post("/api/agents/chat", {
        agent_id: "pipeline_generator",
        message: trimmed,
        history: [],
      });

      let parsed: GeneratedPipeline | null = null;

      try {
        const reply: string = data.reply ?? "";
        const jsonMatch = reply.match(/\{[\s\S]*\}/);
        if (jsonMatch) {
          const obj = JSON.parse(jsonMatch[0]) as Record<string, unknown>;
          if (Array.isArray(obj.nodes)) {
            parsed = {
              nodes: obj.nodes as Array<Record<string, unknown>>,
              edges: (obj.edges as Array<Record<string, unknown>>) ?? [],
            };
          }
        }
      } catch {
        // JSON parse failed
      }

      // Fallback: structured definition
      if (!parsed && data.definition) {
        parsed = data.definition as GeneratedPipeline;
      }

      if (parsed && parsed.nodes.length > 0) {
        onGenerated(parsed);
        setDescription("");
        onClose();
      } else {
        setError(
          "Could not generate a valid pipeline from that description. Try being more specific."
        );
      }
    } catch {
      setError("Generation request failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleChipClick = (prompt: string) => {
    setDescription(prompt);
  };

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-800">
            Generate Pipeline from Description
          </h2>
          <button
            onClick={() => {
              onClose();
              setError(null);
            }}
            className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4">
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe what you want your pipeline to do..."
            rows={4}
            className="w-full border border-gray-300 rounded-lg p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-purple-400 focus:border-purple-400"
            disabled={loading}
          />

          {/* Example chips */}
          <div>
            <p className="text-xs text-gray-400 mb-2">Try an example:</p>
            <div className="flex flex-wrap gap-2">
              {EXAMPLE_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => handleChipClick(prompt)}
                  disabled={loading}
                  className="px-2.5 py-1 text-xs text-purple-700 bg-purple-50 hover:bg-purple-100 rounded-full transition-colors disabled:opacity-50"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          {/* Loading indicator */}
          {loading && (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <svg
                className="animate-spin h-4 w-4 text-purple-500"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
                />
              </svg>
              Generating pipeline...
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-200">
          <button
            onClick={() => {
              onClose();
              setError(null);
            }}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
            disabled={loading}
          >
            Cancel
          </button>
          <button
            onClick={handleGenerate}
            disabled={loading || !description.trim()}
            className="px-4 py-2 text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 rounded-md disabled:opacity-50 transition-colors"
          >
            {loading ? "Generating..." : "Generate Pipeline"}
          </button>
        </div>
      </div>
    </div>
  );
}
