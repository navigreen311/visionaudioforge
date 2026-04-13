"use client";

import React from "react";

interface WizardStep1Props {
  onNext: () => void;
}

export default function WizardStep1({ onNext }: WizardStep1Props) {
  return (
    <div className="flex flex-col items-center text-center px-6 py-8">
      <h2 className="text-2xl font-bold text-gray-900 mb-2">
        Welcome to VisionAudioForge!
      </h2>
      <p className="text-gray-500 mb-8">
        Let&apos;s get you set up in under 2 minutes
      </p>

      <ul className="space-y-4 text-left w-full max-w-sm mb-10">
        <li className="flex items-start gap-3">
          <span className="mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-100 text-blue-600 text-sm font-semibold">
            1
          </span>
          <span className="text-gray-700">
            <strong>AI Analysis</strong> &mdash; Automatically analyze video and
            audio with state-of-the-art models
          </span>
        </li>
        <li className="flex items-start gap-3">
          <span className="mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-100 text-blue-600 text-sm font-semibold">
            2
          </span>
          <span className="text-gray-700">
            <strong>Live Monitoring</strong> &mdash; Watch streams in real-time
            with intelligent alerts
          </span>
        </li>
        <li className="flex items-start gap-3">
          <span className="mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-100 text-blue-600 text-sm font-semibold">
            3
          </span>
          <span className="text-gray-700">
            <strong>Intelligent Automation</strong> &mdash; Build pipelines that
            react to what they see and hear
          </span>
        </li>
      </ul>

      <button
        onClick={onNext}
        className="rounded-lg bg-blue-600 px-8 py-3 text-white font-semibold hover:bg-blue-700 transition-colors"
      >
        Let&apos;s go
      </button>
    </div>
  );
}
