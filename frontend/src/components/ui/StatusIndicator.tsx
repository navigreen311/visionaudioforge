"use client";

import React from "react";

const statusColors = {
  online: "bg-green-500",
  offline: "bg-gray-400",
  warning: "bg-yellow-500",
};

interface StatusIndicatorProps {
  status: keyof typeof statusColors;
  label?: string;
}

export default function StatusIndicator({ status, label }: StatusIndicatorProps) {
  return (
    <span className="inline-flex items-center gap-2">
      <span className="relative flex h-2.5 w-2.5">
        {status === "online" && (
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
        )}
        <span
          className={`relative inline-flex h-2.5 w-2.5 rounded-full ${statusColors[status]}`}
        />
      </span>
      {label && <span className="text-sm text-gray-700">{label}</span>}
    </span>
  );
}
