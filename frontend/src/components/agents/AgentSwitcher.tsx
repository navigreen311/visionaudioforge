"use client";

import { useCallback, useEffect, useRef, useState } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AgentSummary {
  id: string;
  name: string;
  skill_pack: string;
  status: "idle" | "active" | "patrol" | "error";
}

interface AgentDetail extends AgentSummary {
  description: string;
  auto_patrol: boolean;
  workspace_scope: string;
  created_at: string;
}

interface AgentSwitcherProps {
  currentAgentId: string;
  onSwitch: (agent: AgentDetail) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const STATUS_COLORS: Record<AgentSummary["status"], string> = {
  idle: "bg-gray-400",
  active: "bg-green-500",
  patrol: "bg-amber-500",
  error: "bg-red-500",
};

const SKILL_PACK_COLORS: Record<string, string> = {
  general: "bg-blue-100 text-blue-700",
  investigator: "bg-purple-100 text-purple-700",
  qa_analyst: "bg-teal-100 text-teal-700",
  compliance: "bg-orange-100 text-orange-700",
  media_editor: "bg-pink-100 text-pink-700",
  operations: "bg-yellow-100 text-yellow-700",
  executive: "bg-indigo-100 text-indigo-700",
};

function skillPackBadge(pack: string) {
  const color = SKILL_PACK_COLORS[pack] ?? "bg-gray-100 text-gray-600";
  const label = pack
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${color}`}
    >
      {label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function AgentSwitcher({
  currentAgentId,
  onSwitch,
}: AgentSwitcherProps) {
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [currentAgent, setCurrentAgent] = useState<AgentSummary | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // ---- Fetch agent list -------------------------------------------------
  const fetchAgents = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/agents");
      if (!res.ok) throw new Error("Failed to fetch agents");
      const data: AgentSummary[] = await res.json();

      // Ensure "Default Copilot" is always first
      const sorted = [...data].sort((a, b) => {
        if (a.name === "Default Copilot") return -1;
        if (b.name === "Default Copilot") return 1;
        return a.name.localeCompare(b.name);
      });

      setAgents(sorted);

      const match = sorted.find((a) => a.id === currentAgentId);
      if (match) setCurrentAgent(match);
    } catch {
      // Silently fail; agents list stays empty
    } finally {
      setLoading(false);
    }
  }, [currentAgentId]);

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  // ---- Close on outside click -------------------------------------------
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    if (isOpen) document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  // ---- Select handler ----------------------------------------------------
  const handleSelect = async (agent: AgentSummary) => {
    setIsOpen(false);
    setCurrentAgent(agent);

    try {
      const res = await fetch(`/api/agents/${agent.id}`);
      if (!res.ok) throw new Error("Failed to fetch agent details");
      const detail: AgentDetail = await res.json();
      onSwitch(detail);
    } catch {
      // Fallback: build a minimal detail object
      onSwitch({
        ...agent,
        description: "",
        auto_patrol: false,
        workspace_scope: "all",
        created_at: "",
      });
    }
  };

  // ---- Render ------------------------------------------------------------
  const displayName = currentAgent?.name ?? "Media Copilot";
  const displayPack = currentAgent?.skill_pack ?? "general";

  return (
    <div ref={dropdownRef} className="relative inline-block text-left">
      {/* Trigger */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex items-center gap-2 rounded-lg bg-white px-3 py-2 text-left shadow-sm border border-gray-200 hover:bg-gray-50 transition-colors min-w-[200px]"
      >
        <div className="flex-1 truncate">
          <span className="block text-sm font-semibold text-gray-900 truncate">
            {displayName}
          </span>
          <span className="block mt-0.5">{skillPackBadge(displayPack)}</span>
        </div>
        <svg
          className={`h-4 w-4 text-gray-400 transition-transform ${isOpen ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute left-0 z-30 mt-1 w-72 origin-top-left rounded-lg bg-white shadow-lg ring-1 ring-black/5">
          <div className="max-h-64 overflow-y-auto py-1">
            {loading && (
              <div className="px-4 py-3 text-sm text-gray-400">Loading...</div>
            )}
            {!loading && agents.length === 0 && (
              <div className="px-4 py-3 text-sm text-gray-400">
                No agents found
              </div>
            )}
            {agents.map((agent) => {
              const isSelected = agent.id === currentAgentId;
              return (
                <button
                  key={agent.id}
                  onClick={() => handleSelect(agent)}
                  className={`flex w-full items-center gap-3 px-4 py-2.5 text-left hover:bg-gray-50 transition-colors ${
                    isSelected ? "bg-brand-50" : ""
                  }`}
                >
                  {/* Status dot */}
                  <span
                    className={`inline-block h-2 w-2 flex-shrink-0 rounded-full ${STATUS_COLORS[agent.status]}`}
                    title={agent.status}
                  />

                  {/* Agent info */}
                  <div className="flex-1 min-w-0">
                    <span className="block text-sm font-medium text-gray-900 truncate">
                      {agent.name}
                    </span>
                    <span className="mt-0.5 block">
                      {skillPackBadge(agent.skill_pack)}
                    </span>
                  </div>

                  {/* Selected indicator */}
                  {isSelected && (
                    <svg
                      className="h-4 w-4 text-brand-600 flex-shrink-0"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                  )}
                </button>
              );
            })}
          </div>

          {/* "+ New Agent" action */}
          <div className="border-t border-gray-100">
            <button
              onClick={() => {
                setIsOpen(false);
                // Dispatch a custom event the parent can listen for to open the modal
                window.dispatchEvent(new CustomEvent("open-new-agent-modal"));
              }}
              className="flex w-full items-center gap-2 px-4 py-2.5 text-sm font-medium text-brand-600 hover:bg-brand-50 transition-colors rounded-b-lg"
            >
              <svg
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 4v16m8-8H4"
                />
              </svg>
              New Agent
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
