"use client";

import React, { useState } from "react";

interface WizardStep2Props {
  onNext: (workspaceName: string) => void;
}

export default function WizardStep2({ onNext }: WizardStep2Props) {
  const [name, setName] = useState("My Workspace");

  return (
    <div className="flex flex-col items-center text-center px-6 py-8">
      <h2 className="text-2xl font-bold text-gray-900 mb-2">
        What should we call your workspace?
      </h2>
      <p className="text-gray-500 mb-8">
        You can always change this later in settings.
      </p>

      <div className="w-full max-w-sm mb-10">
        <label
          htmlFor="workspace-name"
          className="block text-sm font-medium text-gray-700 text-left mb-1"
        >
          Workspace name
        </label>
        <input
          id="workspace-name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none transition-colors"
        />
      </div>

      <button
        onClick={() => onNext(name)}
        className="rounded-lg bg-blue-600 px-8 py-3 text-white font-semibold hover:bg-blue-700 transition-colors"
      >
        Continue
      </button>
    </div>
  );
}
