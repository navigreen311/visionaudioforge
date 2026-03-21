"use client";

import React, { useCallback, useRef, useState } from "react";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import Modal from "@/components/ui/Modal";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface WorkspaceSettings {
  name: string;
  description: string;
  logoUrl: string | null;
  accentColor: string;
  plan: string;
  limits: {
    apiCalls: { used: number; max: number };
    storage: { used: number; max: number; unit: string };
    members: { used: number; max: number };
  };
  regional: {
    timezone: string;
    language: string;
    dateFormat: string;
    timeFormat: string;
  };
  info: {
    id: string;
    createdAt: string;
    region: string;
  };
}

const DEFAULT_SETTINGS: WorkspaceSettings = {
  name: "My Workspace",
  description: "",
  logoUrl: null,
  accentColor: "#4F46E5",
  plan: "Free",
  limits: {
    apiCalls: { used: 1240, max: 5000 },
    storage: { used: 2.4, max: 5, unit: "GB" },
    members: { used: 1, max: 3 },
  },
  regional: {
    timezone: "UTC",
    language: "en",
    dateFormat: "MM/DD/YYYY",
    timeFormat: "12h",
  },
  info: {
    id: "ws_abc123def456",
    createdAt: "2025-11-01T00:00:00Z",
    region: "us-east-1",
  },
};

const TIMEZONES = [
  "UTC",
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "Europe/London",
  "Europe/Berlin",
  "Asia/Tokyo",
  "Asia/Shanghai",
  "Australia/Sydney",
];

const LANGUAGES = [
  { value: "en", label: "English" },
  { value: "es", label: "Spanish" },
  { value: "fr", label: "French" },
  { value: "de", label: "German" },
  { value: "ja", label: "Japanese" },
  { value: "zh", label: "Chinese" },
];

const DATE_FORMATS = ["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD"];
const TIME_FORMATS = ["12h", "24h"];

// ---------------------------------------------------------------------------
// Progress Bar
// ---------------------------------------------------------------------------

function ProgressBar({ used, max, label }: { used: number; max: number; label: string }) {
  const pct = Math.min((used / max) * 100, 100);
  const isWarning = pct >= 80;
  const barColor = isWarning ? "bg-amber-500" : "bg-brand-600";

  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-sm">
        <span className="text-gray-600">{label}</span>
        <span className="font-medium text-gray-900">
          {used.toLocaleString()} / {max.toLocaleString()}
        </span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
        <div
          className={`h-full rounded-full transition-all ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// GeneralTab
// ---------------------------------------------------------------------------

export default function GeneralTab() {
  const [settings, setSettings] = useState<WorkspaceSettings>(DEFAULT_SETTINGS);
  const [saving, setSaving] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState("");
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const logoInputRef = useRef<HTMLInputElement>(null);

  const update = useCallback(
    <K extends keyof WorkspaceSettings>(key: K, value: WorkspaceSettings[K]) => {
      setSettings((prev) => ({ ...prev, [key]: value }));
    },
    [],
  );

  const updateRegional = useCallback(
    <K extends keyof WorkspaceSettings["regional"]>(
      key: K,
      value: WorkspaceSettings["regional"][K],
    ) => {
      setSettings((prev) => ({
        ...prev,
        regional: { ...prev.regional, [key]: value },
      }));
    },
    [],
  );

  const handleLogoUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    setSettings((prev) => ({ ...prev, logoUrl: url }));
  }, []);

  const handleSaveAll = useCallback(async () => {
    setSaving(true);
    // TODO: call PATCH /api/settings/workspace
    await new Promise((resolve) => setTimeout(resolve, 600));
    setSaving(false);
  }, []);

  const handleExportData = useCallback(async () => {
    // TODO: call POST /api/settings/workspace/export
    alert("Data export initiated. You will receive a download link via email.");
  }, []);

  const handleDeleteWorkspace = useCallback(async () => {
    if (deleteConfirm !== settings.name) return;
    // TODO: call DELETE /api/settings/workspace
    alert("Workspace deletion requested.");
    setShowDeleteModal(false);
    setDeleteConfirm("");
  }, [deleteConfirm, settings.name]);

  return (
    <div className="space-y-6">
      {/* A. Workspace Identity */}
      <Card title="Workspace Identity">
        <div className="space-y-4">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Workspace Name
            </label>
            <input
              type="text"
              value={settings.name}
              onChange={(e) => update("name", e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              rows={3}
              value={settings.description}
              onChange={(e) => update("description", e.target.value)}
              placeholder="What is this workspace for?"
              className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 resize-none"
            />
          </div>

          {/* Logo */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Logo
            </label>
            <div className="flex items-center gap-4">
              <div className="flex h-16 w-16 items-center justify-center overflow-hidden rounded-lg border border-gray-200 bg-gray-50">
                {settings.logoUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={settings.logoUrl}
                    alt="Workspace logo"
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <svg
                    className="h-8 w-8 text-gray-300"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                    />
                  </svg>
                )}
              </div>
              <div>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => logoInputRef.current?.click()}
                >
                  Upload Logo
                </Button>
                <p className="mt-1 text-xs text-gray-500">
                  PNG, JPG up to 2MB. Recommended 256x256px.
                </p>
                <input
                  ref={logoInputRef}
                  type="file"
                  accept="image/png,image/jpeg"
                  onChange={handleLogoUpload}
                  className="hidden"
                />
              </div>
            </div>
          </div>

          {/* Accent Color */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Accent Color
            </label>
            <div className="flex items-center gap-3">
              <input
                type="color"
                value={settings.accentColor}
                onChange={(e) => update("accentColor", e.target.value)}
                className="h-9 w-9 cursor-pointer rounded border border-gray-300"
              />
              <input
                type="text"
                value={settings.accentColor}
                onChange={(e) => update("accentColor", e.target.value)}
                className="w-28 rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>
          </div>
        </div>
      </Card>

      {/* B. Plan & Billing */}
      <Card title="Plan & Billing">
        <div className="space-y-4">
          <div className="flex items-center justify-between rounded-lg border border-gray-200 bg-gray-50 p-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-semibold text-gray-900">
                  {settings.plan} Plan
                </span>
                <Badge variant="info">{settings.plan}</Badge>
              </div>
              <p className="mt-1 text-sm text-gray-500">
                Your current plan and usage limits.
              </p>
            </div>
            <Button variant="primary" size="sm">
              Upgrade
            </Button>
          </div>

          <div className="space-y-3">
            <ProgressBar
              used={settings.limits.apiCalls.used}
              max={settings.limits.apiCalls.max}
              label="API Calls (this month)"
            />
            <ProgressBar
              used={settings.limits.storage.used}
              max={settings.limits.storage.max}
              label={`Storage (${settings.limits.storage.unit})`}
            />
            <ProgressBar
              used={settings.limits.members.used}
              max={settings.limits.members.max}
              label="Team Members"
            />
          </div>
        </div>
      </Card>

      {/* C. Regional */}
      <Card title="Regional Settings">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {/* Timezone */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Timezone
            </label>
            <select
              value={settings.regional.timezone}
              onChange={(e) => updateRegional("timezone", e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              {TIMEZONES.map((tz) => (
                <option key={tz} value={tz}>
                  {tz}
                </option>
              ))}
            </select>
          </div>

          {/* Language */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Language
            </label>
            <select
              value={settings.regional.language}
              onChange={(e) => updateRegional("language", e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              {LANGUAGES.map((lang) => (
                <option key={lang.value} value={lang.value}>
                  {lang.label}
                </option>
              ))}
            </select>
          </div>

          {/* Date Format */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Date Format
            </label>
            <select
              value={settings.regional.dateFormat}
              onChange={(e) => updateRegional("dateFormat", e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              {DATE_FORMATS.map((fmt) => (
                <option key={fmt} value={fmt}>
                  {fmt}
                </option>
              ))}
            </select>
          </div>

          {/* Time Format */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Time Format
            </label>
            <select
              value={settings.regional.timeFormat}
              onChange={(e) => updateRegional("timeFormat", e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              {TIME_FORMATS.map((fmt) => (
                <option key={fmt} value={fmt}>
                  {fmt}
                </option>
              ))}
            </select>
          </div>
        </div>
      </Card>

      {/* D. Workspace Info */}
      <Card title="Workspace Info">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">Workspace ID</span>
            <div className="flex items-center gap-2">
              <code className="rounded bg-gray-100 px-3 py-1 text-sm font-mono text-gray-700">
                {settings.info.id}
              </code>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigator.clipboard.writeText(settings.info.id)}
              >
                Copy
              </Button>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">Created</span>
            <span className="text-sm font-medium text-gray-900">
              {new Date(settings.info.createdAt).toLocaleDateString()}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">Region</span>
            <span className="text-sm font-medium text-gray-900">
              {settings.info.region}
            </span>
          </div>
        </div>
      </Card>

      {/* E. Danger Zone */}
      <Card
        title="Danger Zone"
        className="border-red-200"
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-medium text-gray-900">Export Data</h4>
              <p className="text-sm text-gray-500">
                Download all your workspace data as a ZIP archive.
              </p>
            </div>
            <Button variant="secondary" size="sm" onClick={handleExportData}>
              Export Data
            </Button>
          </div>

          <div className="border-t border-gray-200" />

          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-medium text-red-700">Delete Workspace</h4>
              <p className="text-sm text-gray-500">
                Permanently delete this workspace and all its data.
              </p>
            </div>
            <Button
              variant="danger"
              size="sm"
              onClick={() => setShowDeleteModal(true)}
            >
              Delete Workspace
            </Button>
          </div>
        </div>
      </Card>

      {/* Save All */}
      <div className="flex justify-end">
        <Button variant="primary" size="lg" loading={saving} onClick={handleSaveAll}>
          Save All Changes
        </Button>
      </div>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => {
          setShowDeleteModal(false);
          setDeleteConfirm("");
        }}
        title="Delete Workspace"
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => {
                setShowDeleteModal(false);
                setDeleteConfirm("");
              }}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              disabled={deleteConfirm !== settings.name}
              onClick={handleDeleteWorkspace}
            >
              Delete Permanently
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            This action is <strong>irreversible</strong>. All workspace data, projects,
            API keys, and member access will be permanently deleted.
          </p>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Type <strong>{settings.name}</strong> to confirm
            </label>
            <input
              type="text"
              value={deleteConfirm}
              onChange={(e) => setDeleteConfirm(e.target.value)}
              placeholder={settings.name}
              className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-red-500 focus:outline-none focus:ring-1 focus:ring-red-500"
            />
          </div>
        </div>
      </Modal>
    </div>
  );
}
