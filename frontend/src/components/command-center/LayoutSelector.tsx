"use client";

import React, { useState, useRef, useEffect } from "react";
import type { GridLayout } from "@/lib/api";

const layouts: { value: GridLayout; label: string; icon: React.ReactNode }[] = [
  {
    value: "2x2",
    label: "2x2 Grid",
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
        <rect x="1" y="1" width="8" height="8" rx="1" />
        <rect x="11" y="1" width="8" height="8" rx="1" />
        <rect x="1" y="11" width="8" height="8" rx="1" />
        <rect x="11" y="11" width="8" height="8" rx="1" />
      </svg>
    ),
  },
  {
    value: "3x3",
    label: "3x3 Grid",
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
        <rect x="1" y="1" width="5" height="5" rx="0.5" />
        <rect x="7.5" y="1" width="5" height="5" rx="0.5" />
        <rect x="14" y="1" width="5" height="5" rx="0.5" />
        <rect x="1" y="7.5" width="5" height="5" rx="0.5" />
        <rect x="7.5" y="7.5" width="5" height="5" rx="0.5" />
        <rect x="14" y="7.5" width="5" height="5" rx="0.5" />
        <rect x="1" y="14" width="5" height="5" rx="0.5" />
        <rect x="7.5" y="14" width="5" height="5" rx="0.5" />
        <rect x="14" y="14" width="5" height="5" rx="0.5" />
      </svg>
    ),
  },
  {
    value: "4x4",
    label: "4x4 Grid",
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
        {[0, 1, 2, 3].map((r) =>
          [0, 1, 2, 3].map((c) => (
            <rect key={`${r}-${c}`} x={1 + c * 4.75} y={1 + r * 4.75} width="3.5" height="3.5" rx="0.5" />
          ))
        )}
      </svg>
    ),
  },
  {
    value: "1+3",
    label: "1 + 3",
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
        <rect x="1" y="1" width="12" height="18" rx="1" />
        <rect x="14.5" y="1" width="4.5" height="5" rx="0.5" />
        <rect x="14.5" y="7.5" width="4.5" height="5" rx="0.5" />
        <rect x="14.5" y="14" width="4.5" height="5" rx="0.5" />
      </svg>
    ),
  },
  {
    value: "1+5",
    label: "1 + 5",
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
        <rect x="1" y="1" width="12" height="18" rx="1" />
        <rect x="14.5" y="1" width="4.5" height="3" rx="0.5" />
        <rect x="14.5" y="5" width="4.5" height="3" rx="0.5" />
        <rect x="14.5" y="9" width="4.5" height="3" rx="0.5" />
        <rect x="14.5" y="13" width="4.5" height="3" rx="0.5" />
        <rect x="14.5" y="17" width="4.5" height="2" rx="0.5" />
      </svg>
    ),
  },
];

interface LayoutSelectorProps {
  value: GridLayout;
  onChange: (layout: GridLayout) => void;
}

export default function LayoutSelector({ value, onChange }: LayoutSelectorProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const current = layouts.find((l) => l.value === value) || layouts[0];

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm hover:bg-gray-50 transition-colors"
      >
        {current.icon}
        <span className="hidden sm:inline">{current.label}</span>
        <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && (
        <div className="absolute right-0 mt-1 w-44 rounded-lg border border-gray-200 bg-white shadow-lg py-1 z-50">
          {layouts.map((l) => (
            <button
              key={l.value}
              onClick={() => {
                onChange(l.value);
                setOpen(false);
              }}
              className={`flex w-full items-center gap-3 px-3 py-2 text-sm hover:bg-gray-50 ${
                l.value === value ? "bg-brand-50 text-brand-700 font-medium" : "text-gray-700"
              }`}
            >
              {l.icon}
              <span>{l.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
