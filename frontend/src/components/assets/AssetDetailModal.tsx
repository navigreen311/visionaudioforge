"use client";

import React, { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import type { Asset } from "@/lib/api";
import { updateAsset, deleteAsset, downloadAssetUrl } from "@/lib/api";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import { formatSize, formatDate } from "./AssetCard";

interface AssetDetailModalProps {
  asset: Asset | null;
  onClose: () => void;
  onDeleted: () => void;
  onUpdated: () => void;
}

export default function AssetDetailModal({
  asset,
  onClose,
  onDeleted,
  onUpdated,
}: AssetDetailModalProps) {
  const [editingTags, setEditingTags] = useState(false);
  const [tagInput, setTagInput] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [savingTags, setSavingTags] = useState(false);

  useEffect(() => {
    if (asset) {
      setTagInput(asset.tags.join(", "));
      setEditingTags(false);
    }
  }, [asset]);

  useEffect(() => {
    if (asset) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [asset]);

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (asset) window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [asset, onClose]);

  if (!asset) return null;

  const handleSaveTags = async () => {
    setSavingTags(true);
    try {
      const newTags = tagInput
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      await updateAsset(asset.id, { tags: newTags });
      setEditingTags(false);
      onUpdated();
    } catch {
      // Toast could show error
    } finally {
      setSavingTags(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm("Are you sure you want to delete this asset?")) return;
    setDeleting(true);
    try {
      await deleteAsset(asset.id);
      onDeleted();
      onClose();
    } catch {
      // Toast could show error
    } finally {
      setDeleting(false);
    }
  };

  const handleDownload = () => {
    const url = downloadAssetUrl(asset.id);
    window.open(url, "_blank");
  };

  const typeBadgeVariant: Record<string, "info" | "success" | "warning"> = {
    image: "info",
    video: "success",
    audio: "warning",
  };

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Overlay */}
      <div className="fixed inset-0 bg-black/60" onClick={onClose} />

      {/* Panel - wider for detail view */}
      <div className="relative z-10 w-full max-w-4xl max-h-[90vh] rounded-lg bg-white shadow-xl mx-4 overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4 shrink-0">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-gray-900 truncate max-w-md">
              {asset.filename}
            </h2>
            <Badge variant={typeBadgeVariant[asset.type] ?? "neutral"}>
              {asset.type}
            </Badge>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto">
          <div className="flex flex-col lg:flex-row">
            {/* Media preview */}
            <div className="flex-1 flex items-center justify-center bg-gray-900 min-h-[300px] p-4">
              {asset.type === "image" && (
                <img
                  src={asset.url || asset.thumbnail_url}
                  alt={asset.filename}
                  className="max-w-full max-h-[60vh] object-contain cursor-zoom-in"
                  onClick={(e) => {
                    const img = e.currentTarget;
                    if (img.style.maxHeight) {
                      img.style.maxHeight = "";
                      img.style.maxWidth = "";
                      img.style.cursor = "zoom-out";
                    } else {
                      img.style.maxHeight = "60vh";
                      img.style.maxWidth = "100%";
                      img.style.cursor = "zoom-in";
                    }
                  }}
                />
              )}
              {asset.type === "video" && (
                <video
                  src={asset.url}
                  controls
                  className="max-w-full max-h-[60vh]"
                >
                  Your browser does not support the video element.
                </video>
              )}
              {asset.type === "audio" && (
                <div className="flex flex-col items-center gap-6 w-full max-w-md">
                  {/* Waveform visualization placeholder */}
                  <div className="w-full h-24 flex items-end justify-center gap-0.5">
                    {Array.from({ length: 60 }).map((_, i) => {
                      const h = 20 + Math.sin(i * 0.5) * 40 + Math.random() * 20;
                      return (
                        <div
                          key={i}
                          className="w-1 bg-brand-500 rounded-full opacity-70"
                          style={{ height: `${h}%` }}
                        />
                      );
                    })}
                  </div>
                  <audio src={asset.url} controls className="w-full">
                    Your browser does not support the audio element.
                  </audio>
                </div>
              )}
              {!asset.url && !asset.thumbnail_url && (
                <div className="text-gray-400 text-sm">No preview available</div>
              )}
            </div>

            {/* Metadata panel */}
            <div className="w-full lg:w-80 border-t lg:border-t-0 lg:border-l border-gray-200 p-6 space-y-5 shrink-0">
              <div>
                <h4 className="text-xs font-medium uppercase tracking-wider text-gray-500 mb-2">
                  Details
                </h4>
                <dl className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Filename</dt>
                    <dd className="text-gray-900 text-right truncate max-w-[180px]" title={asset.filename}>
                      {asset.filename}
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Type</dt>
                    <dd className="text-gray-900 capitalize">{asset.type}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Size</dt>
                    <dd className="text-gray-900">{formatSize(asset.size)}</dd>
                  </div>
                  {(asset.width || asset.height) && (
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
                      <dd className="text-gray-900">{asset.duration.toFixed(1)}s</dd>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Created</dt>
                    <dd className="text-gray-900">{formatDate(asset.created_at)}</dd>
                  </div>
                </dl>
              </div>

              {/* Tags */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-xs font-medium uppercase tracking-wider text-gray-500">
                    Tags
                  </h4>
                  <button
                    onClick={() => {
                      if (editingTags) {
                        handleSaveTags();
                      } else {
                        setEditingTags(true);
                      }
                    }}
                    className="text-xs text-brand-600 hover:text-brand-700 font-medium"
                  >
                    {editingTags ? (savingTags ? "Saving..." : "Save") : "Edit"}
                  </button>
                </div>
                {editingTags ? (
                  <input
                    type="text"
                    value={tagInput}
                    onChange={(e) => setTagInput(e.target.value)}
                    placeholder="tag1, tag2, tag3"
                    className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleSaveTags();
                    }}
                  />
                ) : (
                  <div className="flex flex-wrap gap-1">
                    {asset.tags.length > 0 ? (
                      asset.tags.map((tag) => (
                        <span
                          key={tag}
                          className="inline-flex rounded-full bg-gray-100 px-2.5 py-0.5 text-xs text-gray-700"
                        >
                          {tag}
                        </span>
                      ))
                    ) : (
                      <span className="text-sm text-gray-400">No tags</span>
                    )}
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="space-y-2 pt-2 border-t border-gray-200">
                <Button variant="secondary" className="w-full" onClick={handleDownload}>
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Download
                </Button>

                {asset.type === "image" && (
                  <a
                    href="/vision"
                    className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                    Analyze (Vision)
                  </a>
                )}

                {asset.type === "audio" && (
                  <a
                    href="/audio"
                    className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2z" />
                    </svg>
                    Analyze (Audio)
                  </a>
                )}

                <Button variant="secondary" className="w-full">
                  Add to Case
                </Button>

                <Button
                  variant="danger"
                  className="w-full"
                  onClick={handleDelete}
                  loading={deleting}
                >
                  Delete Asset
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}
