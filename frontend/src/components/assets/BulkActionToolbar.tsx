"use client";

import React, { useState } from "react";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type BulkAction =
  | "delete"
  | "add-tags"
  | "index-search"
  | "export"
  | "add-to-collection";

interface BulkActionToolbarProps {
  selectedCount: number;
  totalCount: number;
  onAction: (action: BulkAction, payload?: string[]) => void;
  onSelectAll: () => void;
  onDeselectAll: () => void;
  onCancel: () => void;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ToolbarButton({
  onClick,
  label,
  variant = "default",
  children,
}: {
  onClick: () => void;
  label: string;
  variant?: "default" | "danger";
  children: React.ReactNode;
}) {
  const base =
    "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2";
  const styles =
    variant === "danger"
      ? `${base} text-red-100 hover:bg-red-500/20 focus:ring-red-400`
      : `${base} text-gray-100 hover:bg-white/10 focus:ring-brand-400`;

  return (
    <button onClick={onClick} className={styles} title={label}>
      {children}
      <span className="hidden sm:inline">{label}</span>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Icons (inline SVGs matching codebase style)
// ---------------------------------------------------------------------------

function TrashIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
      />
    </svg>
  );
}

function TagIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M7 7h.01M7 3h5a1.99 1.99 0 011.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A2 2 0 013 12V7a4 4 0 014-4z"
      />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
      />
    </svg>
  );
}

function DownloadIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
      />
    </svg>
  );
}

function FolderPlusIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 13h6m-3-3v6m-9 1V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"
      />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function BulkActionToolbar({
  selectedCount,
  totalCount,
  onAction,
  onSelectAll,
  onDeselectAll,
  onCancel,
}: BulkActionToolbarProps) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showTagModal, setShowTagModal] = useState(false);
  const [tagInput, setTagInput] = useState("");

  if (selectedCount === 0) return null;

  const allSelected = selectedCount === totalCount && totalCount > 0;

  function handleDelete() {
    setShowDeleteConfirm(false);
    onAction("delete");
  }

  function handleAddTags() {
    const tags = tagInput
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    if (tags.length > 0) {
      onAction("add-tags", tags);
    }
    setTagInput("");
    setShowTagModal(false);
  }

  return (
    <>
      {/* Fixed bottom toolbar */}
      <div className="fixed bottom-0 inset-x-0 z-40 border-t border-gray-700 bg-gray-900 shadow-lg">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          {/* Left: count + select/deselect */}
          <div className="flex items-center gap-3">
            <span className="text-sm font-semibold text-white">
              {selectedCount} selected
            </span>
            <div className="h-4 w-px bg-gray-600" />
            {allSelected ? (
              <button
                onClick={onDeselectAll}
                className="text-sm text-brand-300 hover:text-brand-200 transition-colors"
              >
                Deselect All
              </button>
            ) : (
              <button
                onClick={onSelectAll}
                className="text-sm text-brand-300 hover:text-brand-200 transition-colors"
              >
                Select All
              </button>
            )}
          </div>

          {/* Center: actions */}
          <div className="flex items-center gap-1">
            <ToolbarButton
              onClick={() => setShowDeleteConfirm(true)}
              label="Delete"
              variant="danger"
            >
              <TrashIcon />
            </ToolbarButton>

            <ToolbarButton onClick={() => setShowTagModal(true)} label="Add Tags">
              <TagIcon />
            </ToolbarButton>

            <ToolbarButton onClick={() => onAction("index-search")} label="Index for Search">
              <SearchIcon />
            </ToolbarButton>

            <ToolbarButton onClick={() => onAction("export")} label="Export">
              <DownloadIcon />
            </ToolbarButton>

            <ToolbarButton onClick={() => onAction("add-to-collection")} label="Add to Collection">
              <FolderPlusIcon />
            </ToolbarButton>
          </div>

          {/* Right: cancel */}
          <button
            onClick={onCancel}
            className="inline-flex items-center gap-1 rounded-lg p-2 text-gray-400 hover:bg-white/10 hover:text-white transition-colors"
            title="Cancel selection"
          >
            <CloseIcon />
          </button>
        </div>
      </div>

      {/* Delete confirmation modal */}
      <Modal
        isOpen={showDeleteConfirm}
        onClose={() => setShowDeleteConfirm(false)}
        title="Confirm Delete"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowDeleteConfirm(false)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={handleDelete}>
              Delete {selectedCount} Asset{selectedCount !== 1 ? "s" : ""}
            </Button>
          </>
        }
      >
        <p className="text-sm text-gray-600">
          Are you sure you want to delete{" "}
          <span className="font-semibold text-gray-900">{selectedCount}</span>{" "}
          asset{selectedCount !== 1 ? "s" : ""}? This action cannot be undone.
        </p>
      </Modal>

      {/* Add Tags modal */}
      <Modal
        isOpen={showTagModal}
        onClose={() => {
          setShowTagModal(false);
          setTagInput("");
        }}
        title="Add Tags"
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => {
                setShowTagModal(false);
                setTagInput("");
              }}
            >
              Cancel
            </Button>
            <Button onClick={handleAddTags} disabled={tagInput.trim().length === 0}>
              Add Tags
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <p className="text-sm text-gray-600">
            Add tags to {selectedCount} selected asset{selectedCount !== 1 ? "s" : ""}.
            Separate multiple tags with commas.
          </p>
          <input
            type="text"
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            placeholder="e.g. outdoor, landscape, 2024"
            className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            onKeyDown={(e) => {
              if (e.key === "Enter") handleAddTags();
            }}
            autoFocus
          />
        </div>
      </Modal>
    </>
  );
}
