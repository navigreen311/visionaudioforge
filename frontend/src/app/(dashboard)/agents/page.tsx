"use client";

import { useCallback, useEffect, useState } from "react";
import CopilotChat from "@/components/agents/CopilotChat";
import MemoryPanel from "@/components/agents/MemoryPanel";
import SkillPackSwitcher from "@/components/agents/SkillPackSwitcher";
import api from "@/lib/api";

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

const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL?.replace(/^http/, "ws") + "/ws/agents/stream" ||
  "ws://localhost:8000/ws/agents/stream";

export default function AgentsPage() {
  const [agentId, setAgentId] = useState<string>("default-agent");
  const [skillPack, setSkillPack] = useState("general");
  const [memories, setMemories] = useState<Memory[]>([]);
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [memoryLoading, setMemoryLoading] = useState(false);

  const fetchMemories = useCallback(async () => {
    try {
      const res = await api.get(`/api/agents/${agentId}/memory`);
      setMemories(res.data);
    } catch {
      // Agent may not exist yet — that's fine
      setMemories([]);
    }
  }, [agentId]);

  const fetchAgents = useCallback(async () => {
    try {
      const res = await api.get("/api/agents");
      setAgents(res.data);
    } catch {
      setAgents([]);
    }
  }, []);

  useEffect(() => {
    fetchAgents();
    fetchMemories();
  }, [fetchAgents, fetchMemories]);

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

  const currentAgent = agents.find((a) => a.id === agentId);

  return (
    <div className="flex gap-6 h-[calc(100vh-6rem)]">
      {/* Main chat area */}
      <div className="flex-1 min-w-0">
        <CopilotChat
          agentId={agentId}
          skillPack={skillPack}
          wsUrl={WS_URL}
        />
      </div>

      {/* Sidebar panels */}
      <div className="w-80 shrink-0 space-y-4 overflow-y-auto">
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
        </div>

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
