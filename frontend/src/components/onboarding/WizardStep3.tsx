"use client";

import React, { useState } from "react";

interface ActionOption {
  id: string;
  label: string;
  description: string;
  route: string;
}

const actions: ActionOption[] = [
  {
    id: "capture",
    label: "Connect a camera",
    description: "Set up live video capture and monitoring",
    route: "/capture",
  },
  {
    id: "assets",
    label: "Upload media",
    description: "Import video or audio files for analysis",
    route: "/assets",
  },
  {
    id: "pipeline",
    label: "Build a pipeline",
    description: "Create automated AI processing workflows",
    route: "/pipeline",
  },
  {
    id: "agents",
    label: "Ask the Copilot",
    description: "Get AI-powered assistance and insights",
    route: "/agents",
  },
];

interface WizardStep3Props {
  onNext: (route: string) => void;
}

export default function WizardStep3({ onNext }: WizardStep3Props) {
  const [selected, setSelected] = useState<string | null>(null);

  const selectedRoute = actions.find((a) => a.id === selected)?.route ?? "/";

  return (
    <div className="flex flex-col items-center text-center px-6 py-8">
      <h2 className="text-2xl font-bold text-gray-900 mb-2">
        Choose your first action
      </h2>
      <p className="text-gray-500 mb-8">
        Pick what you&apos;d like to do first. You can explore everything later.
      </p>

      <div className="grid grid-cols-2 gap-4 w-full max-w-md mb-10">
        {actions.map((action) => (
          <button
            key={action.id}
            onClick={() => setSelected(action.id)}
            className={`flex flex-col items-center justify-center rounded-xl border-2 p-5 text-center transition-colors ${
              selected === action.id
                ? "border-blue-500 bg-blue-50"
                : "border-gray-200 bg-white hover:border-gray-300"
            }`}
          >
            <span className="text-sm font-semibold text-gray-900">
              {action.label}
            </span>
            <span className="mt-1 text-xs text-gray-500">
              {action.description}
            </span>
          </button>
        ))}
      </div>

      <button
        disabled={!selected}
        onClick={() => onNext(selectedRoute)}
        className="rounded-lg bg-blue-600 px-8 py-3 text-white font-semibold hover:bg-blue-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
      >
        Continue
      </button>
    </div>
  );
}
