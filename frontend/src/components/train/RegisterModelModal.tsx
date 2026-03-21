"use client";

import { useState, useCallback } from "react";
import axios from "axios";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface RegisterModelModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRegistered: () => void;
  workspaceId: string;
}

interface FormState {
  name: string;
  version: string;
  backbone: string;
  tags: string[];
  description: string;
  status: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const BACKBONES = [
  "ResNet18",
  "ResNet50",
  "ViT-B/16",
  "EfficientNet-B0",
  "CLIP ViT-B/32",
  "Whisper-Small",
  "Wav2Vec2",
  "CLAP",
] as const;

const STATUSES = [
  "registered",
  "staging",
  "production",
  "shadow",
] as const;

const INITIAL_STATE: FormState = {
  name: "",
  version: "",
  backbone: BACKBONES[0],
  tags: [],
  description: "",
  status: "registered",
};

// ---------------------------------------------------------------------------
// Tag input sub-component
// ---------------------------------------------------------------------------
function TagInput({
  tags,
  onChange,
}: {
  tags: string[];
  onChange: (tags: string[]) => void;
}) {
  const [input, setInput] = useState("");

  const addTag = useCallback(() => {
    const trimmed = input.trim();
    if (trimmed && !tags.includes(trimmed)) {
      onChange([...tags, trimmed]);
    }
    setInput("");
  }, [input, tags, onChange]);

  const removeTag = (tag: string) => {
    onChange(tags.filter((t) => t !== tag));
  };

  return (
    <div>
      <div className="flex flex-wrap gap-1.5 mb-2">
        {tags.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-[#185FA5]/10 text-[#185FA5] text-xs font-medium"
          >
            {tag}
            <button
              type="button"
              onClick={() => removeTag(tag)}
              className="hover:text-red-500 transition-colors"
              aria-label={`Remove tag ${tag}`}
            >
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              addTag();
            }
          }}
          placeholder="Type a tag and press Enter"
          className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#185FA5]/40 focus:border-[#185FA5]"
        />
        <button
          type="button"
          onClick={addTag}
          disabled={!input.trim()}
          className="px-3 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-40 transition-colors"
        >
          Add
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
export default function RegisterModelModal({
  isOpen,
  onClose,
  onRegistered,
  workspaceId,
}: RegisterModelModalProps) {
  const [form, setForm] = useState<FormState>({ ...INITIAL_STATE });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateField = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async () => {
    if (!form.name.trim() || !form.version.trim()) return;

    setSubmitting(true);
    setError(null);
    try {
      await axios.post(`${API_BASE}/api/registry/register`, {
        name: form.name.trim(),
        version: form.version.trim(),
        backbone: form.backbone || null,
        tags: form.tags.length > 0 ? form.tags : null,
        description: form.description.trim() || null,
        status: form.status,
        metrics: {},
        workspace_id: workspaceId,
      });
      setForm({ ...INITIAL_STATE });
      onRegistered();
      onClose();
    } catch (err) {
      console.error("Register model failed", err);
      setError("Failed to register model. Please check backend connectivity.");
    } finally {
      setSubmitting(false);
    }
  };

  const canSubmit = form.name.trim().length > 0 && form.version.trim().length > 0;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Register Model"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleSubmit}
            loading={submitting}
            disabled={!canSubmit}
          >
            Register
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {error && (
          <div className="p-3 rounded-lg bg-red-50 text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Name <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={form.name}
            onChange={(e) => updateField("name", e.target.value)}
            placeholder="e.g. scene-classifier-v2"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#185FA5]/40 focus:border-[#185FA5]"
          />
        </div>

        {/* Version */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Version <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={form.version}
            onChange={(e) => updateField("version", e.target.value)}
            placeholder="e.g. 1.0.0"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#185FA5]/40 focus:border-[#185FA5]"
          />
        </div>

        {/* Backbone */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Backbone
          </label>
          <select
            value={form.backbone}
            onChange={(e) => updateField("backbone", e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#185FA5]/40 focus:border-[#185FA5] bg-white"
          >
            {BACKBONES.map((b) => (
              <option key={b} value={b}>
                {b}
              </option>
            ))}
          </select>
        </div>

        {/* Status */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Status
          </label>
          <select
            value={form.status}
            onChange={(e) => updateField("status", e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#185FA5]/40 focus:border-[#185FA5] bg-white"
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </option>
            ))}
          </select>
        </div>

        {/* Tags */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Tags
          </label>
          <TagInput
            tags={form.tags}
            onChange={(tags) => updateField("tags", tags)}
          />
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Description
          </label>
          <textarea
            value={form.description}
            onChange={(e) => updateField("description", e.target.value)}
            placeholder="Brief description of this model..."
            rows={3}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#185FA5]/40 focus:border-[#185FA5] resize-none"
          />
        </div>
      </div>
    </Modal>
  );
}
