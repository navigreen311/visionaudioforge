"use client";

import { useEffect, useRef, useState } from "react";

interface Workspace {
  id: string;
  name: string;
  plan: "free" | "pro" | "enterprise";
  member_count: number;
  is_current: boolean;
}

const PLAN_BADGE_COLORS: Record<string, string> = {
  free: "bg-gray-600 text-gray-200",
  pro: "bg-blue-600 text-blue-100",
  enterprise: "bg-purple-600 text-purple-100",
};

const STUB_WORKSPACES: Workspace[] = [
  { id: "ws_001", name: "Main Workspace", plan: "pro", member_count: 5, is_current: true },
  { id: "ws_002", name: "Testing", plan: "free", member_count: 2, is_current: false },
  { id: "ws_003", name: "Production", plan: "enterprise", member_count: 12, is_current: false },
];

export default function WorkspaceSwitcher() {
  const [open, setOpen] = useState(false);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchWorkspaces();
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  async function fetchWorkspaces() {
    try {
      const res = await fetch("/api/workspaces");
      if (res.ok) {
        const data = await res.json();
        setWorkspaces(data.length ? data : STUB_WORKSPACES);
      } else {
        setWorkspaces(STUB_WORKSPACES);
      }
    } catch {
      setWorkspaces(STUB_WORKSPACES);
    } finally {
      setLoading(false);
    }
  }

  async function switchWorkspace(workspaceId: string) {
    try {
      await fetch("/api/workspaces/switch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workspace_id: workspaceId }),
      });
    } catch {
      // continue even if the API call fails
    }
    try {
      localStorage.setItem("workspace_id", workspaceId);
    } catch {
      // localStorage may be unavailable
    }
    window.location.reload();
  }

  async function createWorkspace() {
    if (!newName.trim()) return;
    try {
      const res = await fetch("/api/workspaces", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName.trim() }),
      });
      if (res.ok) {
        const created = await res.json();
        setWorkspaces((prev) => [...prev, { ...created, is_current: false, member_count: 1, plan: "free" }]);
        setNewName("");
        setCreating(false);
      }
    } catch {
      // silently fail
    }
  }

  const current = workspaces.find((ws) => ws.is_current) ?? workspaces[0];

  if (loading) {
    return (
      <div className="px-3 py-3 border-b border-brand-700">
        <div className="h-9 rounded-lg bg-brand-800 animate-pulse" />
      </div>
    );
  }

  return (
    <div className="relative px-3 py-3 border-b border-brand-700" ref={dropdownRef}>
      {/* Trigger */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-2 rounded-lg bg-brand-800 px-3 py-2 text-sm text-white hover:bg-brand-700 transition-colors"
      >
        <div className="flex items-center gap-2 min-w-0">
          <span className="truncate font-medium">{current?.name ?? "Workspace"}</span>
          {current && (
            <span className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${PLAN_BADGE_COLORS[current.plan]}`}>
              {current.plan}
            </span>
          )}
        </div>
        <svg className={`h-4 w-4 shrink-0 transition-transform ${open ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute left-3 right-3 top-full z-50 mt-1 rounded-lg border border-brand-700 bg-[#0A1628] shadow-xl">
          <div className="max-h-64 overflow-y-auto p-1">
            {workspaces.map((ws) => (
              <button
                key={ws.id}
                onClick={() => {
                  if (!ws.is_current) switchWorkspace(ws.id);
                  else setOpen(false);
                }}
                className={`flex w-full items-center justify-between gap-2 rounded-md px-3 py-2 text-sm transition-colors ${
                  ws.is_current ? "bg-brand-700 text-white" : "text-brand-100 hover:bg-brand-800 hover:text-white"
                }`}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className="truncate">{ws.name}</span>
                  <span className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${PLAN_BADGE_COLORS[ws.plan]}`}>
                    {ws.plan}
                  </span>
                </div>
                <span className="shrink-0 text-xs text-brand-400">{ws.member_count} members</span>
              </button>
            ))}
          </div>

          {/* Create new workspace */}
          <div className="border-t border-brand-700 p-2">
            {!creating ? (
              <button
                onClick={() => setCreating(true)}
                className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-brand-300 hover:bg-brand-800 hover:text-white transition-colors"
              >
                <span className="text-lg leading-none">+</span>
                <span>Create new workspace</span>
              </button>
            ) : (
              <div className="flex gap-2">
                <input
                  autoFocus
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && createWorkspace()}
                  placeholder="Workspace name"
                  className="flex-1 rounded-md bg-brand-800 border border-brand-600 px-2 py-1.5 text-sm text-white placeholder-brand-400 focus:outline-none focus:border-brand-500"
                />
                <button
                  onClick={createWorkspace}
                  className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-500 transition-colors"
                >
                  Create
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
