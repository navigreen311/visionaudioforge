"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import dynamic from "next/dynamic";
import CopilotChat from "@/components/agents/CopilotChat";
import MemoryPanel from "@/components/agents/MemoryPanel";
import SkillPackSwitcher from "@/components/agents/SkillPackSwitcher";
import api, { wsBaseUrl } from "@/lib/api";

// AgentSwitcher is the only one of the "AG3+" panels that was both complete and
// missing from the page: agentId was set once to "default-agent" and never
// changed, so the copilot could not be pointed at any other agent even though
// the page was already fetching the list.
//
// The block that used to live here imported five more panels and then wrote
// `void PatrolModePanel;` and so on to silence the unused-variable lint, under a
// comment calling them "wired but not yet rendered". They were not wired: two
// duplicated inline UI this page already renders (patrol mode, conversation
// history) and three needed changes to CopilotChat's API to receive input
// (VoiceInput, LiveContextPanel, MessageActions). Silencing the lint is what let
// the component tree look ~42% larger than the app it renders.
const AgentSwitcher = dynamic(() => import("@/components/agents/AgentSwitcher"), {
  loading: () => <div className="h-24 animate-pulse rounded-xl bg-gray-100" />,
  ssr: false,
});

interface Memory {
  id: string;
  content: string;
  importance_score: number;
  freshness_score: number;
  created_at: string;
}

interface AgentInfo {
  id: string;
  name: string;
  agent_type: string;
  status: string;
  created_at: string;
}

interface PatrolFinding {
  check: string;
  status: "ok" | "warning" | "critical";
  message: string;
  timestamp: string;
}

interface HistoryMessage {
  id: string;
  role: string;
  content: string;
  timestamp: string;
  tool_use?: Record<string, unknown> | null;
}

// Base URL only - CopilotChat appends the session token at connect time, since
// this is module scope and there is no session to read here.
//
// The `||` fallback used to be dead code: `+` binds tighter than `||`, so with
// NEXT_PUBLIC_WS_URL unset this evaluated to the string
// "undefined/ws/agents/stream", which is truthy.
const WS_URL = `${wsBaseUrl()}/ws/agents/stream`;

export default function AgentsPage() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") ?? undefined;

  // Null until an agent is known. This was the literal "default-agent", which
  // is not a UUID, so the first render fired /memory and /patrol/report at a id
  // the database could not parse - two 500s on every visit before the operator
  // touched anything. The server now answers 404 for an unparseable id; the
  // page should not be asking in the first place.
  const [agentId, setAgentId] = useState<string | null>(null);
  const [skillPack, setSkillPack] = useState("general");
  const [memories, setMemories] = useState<Memory[]>([]);
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [memoryLoading, setMemoryLoading] = useState(false);

  // Patrol state
  const [patrolActive, setPatrolActive] = useState(false);
  const [patrolFindings, setPatrolFindings] = useState<PatrolFinding[]>([]);
  const [patrolLoading, setPatrolLoading] = useState(false);

  // Conversation history state
  const [historyMessages, setHistoryMessages] = useState<HistoryMessage[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  const fetchMemories = useCallback(async () => {
    if (!agentId) return;
    try {
      const res = await api.get(`/api/agents/${agentId}/memory`);
      setMemories(res.data);
    } catch {
      setMemories([]);
    }
  }, [agentId]);

  const fetchAgents = useCallback(async () => {
    try {
      const res = await api.get("/api/agents");
      const list: AgentInfo[] = res.data ?? [];
      setAgents(list);
      // Adopt the first real agent so the panels have something to load. The
      // switcher below can change it; until this resolves there is nothing to
      // ask about.
      setAgentId((current) => current ?? list[0]?.id ?? null);
    } catch {
      setAgents([]);
    }
  }, []);

  const fetchPatrolReport = useCallback(async () => {
    if (!agentId) return;
    try {
      const res = await api.get(`/api/agents/${agentId}/patrol/report`);
      setPatrolActive(res.data.is_patrolling ?? false);
      setPatrolFindings(res.data.findings ?? []);
    } catch {
      setPatrolFindings([]);
    }
  }, [agentId]);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await api.get(`/api/agents/${agentId}/history?limit=50`);
      setHistoryMessages(res.data.messages ?? []);
    } catch {
      setHistoryMessages([]);
    }
  }, [agentId]);

  useEffect(() => {
    fetchAgents();
    fetchMemories();
    fetchPatrolReport();
  }, [fetchAgents, fetchMemories, fetchPatrolReport]);

  const handleDeleteMemory = async (memoryId: string) => {
    try {
      await api.delete(`/api/agents/${agentId}/memory/${memoryId}`);
      setMemories((prev) => prev.filter((m) => m.id !== memoryId));
    } catch {
      // ignore
    }
  };

  const handleDecay = async () => {
    setMemoryLoading(true);
    try {
      await api.post(`/api/agents/${agentId}/memory/decay`);
      await fetchMemories();
    } finally {
      setMemoryLoading(false);
    }
  };

  const handleTogglePatrol = async () => {
    setPatrolLoading(true);
    try {
      if (patrolActive) {
        await api.post(`/api/agents/${agentId}/patrol/stop`);
        setPatrolActive(false);
      } else {
        await api.post(`/api/agents/${agentId}/patrol/start`);
        setPatrolActive(true);
      }
      // Refresh findings after a short delay
      setTimeout(() => fetchPatrolReport(), 2000);
    } catch {
      // ignore
    } finally {
      setPatrolLoading(false);
    }
  };

  const handleToggleHistory = async () => {
    if (!showHistory) {
      await fetchHistory();
    }
    setShowHistory((prev) => !prev);
  };

  const handleClearHistory = async () => {
    try {
      await api.delete(`/api/agents/${agentId}/history`);
      setHistoryMessages([]);
    } catch {
      // ignore
    }
  };

  const currentAgent = agents.find((a) => a.id === agentId);

  const statusColor = (s: string) => {
    if (s === "critical") return "text-red-600 bg-red-50";
    if (s === "warning") return "text-amber-600 bg-amber-50";
    return "text-green-600 bg-green-50";
  };

  return (
    <div className="flex gap-6 h-[calc(100vh-6rem)]">
        {/* Every route needs one h1 - it is what a screen reader announces on
            navigation. This shell is full-height by design, so the heading is
            visually hidden rather than laid out. */}
      <h1 className="sr-only">Agent Copilot</h1>

      {/* Main chat area */}
      <div className="flex-1 min-w-0">
        <CopilotChat
          agentId={agentId}
          skillPack={skillPack}
          wsUrl={WS_URL}
          initialMessage={initialQuery}
        />
      </div>

      {/* Sidebar panels */}
      <div className="w-80 shrink-0 space-y-4 overflow-y-auto">
        <AgentSwitcher
          currentAgentId={agentId}
          onSwitch={(agent) => {
            setAgentId(agent.id);
            if (agent.skill_pack) setSkillPack(agent.skill_pack);
          }}
        />

        {/* Agent Info */}
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <h3 className="font-semibold text-gray-900 text-sm mb-3">Agent Info</h3>
          <div className="space-y-2 text-xs text-gray-600">
            <div className="flex justify-between">
              <span>Name</span>
              <span className="font-medium text-gray-900">
                {currentAgent?.name || "Default Copilot"}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Status</span>
              <span className="inline-flex items-center gap-1">
                <span className="w-1.5 h-1.5 bg-green-500 rounded-full" />
                {currentAgent?.status || "active"}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Memories</span>
              <span className="font-medium text-gray-900">{memories.length}</span>
            </div>
            <div className="flex justify-between">
              <span>Skill Pack</span>
              <span className="font-medium text-brand-600">{skillPack}</span>
            </div>
          </div>

          {/* Patrol Mode Toggle */}
          <div className="mt-4 pt-3 border-t border-gray-100">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-gray-700">Patrol Mode</span>
                {patrolActive && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
                    <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                    Patrolling
                  </span>
                )}
              </div>
              <button
                onClick={handleTogglePatrol}
                disabled={patrolLoading}
                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                  patrolActive ? "bg-green-500" : "bg-gray-300"
                } ${patrolLoading ? "opacity-50" : ""}`}
              >
                <span
                  className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                    patrolActive ? "translate-x-4" : "translate-x-0.5"
                  }`}
                />
              </button>
            </div>
          </div>

          {/* Conversation History Toggle */}
          <div className="mt-3 pt-3 border-t border-gray-100">
            <button
              onClick={handleToggleHistory}
              className="w-full text-xs text-brand-600 hover:text-brand-700 font-medium text-left"
            >
              {showHistory ? "Hide" : "Show"} Conversation History
            </button>
          </div>
        </div>

        {/* Patrol Findings Feed */}
        {patrolActive && patrolFindings.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <h3 className="font-semibold text-gray-900 text-sm mb-3">Patrol Findings</h3>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {patrolFindings.slice(0, 10).map((finding, idx) => (
                <div
                  key={`${finding.check}-${idx}`}
                  className={`rounded-lg px-3 py-2 text-xs ${statusColor(finding.status)}`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold uppercase text-[10px]">
                      {finding.status}
                    </span>
                    <span className="text-[10px] opacity-70">
                      {finding.check}
                    </span>
                  </div>
                  <p className="leading-snug">{finding.message}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Conversation History Viewer */}
        {showHistory && (
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-gray-900 text-sm">History</h3>
              <button
                onClick={handleClearHistory}
                className="text-[10px] text-red-500 hover:text-red-700 font-medium"
              >
                Clear
              </button>
            </div>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {historyMessages.length === 0 && (
                <p className="text-xs text-gray-400">No conversation history yet.</p>
              )}
              {historyMessages.map((msg) => (
                <div
                  key={msg.id}
                  className={`rounded-lg px-3 py-2 text-xs ${
                    msg.role === "user"
                      ? "bg-brand-50 text-brand-800"
                      : "bg-gray-50 text-gray-700"
                  }`}
                >
                  <div className="flex items-center justify-between mb-0.5">
                    <span className="font-semibold capitalize text-[10px]">
                      {msg.role}
                    </span>
                    <span className="text-[10px] text-gray-400">
                      {msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : ""}
                    </span>
                  </div>
                  <p className="leading-snug line-clamp-3">{msg.content}</p>
                  {msg.tool_use && (
                    <details className="mt-1">
                      <summary className="text-[10px] text-amber-600 cursor-pointer font-medium">
                        Tool used
                      </summary>
                      <pre className="text-[10px] mt-1 p-1 bg-amber-50 rounded overflow-x-auto">
                        {JSON.stringify(msg.tool_use, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        <SkillPackSwitcher current={skillPack} onChange={setSkillPack} />

        <MemoryPanel
          memories={memories}
          onDelete={handleDeleteMemory}
          onDecay={handleDecay}
          loading={memoryLoading}
        />
      </div>
    </div>
  );
}
