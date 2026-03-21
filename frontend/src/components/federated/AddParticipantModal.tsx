"use client";

import { useState, useCallback } from "react";
import Modal from "@/components/ui/Modal";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AddParticipantModalProps {
  isOpen: boolean;
  onClose: () => void;
  federationId: string;
  onParticipantAdded?: () => void;
}

interface FormState {
  siteId: string;
  siteName: string;
  location: string;
  connectionUrl: string;
}

const INITIAL_FORM: FormState = {
  siteId: "",
  siteName: "",
  location: "",
  connectionUrl: "",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function AddParticipantModal({
  isOpen,
  onClose,
  federationId,
  onParticipantAdded,
}: AddParticipantModalProps) {
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const updateField = (field: keyof FormState, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    if (error) setError("");
  };

  const resetForm = useCallback(() => {
    setForm(INITIAL_FORM);
    setError("");
    setLoading(false);
  }, []);

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleInvite = async () => {
    // Validation
    if (!form.siteId.trim()) {
      setError("Site ID is required");
      return;
    }
    if (!form.siteName.trim()) {
      setError("Site name is required");
      return;
    }
    if (!form.connectionUrl.trim()) {
      setError("Connection URL is required");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const res = await fetch(
        `/api/federated/federations/${federationId}/participants`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            site_id: form.siteId.trim(),
            site_name: form.siteName.trim(),
            location: form.location.trim() || undefined,
            connection_url: form.connectionUrl.trim(),
          }),
        }
      );

      if (!res.ok) {
        const data = (await res.json().catch(() => null)) as Record<
          string,
          string
        > | null;
        throw new Error(data?.detail ?? `Request failed (${res.status})`);
      }

      resetForm();
      onParticipantAdded?.();
      onClose();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to invite participant"
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Add Participant"
      footer={
        <>
          <button
            onClick={handleClose}
            className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={handleInvite}
            disabled={loading}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50 transition-colors"
          >
            {loading ? "Inviting..." : "Invite"}
          </button>
        </>
      }
    >
      <div className="space-y-4">
        {error && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Site ID */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Site ID <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={form.siteId}
            onChange={(e) => updateField("siteId", e.target.value)}
            placeholder="e.g. site-west-01"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
          <p className="mt-1 text-xs text-gray-400">
            Unique identifier for this participant site
          </p>
        </div>

        {/* Site Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Site Name <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={form.siteName}
            onChange={(e) => updateField("siteName", e.target.value)}
            placeholder="e.g. West Campus Lab"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </div>

        {/* Location */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Location{" "}
            <span className="text-gray-400 font-normal">(optional)</span>
          </label>
          <input
            type="text"
            value={form.location}
            onChange={(e) => updateField("location", e.target.value)}
            placeholder="e.g. San Francisco, CA"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </div>

        {/* Connection URL */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Connection URL <span className="text-red-500">*</span>
          </label>
          <input
            type="url"
            value={form.connectionUrl}
            onChange={(e) => updateField("connectionUrl", e.target.value)}
            placeholder="https://site-west-01.example.com:8443"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
          <p className="mt-1 text-xs text-gray-400">
            Endpoint where the participant node is reachable
          </p>
        </div>
      </div>
    </Modal>
  );
}
