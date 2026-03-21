"use client";

import { useState, useCallback, type KeyboardEvent } from "react";
import Modal from "@/components/ui/Modal";
import api from "@/lib/api";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface StoreMemoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSaved: () => void;
}

type Category =
  | "Fact"
  | "Decision"
  | "Observation"
  | "Alert"
  | "Preference"
  | "Context"
  | "Custom";

type Scope = "Workspace" | "Global";

const CATEGORIES: Category[] = [
  "Fact",
  "Decision",
  "Observation",
  "Alert",
  "Preference",
  "Context",
  "Custom",
];

/* ------------------------------------------------------------------ */
/* Importance helpers                                                   */
/* ------------------------------------------------------------------ */

function importanceLabel(value: number): string {
  if (value <= 3) return "Low";
  if (value <= 6) return "Medium";
  return "High";
}

function importanceColor(value: number): string {
  if (value <= 3) return "text-gray-500";
  if (value <= 6) return "text-amber-500";
  return "text-green-600";
}

function importanceTrackColor(value: number): string {
  if (value <= 3) return "accent-gray-400";
  if (value <= 6) return "accent-amber-500";
  return "accent-green-600";
}

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export default function StoreMemoryModal({
  isOpen,
  onClose,
  onSaved,
}: StoreMemoryModalProps) {
  const [content, setContent] = useState("");
  const [category, setCategory] = useState<Category>("Fact");
  const [importance, setImportance] = useState(5);
  const [scope, setScope] = useState<Scope>("Workspace");
  const [isPrivate, setIsPrivate] = useState(false);
  const [source, setSource] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState("");
  const [saving, setSaving] = useState(false);

  /* ---- Tag handling ---- */
  const addTag = useCallback(
    (raw: string) => {
      const tag = raw.trim().toLowerCase();
      if (tag && !tags.includes(tag)) {
        setTags((prev) => [...prev, tag]);
      }
      setTagInput("");
    },
    [tags],
  );

  const removeTag = useCallback((tag: string) => {
    setTags((prev) => prev.filter((t) => t !== tag));
  }, []);

  const handleTagKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addTag(tagInput);
    }
    if (e.key === "Backspace" && tagInput === "" && tags.length > 0) {
      setTags((prev) => prev.slice(0, -1));
    }
  };

  /* ---- Reset form ---- */
  const resetForm = useCallback(() => {
    setContent("");
    setCategory("Fact");
    setImportance(5);
    setScope("Workspace");
    setIsPrivate(false);
    setSource("");
    setTags([]);
    setTagInput("");
  }, []);

  /* ---- Submit ---- */
  const handleSave = async () => {
    if (!content.trim()) return;
    setSaving(true);
    try {
      await api.post("/api/memory", {
        content: content.trim(),
        category: category.toLowerCase(),
        importance,
        scope: scope.toLowerCase(),
        is_private: isPrivate,
        source: source.trim() || null,
        tags,
      });
      resetForm();
      onSaved();
      onClose();
    } catch {
      // Error is surfaced by global interceptor / toast
    } finally {
      setSaving(false);
    }
  };

  /* ---- Footer ---- */
  const footer = (
    <>
      <button
        onClick={onClose}
        className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors"
      >
        Cancel
      </button>
      <button
        onClick={handleSave}
        disabled={!content.trim() || saving}
        className="px-4 py-2 text-sm rounded-lg bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-50 transition-colors"
      >
        {saving ? "Saving..." : "Save Memory"}
      </button>
    </>
  );

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Store Memory" footer={footer}>
      <div className="space-y-5">
        {/* Content */}
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Content
          </label>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="What should be remembered?"
            rows={4}
            className="w-full border border-gray-300 rounded-lg p-3 text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500 resize-none"
          />
        </div>

        {/* Category */}
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Category
          </label>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value as Category)}
            className="w-full border border-gray-300 rounded-lg p-2 text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>

        {/* Importance slider */}
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Importance
          </label>
          <div className="flex items-center gap-3">
            <input
              type="range"
              min={1}
              max={10}
              step={1}
              value={importance}
              onChange={(e) => setImportance(Number(e.target.value))}
              className={`flex-1 ${importanceTrackColor(importance)}`}
            />
            <span
              className={`text-sm font-semibold w-20 text-right ${importanceColor(importance)}`}
            >
              {importance} &middot; {importanceLabel(importance)}
            </span>
          </div>
        </div>

        {/* Scope */}
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Scope
          </label>
          <div className="flex gap-2">
            {(["Workspace", "Global"] as Scope[]).map((s) => (
              <button
                key={s}
                onClick={() => setScope(s)}
                className={`px-4 py-2 text-sm rounded-lg border transition-colors ${
                  scope === s
                    ? "bg-brand-600 text-white border-brand-600"
                    : "border-gray-300 text-gray-700 hover:bg-gray-50"
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        {/* Private toggle */}
        <label className="flex items-center gap-2 cursor-pointer">
          <div
            role="switch"
            aria-checked={isPrivate}
            tabIndex={0}
            onClick={() => setIsPrivate(!isPrivate)}
            onKeyDown={(e) => {
              if (e.key === " " || e.key === "Enter") setIsPrivate(!isPrivate);
            }}
            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
              isPrivate ? "bg-brand-600" : "bg-gray-300"
            }`}
          >
            <span
              className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                isPrivate ? "translate-x-4" : "translate-x-1"
              }`}
            />
          </div>
          <span className="text-sm text-gray-700">Private</span>
        </label>

        {/* Source */}
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Source
          </label>
          <input
            value={source}
            onChange={(e) => setSource(e.target.value)}
            placeholder="e.g. user input, agent inference, API..."
            className="w-full border border-gray-300 rounded-lg p-2 text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
          />
        </div>

        {/* Tags */}
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Tags
          </label>
          <div className="flex flex-wrap gap-1.5 border border-gray-300 rounded-lg p-2 min-h-[38px] focus-within:ring-2 focus-within:ring-brand-500 focus-within:border-brand-500">
            {tags.map((tag) => (
              <span
                key={tag}
                className="inline-flex items-center gap-1 bg-gray-100 text-gray-700 text-xs px-2 py-1 rounded-full"
              >
                {tag}
                <button
                  onClick={() => removeTag(tag)}
                  className="text-gray-400 hover:text-gray-600"
                  aria-label={`Remove tag ${tag}`}
                >
                  &times;
                </button>
              </span>
            ))}
            <input
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={handleTagKeyDown}
              onBlur={() => {
                if (tagInput.trim()) addTag(tagInput);
              }}
              placeholder={tags.length === 0 ? "Type and press Enter..." : ""}
              className="flex-1 min-w-[100px] text-sm outline-none bg-transparent"
            />
          </div>
        </div>
      </div>
    </Modal>
  );
}
