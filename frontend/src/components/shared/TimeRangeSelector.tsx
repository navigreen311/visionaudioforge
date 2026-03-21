"use client";

import React from "react";

interface TimeRangeOption {
  label: string;
  value: string;
}

const TIME_RANGES: ReadonlyArray<TimeRangeOption> = [
  { label: "Today", value: "1d" },
  { label: "7 days", value: "7d" },
  { label: "30 days", value: "30d" },
] as const;

interface TimeRangeSelectorProps {
  value: string;
  onChange: (range: string) => void;
}

export default function TimeRangeSelector({ value, onChange }: TimeRangeSelectorProps) {
  return (
    <div
      className="inline-flex items-center gap-1 rounded-full bg-gray-100 p-1"
      role="group"
      aria-label="Time range selector"
    >
      {TIME_RANGES.map((range) => {
        const isActive = value === range.value;
        return (
          <button
            key={range.value}
            type="button"
            onClick={() => onChange(range.value)}
            aria-pressed={isActive}
            className={[
              "rounded-full px-3 py-1 text-sm font-medium transition-all duration-150",
              isActive
                ? "bg-[#185FA5] text-white shadow-sm"
                : "text-gray-600 hover:bg-gray-200 hover:text-gray-800",
            ].join(" ")}
          >
            {range.label}
          </button>
        );
      })}
    </div>
  );
}
