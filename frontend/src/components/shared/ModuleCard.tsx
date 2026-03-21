"use client";

import Link from "next/link";
import Badge from "@/components/ui/Badge";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ModuleCardProps {
  name: string;
  status: "Active" | "Coming Soon";
  href?: string;
}

// ---------------------------------------------------------------------------
// Arrow icon
// ---------------------------------------------------------------------------

function ArrowRightIcon() {
  return (
    <svg
      className="h-4 w-4 text-gray-400 group-hover:text-[#185FA5] transition-colors flex-shrink-0"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ModuleCard({ name, status, href }: ModuleCardProps) {
  const isActive = status === "Active";

  const content = (
    <div className="flex items-center justify-between w-full">
      <span className="text-sm font-medium text-gray-700">{name}</span>
      <div className="flex items-center gap-2">
        <Badge variant={isActive ? "success" : "neutral"}>{status}</Badge>
        {isActive && <ArrowRightIcon />}
      </div>
    </div>
  );

  if (isActive && href) {
    return (
      <Link
        href={href}
        className="group flex items-center justify-between rounded-lg border border-gray-100 px-4 py-3 transition-colors hover:bg-blue-50 hover:border-[#185FA5]/30"
      >
        {content}
      </Link>
    );
  }

  return (
    <div
      className="relative flex items-center justify-between rounded-lg border border-gray-100 px-4 py-3 cursor-default group"
      title="This module is in development"
    >
      {content}
      {/* Tooltip on hover for Coming Soon modules */}
      <div className="pointer-events-none absolute -top-8 left-1/2 -translate-x-1/2 whitespace-nowrap rounded bg-gray-800 px-2 py-1 text-xs text-white opacity-0 group-hover:opacity-100 transition-opacity z-10">
        Coming soon
      </div>
    </div>
  );
}
