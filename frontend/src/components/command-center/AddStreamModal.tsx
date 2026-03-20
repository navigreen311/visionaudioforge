"use client";

import React, { useState } from "react";
import Modal from "@/components/ui/Modal";
import type { StreamSourceType, AddStreamPayload } from "@/lib/api";
import { addStream } from "@/lib/api";

interface AddStreamModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAdded?: () => void;
  totalSlots: number;
  usedPositions: number[];
}

export default function AddStreamModal({
  isOpen,
  onClose,
  onAdded,
  totalSlots,
  usedPositions,
}: AddStreamModalProps) {
  const [name, setName] = useState("");
  const [sourceType, setSourceType] = useState<StreamSourceType>("camera");
  const [url, setUrl] = useState("");
  const [position, setPosition] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const availablePositions = Array.from({ length: totalSlots }, (_, i) => i).filter(
    (p) => !usedPositions.includes(p)
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError("Name is required");
      return;
    }
    if (sourceType === "rtsp" && !url.trim()) {
      setError("RTSP URL is required");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const payload: AddStreamPayload = {
        name: name.trim(),
        source_type: sourceType,
        position,
      };
      if (sourceType === "rtsp") payload.url = url.trim();
      await addStream(payload);
      setName("");
      setUrl("");
      setSourceType("camera");
      setPosition(0);
      onAdded?.();
      onClose();
    } catch {
      setError("Failed to add stream. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Add Stream"
      footer={
        <>
          <button
            onClick={onClose}
            className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {loading ? "Adding..." : "Add Stream"}
          </button>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Stream Name
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Front Entrance Camera"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Source Type
          </label>
          <div className="flex gap-2">
            {(["camera", "rtsp", "screen"] as StreamSourceType[]).map((st) => (
              <button
                key={st}
                type="button"
                onClick={() => setSourceType(st)}
                className={`flex-1 rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                  sourceType === st
                    ? "border-brand-500 bg-brand-50 text-brand-700"
                    : "border-gray-300 text-gray-600 hover:bg-gray-50"
                }`}
              >
                {st === "camera" ? "Camera" : st === "rtsp" ? "RTSP" : "Screen"}
              </button>
            ))}
          </div>
        </div>

        {sourceType === "rtsp" && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              RTSP URL
            </label>
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="rtsp://..."
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Grid Position
          </label>
          <select
            value={position}
            onChange={(e) => setPosition(Number(e.target.value))}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          >
            {availablePositions.map((p) => (
              <option key={p} value={p}>
                Slot {p + 1}
              </option>
            ))}
            {availablePositions.length === 0 && (
              <option value={0}>No slots available</option>
            )}
          </select>
        </div>
      </form>
    </Modal>
  );
}
