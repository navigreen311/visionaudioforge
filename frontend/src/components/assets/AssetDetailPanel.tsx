"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { createPortal } from "react-dom";
import type { Asset } from "@/lib/api";
import { updateAsset, deleteAsset, downloadAssetUrl, indexAsset } from "@/lib/api";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import { formatSize, formatDate } from "./AssetCard";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AssetDetailPanelProps {
  asset: Asset | null;
  isOpen: boolean;
  onClose: () => void;
  onDelete: (id: string) => void;
  onUpdate: (updated: Asset) => void;
}

interface TransformationEntry {
  id: string;
  name: string;
  timestamp: string;
  params?: string;
}

interface UsageReference {
  id: string;
  kind: "pipeline" | "case";
  name: string;
}

// ---------------------------------------------------------------------------
// Collapsible section helper
// ---------------------------------------------------------------------------

function CollapsibleSection({
  title,
  defaultOpen = false,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="border-t border-gray-200 pt-3">
      <button
        type="button"
        className="flex w-full items-center justify-between text-xs font-medium uppercase tracking-wider text-gray-500 hover:text-gray-700"
        onClick={() => setOpen((v) => !v)}
      >
        {title}
        <svg
          className={`h-4 w-4 transition-transform ${open ? "rotate-180" : ""}`}
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
      {open && <div className="mt-2">{children}</div>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function AssetDetailPanel({
  asset,
  isOpen,
  onClose,
  onDelete,
  onUpdate,
}: AssetDetailPanelProps) {
  // -- local state ----------------------------------------------------------
  const [editingFilename, setEditingFilename] = useState(false);
  const [filenameValue, setFilenameValue] = useState("");
  const [tagInput, setTagInput] = useState("");
  const [showTagInput, setShowTagInput] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [indexing, setIndexing] = useState(false);
  const [indexed, setIndexed] = useState(false);

  // Stub data for version history & usage (will come from API later)
  const [versionHistory] = useState<TransformationEntry[]>([]);
  const [usageRefs] = useState<UsageReference[]>([]);

  const panelRef = useRef<HTMLDivElement>(null);
  const tagInputRef = useRef<HTMLInputElement>(null);

  // -- sync local state with prop -------------------------------------------
  useEffect(() => {
    if (asset) {
      setFilenameValue(asset.filename);
      setEditingFilename(false);
      setShowTagInput(false);
      setTagInput("");
      // ASSUMPTION: index status would come from asset; stub to false for now
      setIndexed(false);
    }
  }, [asset]);

  // -- body scroll lock -----------------------------------------------------
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  // -- escape to close ------------------------------------------------------
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose],
  );

  useEffect(() => {
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, handleKeyDown]);

  // -- focus tag input when shown -------------------------------------------
  useEffect(() => {
    if (showTagInput && tagInputRef.current) {
      tagInputRef.current.focus();
    }
  }, [showTagInput]);

  // -- handlers -------------------------------------------------------------

  const handleSaveFilename = async () => {
    if (!asset || filenameValue.trim() === asset.filename) {
      setEditingFilename(false);
      return;
    }
    setSaving(true);
    try {
      const updated = await updateAsset(asset.id, {
        filename: filenameValue.trim(),
      });
      onUpdate(updated);
      setEditingFilename(false);
    } catch {
      // error handling deferred to toast system
    } finally {
      setSaving(false);
    }
  };

  const handleAddTag = async () => {
    if (!asset || !tagInput.trim()) return;
    const newTag = tagInput.trim();
    if (asset.tags.includes(newTag)) {
      setTagInput("");
      return;
    }
    setSaving(true);
    try {
      const updated = await updateAsset(asset.id, {
        tags: [...asset.tags, newTag],
      });
      onUpdate(updated);
      setTagInput("");
      setShowTagInput(false);
    } catch {
      // error handling deferred to toast system
    } finally {
      setSaving(false);
    }
  };

  const handleRemoveTag = async (tag: string) => {
    if (!asset) return;
    setSaving(true);
    try {
      const updated = await updateAsset(asset.id, {
        tags: asset.tags.filter((t) => t !== tag),
      });
      onUpdate(updated);
    } catch {
      // error handling deferred to toast system
    } finally {
      setSaving(false);
    }
  };

  const handleIndex = async () => {
    if (!asset) return;
    setIndexing(true);
    try {
      await indexAsset({
        asset_id: asset.id,
        modality: asset.type,
        content_url: asset.url || "",
      });
      setIndexed(true);
    } catch {
      // error handling deferred to toast system
    } finally {
      setIndexing(false);
    }
  };

  const handleDelete = async () => {
    if (!asset) return;
    if (!confirm("Are you sure you want to delete this asset? This action cannot be undone."))
      return;
    setDeleting(true);
    try {
      await deleteAsset(asset.id);
      onDelete(asset.id);
      onClose();
    } catch {
      // error handling deferred to toast system
    } finally {
      setDeleting(false);
    }
  };

  const handleDownload = () => {
    if (!asset) return;
    const url = downloadAssetUrl(asset.id);
    window.open(url, "_blank");
  };

  // -- guard ----------------------------------------------------------------
  if (!isOpen || !asset) return null;

  // -- determine open-in link -----------------------------------------------
  const openInHref =
    asset.type === "image" || asset.type === "video" ? "/vision" : "/audio";
  const openInLabel =
    asset.type === "image" || asset.type === "video"
      ? "Open in Vision"
      : "Open in Audio";

  // -- render ---------------------------------------------------------------
  return createPortal(
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 transition-opacity"
        onClick={onClose}
      />

      {/* Slide-over panel */}
      <div
        ref={panelRef}
        className="relative ml-auto flex h-full w-full max-w-[400px] flex-col bg-white shadow-xl animate-in slide-in-from-right"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3 shrink-0">
          <h2 className="text-sm font-semibold text-gray-900">Asset Details</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
            aria-label="Close panel"
          >
            <svg
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto">
          {/* A. Preview */}
          <div className="flex items-center justify-center bg-gray-900 p-4 min-h-[200px]">
            {asset.type === "image" && (
              <img
                src={asset.url || asset.thumbnail_url}
                alt={asset.filename}
                className="max-h-[400px] w-full object-contain"
              />
            )}
            {asset.type === "audio" && (
              <div className="w-full px-2">
                <audio src={asset.url} controls className="w-full">
                  Your browser does not support the audio element.
                </audio>
              </div>
            )}
            {asset.type === "video" && (
              <video
                src={asset.url}
                controls
                className="max-h-[400px] w-full object-contain"
              >
                Your browser does not support the video element.
              </video>
            )}
            {!asset.url && !asset.thumbnail_url && (
              <span className="text-sm text-gray-400">No preview available</span>
            )}
          </div>

          {/* B. Metadata */}
          <div className="space-y-4 px-4 py-4">
            {/* Filename (editable) */}
            <div>
              <label className="text-xs font-medium uppercase tracking-wider text-gray-500">
                Filename
              </label>
              {editingFilename ? (
                <div className="mt-1 flex gap-1">
                  <input
                    type="text"
                    value={filenameValue}
                    onChange={(e) => setFilenameValue(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleSaveFilename();
                      if (e.key === "Escape") {
                        setFilenameValue(asset.filename);
                        setEditingFilename(false);
                      }
                    }}
                    className="flex-1 rounded border border-gray-300 px-2 py-1 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                  <Button
                    size="sm"
                    onClick={handleSaveFilename}
                    loading={saving}
                  >
                    Save
                  </Button>
                </div>
              ) : (
                <p
                  className="mt-1 cursor-pointer truncate text-sm text-gray-900 hover:text-brand-600"
                  title="Click to edit"
                  onClick={() => setEditingFilename(true)}
                >
                  {asset.filename}
                </p>
              )}
            </div>

            {/* Details grid */}
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-gray-500">Type</dt>
                <dd>
                  <Badge
                    variant={
                      asset.type === "image"
                        ? "info"
                        : asset.type === "video"
                          ? "success"
                          : "warning"
                    }
                  >
                    {asset.type}
                  </Badge>
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Size</dt>
                <dd className="text-gray-900">{formatSize(asset.size)}</dd>
              </div>
              {(asset.width != null || asset.height != null) && (
                <div className="flex justify-between">
                  <dt className="text-gray-500">Dimensions</dt>
                  <dd className="text-gray-900">
                    {asset.width} x {asset.height}
                  </dd>
                </div>
              )}
              {asset.duration != null && (
                <div className="flex justify-between">
                  <dt className="text-gray-500">Duration</dt>
                  <dd className="text-gray-900">
                    {asset.duration.toFixed(1)}s
                  </dd>
                </div>
              )}
              <div className="flex justify-between">
                <dt className="text-gray-500">Uploaded</dt>
                <dd className="text-gray-900">
                  {formatDate(asset.created_at)}
                </dd>
              </div>
            </dl>

            {/* Tags */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium uppercase tracking-wider text-gray-500">
                  Tags
                </span>
                <button
                  type="button"
                  onClick={() => setShowTagInput((v) => !v)}
                  className="flex items-center gap-0.5 text-xs font-medium text-brand-600 hover:text-brand-700"
                >
                  <svg
                    className="h-3.5 w-3.5"
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
                  Add
                </button>
              </div>

              {showTagInput && (
                <div className="mb-2 flex gap-1">
                  <input
                    ref={tagInputRef}
                    type="text"
                    value={tagInput}
                    onChange={(e) => setTagInput(e.target.value)}
                    placeholder="New tag"
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleAddTag();
                      if (e.key === "Escape") {
                        setShowTagInput(false);
                        setTagInput("");
                      }
                    }}
                    className="flex-1 rounded border border-gray-300 px-2 py-1 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                  <Button size="sm" onClick={handleAddTag} loading={saving}>
                    Add
                  </Button>
                </div>
              )}

              <div className="flex flex-wrap gap-1">
                {asset.tags.length > 0 ? (
                  asset.tags.map((tag) => (
                    <span
                      key={tag}
                      className="group inline-flex items-center gap-1 rounded-full bg-gray-100 px-2.5 py-0.5 text-xs text-gray-700"
                    >
                      {tag}
                      <button
                        type="button"
                        onClick={() => handleRemoveTag(tag)}
                        className="hidden group-hover:inline-flex text-gray-400 hover:text-red-500"
                        aria-label={`Remove tag ${tag}`}
                      >
                        <svg
                          className="h-3 w-3"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M6 18L18 6M6 6l12 12"
                          />
                        </svg>
                      </button>
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-gray-400">No tags</span>
                )}
              </div>
            </div>

            {/* C. Index status */}
            <div className="border-t border-gray-200 pt-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium uppercase tracking-wider text-gray-500">
                  Index Status
                </span>
                {indexed ? (
                  <Badge variant="success">Indexed</Badge>
                ) : (
                  <Badge variant="warning">Not indexed</Badge>
                )}
              </div>
              {!indexed && (
                <Button
                  variant="secondary"
                  size="sm"
                  className="mt-2 w-full"
                  onClick={handleIndex}
                  loading={indexing}
                >
                  Index now
                </Button>
              )}
            </div>

            {/* D. Actions */}
            <div className="space-y-2 border-t border-gray-200 pt-3">
              <span className="text-xs font-medium uppercase tracking-wider text-gray-500">
                Actions
              </span>

              <a
                href={openInHref}
                className="flex w-full items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
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
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                  />
                </svg>
                {openInLabel}
              </a>

              <Button variant="secondary" className="w-full" size="sm">
                Add to Case
              </Button>

              <Button
                variant="secondary"
                className="w-full"
                size="sm"
                onClick={handleDownload}
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
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                  />
                </svg>
                Download
              </Button>

              <Button
                variant="danger"
                className="w-full"
                size="sm"
                onClick={handleDelete}
                loading={deleting}
              >
                Delete
              </Button>
            </div>

            {/* E. Version history (collapsible) */}
            <CollapsibleSection title="Version History">
              {versionHistory.length > 0 ? (
                <ul className="space-y-2">
                  {versionHistory.map((entry) => (
                    <li
                      key={entry.id}
                      className="flex items-center justify-between rounded bg-gray-50 px-3 py-2 text-xs"
                    >
                      <span className="font-medium text-gray-700">
                        {entry.name}
                      </span>
                      <span className="text-gray-400">
                        {formatDate(entry.timestamp)}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-gray-400">
                  No transformations applied yet.
                </p>
              )}
            </CollapsibleSection>

            {/* F. Usage (collapsible) */}
            <CollapsibleSection title="Usage">
              {usageRefs.length > 0 ? (
                <ul className="space-y-2">
                  {usageRefs.map((ref) => (
                    <li
                      key={ref.id}
                      className="flex items-center justify-between rounded bg-gray-50 px-3 py-2 text-xs"
                    >
                      <span className="font-medium text-gray-700">
                        {ref.name}
                      </span>
                      <Badge variant={ref.kind === "pipeline" ? "info" : "success"}>
                        {ref.kind}
                      </Badge>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-gray-400">
                  Not referenced by any pipeline or case.
                </p>
              )}
            </CollapsibleSection>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}
