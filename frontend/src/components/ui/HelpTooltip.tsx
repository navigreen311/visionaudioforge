"use client";

import React, { useState } from "react";

interface HelpTooltipProps {
  content: string;
  children?: React.ReactNode;
}

export default function HelpTooltip({ content, children }: HelpTooltipProps) {
  const [show, setShow] = useState(false);

  return (
    <span
      className="relative inline-flex items-center"
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      {children ?? (
        <svg
          className="h-4 w-4 cursor-help text-gray-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      )}

      {show && (
        <span className="absolute bottom-full left-1/2 z-50 mb-2 -translate-x-1/2 rounded bg-gray-800 p-2 text-xs text-white max-w-xs whitespace-normal shadow-lg">
          {content}
        </span>
      )}
    </span>
  );
}
