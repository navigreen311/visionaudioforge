"use client";

import React, { useCallback, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import { useToast } from "@/components/ui/Toast";
import {
  testNotificationChannel,
  saveNotificationChannel,
  type NotificationChannelConfig,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Severity = "critical" | "warning" | "info";

interface HeaderRow {
  id: string;
  key: string;
  value: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function generateId(): string {
  return Math.random().toString(36).substring(2, 9);
}

const SEVERITY_OPTIONS: { value: Severity; label: string; color: string }[] = [
  { value: "critical", label: "Critical", color: "bg-red-100 text-red-800 border-red-300" },
  { value: "warning", label: "Warning", color: "bg-yellow-100 text-yellow-800 border-yellow-300" },
  { value: "info", label: "Info", color: "bg-blue-100 text-blue-800 border-blue-300" },
];

const VARIABLE_HINTS = [
  "{{alert.message}}",
  "{{alert.severity}}",
  "{{alert.timestamp}}",
  "{{alert.rule_name}}",
  "{{alert.metric}}",
  "{{alert.value}}",
  "{{alert.threshold}}",
];

const inputClass =
  "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500";

// ---------------------------------------------------------------------------
// Severity Toggle Group
// ---------------------------------------------------------------------------

function SeverityToggles({
  selected,
  onChange,
}: {
  selected: Severity[];
  onChange: (next: Severity[]) => void;
}) {
  const toggle = (sev: Severity) => {
    if (selected.includes(sev)) {
      onChange(selected.filter((s) => s !== sev));
    } else {
      onChange([...selected, sev]);
    }
  };

  return (
    <div className="flex flex-wrap gap-2">
      {SEVERITY_OPTIONS.map((opt) => {
        const active = selected.includes(opt.value);
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => toggle(opt.value)}
            className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
              active
                ? opt.color
                : "border-gray-200 bg-gray-50 text-gray-400"
            }`}
          >
            <span
              className={`inline-block h-2 w-2 rounded-full ${
                active ? "bg-current" : "bg-gray-300"
              }`}
            />
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Email Tag Input
// ---------------------------------------------------------------------------

function EmailTagInput({
  emails,
  onChange,
}: {
  emails: string[];
  onChange: (next: string[]) => void;
}) {
  const [inputValue, setInputValue] = useState("");

  const addEmail = useCallback(
    (raw: string) => {
      const trimmed = raw.trim();
      if (trimmed && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed) && !emails.includes(trimmed)) {
        onChange([...emails, trimmed]);
      }
      setInputValue("");
    },
    [emails, onChange],
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === "," || e.key === "Tab") {
      e.preventDefault();
      addEmail(inputValue);
    }
    if (e.key === "Backspace" && inputValue === "" && emails.length > 0) {
      onChange(emails.slice(0, -1));
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-2 focus-within:border-brand-500 focus-within:ring-1 focus-within:ring-brand-500">
      {emails.map((email) => (
        <span
          key={email}
          className="inline-flex items-center gap-1 rounded-full bg-brand-100 px-2.5 py-0.5 text-xs font-medium text-brand-800"
        >
          {email}
          <button
            type="button"
            onClick={() => onChange(emails.filter((e) => e !== email))}
            className="ml-0.5 text-brand-600 hover:text-brand-900"
          >
            <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </span>
      ))}
      <input
        type="text"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={() => addEmail(inputValue)}
        placeholder={emails.length === 0 ? "Add email addresses..." : ""}
        className="min-w-[120px] flex-1 border-none bg-transparent p-0 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-0"
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Slack Channel Card
// ---------------------------------------------------------------------------

function SlackChannelCard() {
  const { addToast } = useToast();
  const [webhookUrl, setWebhookUrl] = useState("");
  const [channelName, setChannelName] = useState("");
  const [severities, setSeverities] = useState<Severity[]>(["critical", "warning"]);

  const buildConfig = useCallback(
    (): NotificationChannelConfig => ({
      type: "slack",
      enabled: true,
      severity_filter: severities,
      slack: { webhook_url: webhookUrl, channel_name: channelName },
    }),
    [webhookUrl, channelName, severities],
  );

  const testMutation = useMutation({
    mutationFn: () => testNotificationChannel(buildConfig()),
    onSuccess: (res) => addToast("success", res.message),
    onError: () => addToast("error", "Slack test failed"),
  });

  const saveMutation = useMutation({
    mutationFn: () => saveNotificationChannel(buildConfig()),
    onSuccess: () => addToast("success", "Slack channel saved"),
    onError: () => addToast("error", "Failed to save Slack channel"),
  });

  return (
    <Card
      title="Slack"
      className="flex flex-col"
      footer={
        <div className="flex items-center justify-between gap-2">
          <Button
            variant="secondary"
            size="sm"
            loading={testMutation.isPending}
            onClick={() => testMutation.mutate()}
          >
            Test
          </Button>
          <Button
            size="sm"
            loading={saveMutation.isPending}
            onClick={() => saveMutation.mutate()}
          >
            Save
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Webhook URL
          </label>
          <input
            type="url"
            value={webhookUrl}
            onChange={(e) => setWebhookUrl(e.target.value)}
            placeholder="https://hooks.slack.com/services/..."
            className={inputClass}
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Channel Name
          </label>
          <input
            type="text"
            value={channelName}
            onChange={(e) => setChannelName(e.target.value)}
            placeholder="#alerts"
            className={inputClass}
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Severity Filter
          </label>
          <SeverityToggles selected={severities} onChange={setSeverities} />
        </div>
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Email Channel Card
// ---------------------------------------------------------------------------

function EmailChannelCard() {
  const { addToast } = useToast();
  const [recipients, setRecipients] = useState<string[]>([]);
  const [subjectPrefix, setSubjectPrefix] = useState("[ALERT]");
  const [severities, setSeverities] = useState<Severity[]>(["critical", "warning"]);

  const buildConfig = useCallback(
    (): NotificationChannelConfig => ({
      type: "email",
      enabled: true,
      severity_filter: severities,
      email: { recipients, subject_prefix: subjectPrefix },
    }),
    [recipients, subjectPrefix, severities],
  );

  const testMutation = useMutation({
    mutationFn: () => testNotificationChannel(buildConfig()),
    onSuccess: (res) => addToast("success", res.message),
    onError: () => addToast("error", "Email test failed"),
  });

  const saveMutation = useMutation({
    mutationFn: () => saveNotificationChannel(buildConfig()),
    onSuccess: () => addToast("success", "Email channel saved"),
    onError: () => addToast("error", "Failed to save Email channel"),
  });

  return (
    <Card
      title="Email"
      className="flex flex-col"
      footer={
        <div className="flex items-center justify-between gap-2">
          <Button
            variant="secondary"
            size="sm"
            loading={testMutation.isPending}
            onClick={() => testMutation.mutate()}
          >
            Test
          </Button>
          <Button
            size="sm"
            loading={saveMutation.isPending}
            onClick={() => saveMutation.mutate()}
          >
            Save
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Recipients
          </label>
          <EmailTagInput emails={recipients} onChange={setRecipients} />
          <p className="mt-1 text-xs text-gray-500">
            Press Enter or comma to add an email
          </p>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Subject Prefix
          </label>
          <input
            type="text"
            value={subjectPrefix}
            onChange={(e) => setSubjectPrefix(e.target.value)}
            placeholder="[ALERT]"
            className={inputClass}
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Severity Filter
          </label>
          <SeverityToggles selected={severities} onChange={setSeverities} />
        </div>
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Webhook Channel Card
// ---------------------------------------------------------------------------

function WebhookChannelCard() {
  const { addToast } = useToast();
  const [postUrl, setPostUrl] = useState("");
  const [headers, setHeaders] = useState<HeaderRow[]>([
    { id: generateId(), key: "Content-Type", value: "application/json" },
  ]);
  const [payloadTemplate, setPayloadTemplate] = useState(
    JSON.stringify(
      {
        text: "{{alert.message}}",
        severity: "{{alert.severity}}",
        timestamp: "{{alert.timestamp}}",
      },
      null,
      2,
    ),
  );
  const [severities, setSeverities] = useState<Severity[]>(["critical", "warning"]);

  const buildConfig = useCallback((): NotificationChannelConfig => {
    const headersObj: Record<string, string> = {};
    for (const h of headers) {
      if (h.key.trim()) {
        headersObj[h.key.trim()] = h.value;
      }
    }
    return {
      type: "webhook",
      enabled: true,
      severity_filter: severities,
      webhook: {
        url: postUrl,
        headers: headersObj,
        payload_template: payloadTemplate,
      },
    };
  }, [postUrl, headers, payloadTemplate, severities]);

  const testMutation = useMutation({
    mutationFn: () => testNotificationChannel(buildConfig()),
    onSuccess: (res) => addToast("success", res.message),
    onError: () => addToast("error", "Webhook test failed"),
  });

  const saveMutation = useMutation({
    mutationFn: () => saveNotificationChannel(buildConfig()),
    onSuccess: () => addToast("success", "Webhook channel saved"),
    onError: () => addToast("error", "Failed to save Webhook channel"),
  });

  const addHeader = () => {
    setHeaders((prev) => [...prev, { id: generateId(), key: "", value: "" }]);
  };

  const removeHeader = (id: string) => {
    setHeaders((prev) => prev.filter((h) => h.id !== id));
  };

  const updateHeader = (id: string, field: "key" | "value", val: string) => {
    setHeaders((prev) =>
      prev.map((h) => (h.id === id ? { ...h, [field]: val } : h)),
    );
  };

  return (
    <Card
      title="Webhook"
      className="flex flex-col"
      footer={
        <div className="flex items-center justify-between gap-2">
          <Button
            variant="secondary"
            size="sm"
            loading={testMutation.isPending}
            onClick={() => testMutation.mutate()}
          >
            Test
          </Button>
          <Button
            size="sm"
            loading={saveMutation.isPending}
            onClick={() => saveMutation.mutate()}
          >
            Save
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        {/* POST URL */}
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            POST URL
          </label>
          <input
            type="url"
            value={postUrl}
            onChange={(e) => setPostUrl(e.target.value)}
            placeholder="https://example.com/webhook"
            className={inputClass}
          />
        </div>

        {/* Headers */}
        <div>
          <div className="mb-1 flex items-center justify-between">
            <label className="text-sm font-medium text-gray-700">Headers</label>
            <button
              type="button"
              onClick={addHeader}
              className="text-xs font-medium text-brand-600 hover:text-brand-700"
            >
              + Add Header
            </button>
          </div>
          <div className="space-y-2">
            {headers.map((row) => (
              <div key={row.id} className="flex items-center gap-2">
                <input
                  type="text"
                  value={row.key}
                  onChange={(e) => updateHeader(row.id, "key", e.target.value)}
                  placeholder="Key"
                  className={`${inputClass} flex-1`}
                />
                <input
                  type="text"
                  value={row.value}
                  onChange={(e) => updateHeader(row.id, "value", e.target.value)}
                  placeholder="Value"
                  className={`${inputClass} flex-1`}
                />
                <button
                  type="button"
                  onClick={() => removeHeader(row.id)}
                  className="flex-shrink-0 rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-red-500"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Payload Template */}
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Payload Template (JSON)
          </label>
          <textarea
            value={payloadTemplate}
            onChange={(e) => setPayloadTemplate(e.target.value)}
            rows={6}
            className={`${inputClass} font-mono text-xs`}
          />
          <div className="mt-1.5 flex flex-wrap gap-1">
            <span className="text-xs text-gray-500">Variables:</span>
            {VARIABLE_HINTS.map((hint) => (
              <code
                key={hint}
                className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600"
              >
                {hint}
              </code>
            ))}
          </div>
        </div>

        {/* Severity Filter */}
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Severity Filter
          </label>
          <SeverityToggles selected={severities} onChange={setSeverities} />
        </div>
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Main Export
// ---------------------------------------------------------------------------

export default function NotificationChannels() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">
          Notification Channels
        </h2>
        <p className="mt-1 text-sm text-gray-500">
          Configure where alert notifications are delivered. Test each channel
          before saving.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <SlackChannelCard />
        <EmailChannelCard />
        <WebhookChannelCard />
      </div>
    </div>
  );
}
