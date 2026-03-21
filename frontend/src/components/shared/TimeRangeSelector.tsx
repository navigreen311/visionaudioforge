"use client";

import React from "react";

const TIME_RANGES = ["Today", "7 days", "30 days"] as const;

type TimeRange = (typeof TIME_RANGES)[number];

interface TimeRangeSelectorProps {
  value: string;
  onChange: (range: string) => void;
}

export default function TimeRangeSelector({ value, onChange }: TimeRangeSelectorProps) {
  return (
    <div className="inline-flex items-center gap-1 rounded-lg bg-gray-50 p-1">
      {TIME_RANGES.map((range: TimeRange) => (
        <button
          key={range}
          type="button"
          onClick={() => onChange(range)}
          className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
            value === range
              ? "bg-[#185FA5] text-white"
              : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          }`}
        >
          {range}
        </button>
      ))}
    </div>
  );
}
