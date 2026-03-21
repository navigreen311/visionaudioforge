"use client";

import React, { useState, useCallback } from "react";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Priority = "critical" | "high" | "medium" | "low";
type CaseStatus = "open" | "active" | "under_review" | "closed";

export interface NewCasePayload {
  name: string;
  description: string;
  priority: Priority;
  status: CaseStatus;
  assignee: string;
  tags: string[];
}

interface NewCaseModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (payload: NewCasePayload) => Promise<void>;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PRIORITY_OPTIONS: { value: Priority; label: string; color: string; ring: string }[] = [
  { value: "critical", label: "Critical", color: "bg-red-600 text-white", ring: "ring-red-400" },
  { value: "high", label: "High", color: "bg-amber-500 text-white", ring: "ring-amber-300" },
  { value: "medium", label: "Medium", color: "bg-blue-500 text-white", ring: "ring-blue-300" },
  { value: "low", label: "Low", color: "bg-gray-400 text-white", ring: "ring-gray-300" },
];

const STATUS_OPTIONS: { value: CaseStatus; label: string }[] = [
  { value: "open", label: "Open" },
  { value: "active", label: "Active" },
  { value: "under_review", label: "Under Review" },
  { value: "closed", label: "Closed" },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function NewCaseModal({ isOpen, onClose, onSubmit }: NewCaseModalProps) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<Priority>("medium");
  const [status, setStatus] = useState<CaseStatus>("open");
  const [assignee, setAssignee] = useState("");
  const [tagInput, setTagInput] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const resetForm = useCallback(() => {
    setTitle("");
    setDescription("");
    setPriority("medium");
    setStatus("open");
    setAssignee("");
    setTagInput("");
    setTags([]);
  }, []);

  const handleClose = useCallback(() => {
    resetForm();
    onClose();
  }, [resetForm, onClose]);

  const handleAddTag = useCallback(() => {
    const trimmed = tagInput.trim();
    if (trimmed && !tags.includes(trimmed)) {
      setTags((prev) => [...prev, trimmed]);
    }
    setTagInput("");
  }, [tagInput, tags]);

  const handleRemoveTag = useCallback((tag: string) => {
    setTags((prev) => prev.filter((t) => t !== tag));
  }, []);

  const handleTagKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter" || e.key === ",") {
        e.preventDefault();
        handleAddTag();
      }
      if (e.key === "Backspace" && tagInput === "" && tags.length > 0) {
        setTags((prev) => prev.slice(0, -1));
      }
    },
    [handleAddTag, tagInput, tags.length]
  );

  const handleSubmit = useCallback(async () => {
    if (!title.trim()) return;
    setSubmitting(true);
    try {
      await onSubmit({
        name: title.trim(),
        description: description.trim(),
        priority,
        status,
        assignee: assignee.trim(),
        tags,
      });
      resetForm();
    } finally {
      setSubmitting(false);
    }
  }, [title, description, priority, status, assignee, tags, onSubmit, resetForm]);

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Create New Case"
      footer={
        <>
          <Button variant="secondary" onClick={handleClose}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            loading={submitting}
            disabled={!title.trim()}
          >
            Create Case
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {/* Title */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Title <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g., Intrusion Investigation Alpha"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder-gray-400 focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
            autoFocus
          />
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Description
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe the investigation scope and objectives..."
            rows={3}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder-gray-400 focus:ring-2 focus:ring-brand-500 focus:border-brand-500 resize-none"
          />
        </div>

        {/* Priority */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Priority
          </label>
          <div className="flex gap-2">
            {PRIORITY_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setPriority(opt.value)}
                className={`flex-1 rounded-lg px-3 py-2 text-xs font-semibold transition-all ${
                  opt.color
                } ${
                  priority === opt.value
                    ? `ring-2 ${opt.ring} ring-offset-1 scale-105`
                    : "opacity-60 hover:opacity-80"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Status */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Status
          </label>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as CaseStatus)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500 bg-white"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Assignee */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Assignee
          </label>
          <input
            type="text"
            value={assignee}
            onChange={(e) => setAssignee(e.target.value)}
            placeholder="e.g., John Doe"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder-gray-400 focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
          />
        </div>

        {/* Tags */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Tags
          </label>
          <div className="flex flex-wrap gap-1 min-h-[2.5rem] rounded-lg border border-gray-300 px-2 py-1.5 focus-within:ring-2 focus-within:ring-brand-500 focus-within:border-brand-500">
            {tags.map((tag) => (
              <span
                key={tag}
                className="inline-flex items-center gap-1 rounded-full bg-brand-100 text-brand-700 px-2.5 py-0.5 text-xs font-medium"
              >
                {tag}
                <button
                  type="button"
                  onClick={() => handleRemoveTag(tag)}
                  className="hover:text-brand-900 transition-colors"
                >
                  <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </span>
            ))}
            <input
              type="text"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={handleTagKeyDown}
              onBlur={handleAddTag}
              placeholder={tags.length === 0 ? "Type and press Enter to add tags..." : ""}
              className="flex-1 min-w-[120px] border-none outline-none text-sm placeholder-gray-400 bg-transparent py-0.5"
            />
          </div>
          <p className="text-xs text-gray-400 mt-1">Press Enter or comma to add a tag</p>
        </div>
      </div>
    </Modal>
  );
}
