"use client";

import { API_BASE_URL } from "@/lib/api";

import React, { useState, useRef, useCallback } from "react";
import axios from "axios";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";

const API_BASE = API_BASE_URL;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type EvidenceType =
  | "alert"
  | "capture_frame"
  | "audio_clip"
  | "uploaded_file"
  | "text_note";

interface EvidenceTypeOption {
  value: EvidenceType;
  label: string;
  description: string;
}

const EVIDENCE_TYPES: EvidenceTypeOption[] = [
  { value: "alert", label: "Alert", description: "Link a recent alert to this case" },
  { value: "capture_frame", label: "Capture Frame", description: "Attach a captured video frame" },
  { value: "audio_clip", label: "Audio Clip", description: "Attach an audio recording segment" },
  { value: "uploaded_file", label: "Uploaded File", description: "Upload a file as evidence" },
  { value: "text_note", label: "Text Note", description: "Add a free-text note" },
];

interface MockAlert {
  id: string;
  name: string;
  timestamp: string;
  severity: number;
}

const MOCK_RECENT_ALERTS: MockAlert[] = [
  { id: "a1b2c3d4-0001-4000-a000-000000000001", name: "Perimeter breach detected — Zone A", timestamp: "2026-03-20T08:12:00Z", severity: 5 },
  { id: "a1b2c3d4-0002-4000-a000-000000000002", name: "Unusual audio pattern — Server Room", timestamp: "2026-03-19T22:45:00Z", severity: 3 },
  { id: "a1b2c3d4-0003-4000-a000-000000000003", name: "Motion anomaly — Parking Lot B", timestamp: "2026-03-19T14:30:00Z", severity: 4 },
  { id: "a1b2c3d4-0004-4000-a000-000000000004", name: "Access denied — Badge reader 7", timestamp: "2026-03-18T09:00:00Z", severity: 2 },
];

interface AddEvidenceModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  onAdded: () => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function nowLocalDatetime(): string {
  const d = new Date();
  const offset = d.getTimezoneOffset();
  const local = new Date(d.getTime() - offset * 60000);
  return local.toISOString().slice(0, 16);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function AddEvidenceModal({
  isOpen,
  onClose,
  caseId,
  onAdded,
}: AddEvidenceModalProps) {
  const [evidenceType, setEvidenceType] = useState<EvidenceType>("alert");
  const [description, setDescription] = useState("");
  const [timestamp, setTimestamp] = useState(nowLocalDatetime());
  const [severity, setSeverity] = useState(3);
  const [submitting, setSubmitting] = useState(false);

  // Alert-specific
  const [selectedAlertId, setSelectedAlertId] = useState("");

  // File-specific
  const [fileName, setFileName] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Text note
  const [noteText, setNoteText] = useState("");

  const resetForm = useCallback(() => {
    setEvidenceType("alert");
    setDescription("");
    setTimestamp(nowLocalDatetime());
    setSeverity(3);
    setSelectedAlertId("");
    setFileName(null);
    setNoteText("");
  }, []);

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      setFileName(files[0].name);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      setFileName(files[0].name);
    }
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const payload: Record<string, unknown> = {
        type: evidenceType,
        description:
          evidenceType === "text_note"
            ? noteText || description
            : description,
        timestamp: new Date(timestamp).toISOString(),
        severity,
      };

      if (evidenceType === "alert" && selectedAlertId) {
        payload.alert_id = selectedAlertId;
      }

      if (evidenceType === "text_note") {
        payload.content = noteText || description;
      }

      await axios.post(
        `${API_BASE}/api/investigate/cases/${caseId}/events`,
        payload
      );

      resetForm();
      onAdded();
      onClose();
    } catch {
      // Silently handle — in production would show error toast
    } finally {
      setSubmitting(false);
    }
  };

  const canSubmit = (): boolean => {
    if (evidenceType === "alert" && !selectedAlertId) return false;
    if (evidenceType === "text_note" && !noteText.trim()) return false;
    if (
      (evidenceType === "uploaded_file" ||
        evidenceType === "capture_frame" ||
        evidenceType === "audio_clip") &&
      !fileName
    )
      return false;
    if (!description.trim() && evidenceType !== "text_note") return false;
    return true;
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Add Evidence to Case"
      footer={
        <>
          <Button variant="secondary" onClick={handleClose}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            loading={submitting}
            disabled={!canSubmit()}
          >
            Add to Case
          </Button>
        </>
      }
    >
      <div className="space-y-5">
        {/* Evidence type selector */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Evidence Type
          </label>
          <div className="grid grid-cols-2 gap-2">
            {EVIDENCE_TYPES.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setEvidenceType(opt.value)}
                className={`text-left rounded-lg border p-3 transition-all ${
                  evidenceType === opt.value
                    ? "border-brand-500 bg-brand-50 ring-1 ring-brand-500"
                    : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                }`}
              >
                <p className="text-sm font-medium text-gray-900">
                  {opt.label}
                </p>
                <p className="text-xs text-gray-500 mt-0.5">
                  {opt.description}
                </p>
              </button>
            ))}
          </div>
        </div>

        {/* Type-specific inputs */}
        {evidenceType === "alert" && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Select Alert
            </label>
            <select
              value={selectedAlertId}
              onChange={(e) => setSelectedAlertId(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
            >
              <option value="">Choose a recent alert...</option>
              {MOCK_RECENT_ALERTS.map((alert) => (
                <option key={alert.id} value={alert.id}>
                  [{alert.severity}/5] {alert.name} —{" "}
                  {new Date(alert.timestamp).toLocaleString()}
                </option>
              ))}
            </select>
          </div>
        )}

        {(evidenceType === "capture_frame" ||
          evidenceType === "audio_clip" ||
          evidenceType === "uploaded_file") && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              File
            </label>
            <div
              onDrop={handleFileDrop}
              onDragOver={(e) => e.preventDefault()}
              onClick={() => fileInputRef.current?.click()}
              className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 p-6 cursor-pointer hover:border-brand-400 hover:bg-brand-50/30 transition-colors"
            >
              {fileName ? (
                <div className="text-center">
                  <p className="text-sm font-medium text-gray-900">
                    {fileName}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Click or drag to replace
                  </p>
                </div>
              ) : (
                <div className="text-center">
                  <svg
                    className="mx-auto h-8 w-8 text-gray-400 mb-2"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                    />
                  </svg>
                  <p className="text-sm text-gray-600">
                    Drop a file here or click to browse
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    Images, audio, documents up to 50 MB
                  </p>
                </div>
              )}
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                onChange={handleFileSelect}
                accept={
                  evidenceType === "audio_clip"
                    ? "audio/*"
                    : evidenceType === "capture_frame"
                    ? "image/*"
                    : "*/*"
                }
              />
            </div>
          </div>
        )}

        {evidenceType === "text_note" && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Note Content
            </label>
            <textarea
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              placeholder="Write your observation, analysis, or notes..."
              rows={4}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder-gray-400 focus:ring-2 focus:ring-brand-500 focus:border-brand-500 resize-none"
            />
          </div>
        )}

        {/* Timestamp */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Timestamp
          </label>
          <input
            type="datetime-local"
            value={timestamp}
            onChange={(e) => setTimestamp(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
          />
          <p className="text-xs text-gray-400 mt-1">
            Defaults to current time
          </p>
        </div>

        {/* Description (not shown for text_note since it has its own textarea) */}
        {evidenceType !== "text_note" && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description of this evidence..."
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder-gray-400 focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
            />
          </div>
        )}

        {/* Severity */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Severity ({severity}/5)
          </label>
          <input
            type="range"
            min={1}
            max={5}
            value={severity}
            onChange={(e) => setSeverity(Number(e.target.value))}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-gray-400 mt-0.5">
            <span>Low</span>
            <span>Critical</span>
          </div>
        </div>
      </div>
    </Modal>
  );
}
