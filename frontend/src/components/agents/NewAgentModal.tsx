"use client";

import { useState } from "react";
import Modal from "../ui/Modal";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type SkillPackId =
  | "general"
  | "investigator"
  | "qa_analyst"
  | "compliance"
  | "media_editor"
  | "operations"
  | "executive";

interface SkillPackOption {
  id: SkillPackId;
  label: string;
}

interface NewAgentPayload {
  name: string;
  skill_pack: SkillPackId;
  description: string;
  auto_patrol: boolean;
  workspace_scope: string;
}

interface CreatedAgent {
  id: string;
  name: string;
  skill_pack: string;
  status: string;
  description: string;
  auto_patrol: boolean;
  workspace_scope: string;
  created_at: string;
}

interface NewAgentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: (agent: CreatedAgent) => void;
  workspaces?: { id: string; name: string }[];
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const SKILL_PACKS: SkillPackOption[] = [
  { id: "general", label: "General" },
  { id: "investigator", label: "Investigator" },
  { id: "qa_analyst", label: "QA Analyst" },
  { id: "compliance", label: "Compliance" },
  { id: "media_editor", label: "Media Editor" },
  { id: "operations", label: "Operations" },
  { id: "executive", label: "Executive" },
];

const DEFAULT_WORKSPACES = [
  { id: "all", name: "All Workspaces" },
  { id: "current", name: "Current Workspace" },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function NewAgentModal({
  isOpen,
  onClose,
  onCreated,
  workspaces,
}: NewAgentModalProps) {
  const [name, setName] = useState("");
  const [skillPack, setSkillPack] = useState<SkillPackId>("general");
  const [description, setDescription] = useState("");
  const [autoPatrol, setAutoPatrol] = useState(false);
  const [workspaceScope, setWorkspaceScope] = useState("all");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const scopeOptions = workspaces ?? DEFAULT_WORKSPACES;

  const resetForm = () => {
    setName("");
    setSkillPack("general");
    setDescription("");
    setAutoPatrol(false);
    setWorkspaceScope("all");
    setError(null);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleSubmit = async () => {
    const trimmedName = name.trim();
    if (!trimmedName) {
      setError("Agent name is required.");
      return;
    }

    setSubmitting(true);
    setError(null);

    const payload: NewAgentPayload = {
      name: trimmedName,
      skill_pack: skillPack,
      description: description.trim(),
      auto_patrol: autoPatrol,
      workspace_scope: workspaceScope,
    };

    try {
      const res = await fetch("/api/agents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(
          (body as Record<string, string> | null)?.detail ??
            "Failed to create agent"
        );
      }

      const created: CreatedAgent = await res.json();
      resetForm();
      onCreated(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setSubmitting(false);
    }
  };

  // ---- Render ------------------------------------------------------------

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="New Agent"
      footer={
        <>
          <button
            onClick={handleClose}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting || !name.trim()}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {submitting ? "Creating..." : "Create Agent"}
          </button>
        </>
      }
    >
      <div className="space-y-5">
        {/* Error banner */}
        {error && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Agent Name */}
        <div>
          <label
            htmlFor="agent-name"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Agent Name
          </label>
          <input
            id="agent-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Night-Shift Monitor"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
          />
        </div>

        {/* Skill Pack */}
        <div>
          <span className="block text-sm font-medium text-gray-700 mb-2">
            Skill Pack
          </span>
          <div className="flex flex-wrap gap-2">
            {SKILL_PACKS.map((pack) => (
              <button
                key={pack.id}
                type="button"
                onClick={() => setSkillPack(pack.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  skillPack === pack.id
                    ? "bg-brand-600 text-white"
                    : "bg-gray-50 text-gray-600 hover:bg-gray-100 border border-gray-200"
                }`}
              >
                {pack.label}
              </button>
            ))}
          </div>
        </div>

        {/* Description */}
        <div>
          <label
            htmlFor="agent-description"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Description
          </label>
          <textarea
            id="agent-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            placeholder="What does this agent do?"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent resize-none"
          />
        </div>

        {/* Auto-patrol toggle */}
        <div className="flex items-center justify-between">
          <div>
            <span className="block text-sm font-medium text-gray-700">
              Auto-patrol
            </span>
            <span className="block text-xs text-gray-500">
              Agent runs periodic scans autonomously
            </span>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={autoPatrol}
            onClick={() => setAutoPatrol((prev) => !prev)}
            className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ${
              autoPatrol ? "bg-brand-600" : "bg-gray-200"
            }`}
          >
            <span
              className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition-transform ${
                autoPatrol ? "translate-x-5" : "translate-x-0"
              }`}
            />
          </button>
        </div>

        {/* Workspace scope */}
        <div>
          <label
            htmlFor="workspace-scope"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Workspace Scope
          </label>
          <select
            id="workspace-scope"
            value={workspaceScope}
            onChange={(e) => setWorkspaceScope(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent bg-white"
          >
            {scopeOptions.map((ws) => (
              <option key={ws.id} value={ws.id}>
                {ws.name}
              </option>
            ))}
          </select>
        </div>
      </div>
    </Modal>
  );
}
