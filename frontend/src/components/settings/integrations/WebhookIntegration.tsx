'use client';

import { useCallback, useState } from 'react';
import Button from '@/components/ui/Button';
import { useToast } from '@/components/ui/Toast';
import api from '@/lib/api';
import type {
  PayloadFormat,
  TestResult,
  WebhookConfig,
  WebhookEventKind,
  WebhookHeader,
} from './types';

const EVENT_OPTIONS: { value: WebhookEventKind; label: string }[] = [
  { value: 'alert', label: 'Alert' },
  { value: 'pipeline', label: 'Pipeline' },
  { value: 'model', label: 'Model' },
  { value: 'asset', label: 'Asset' },
];

const FORMAT_OPTIONS: { value: PayloadFormat; label: string }[] = [
  { value: 'json', label: 'JSON' },
  { value: 'form', label: 'Form-Encoded' },
];

interface WebhookIntegrationProps {
  initial?: Partial<WebhookConfig>;
  onSave: (config: WebhookConfig) => void;
  onBack: () => void;
}

export default function WebhookIntegration({ initial, onSave, onBack }: WebhookIntegrationProps) {
  const { addToast } = useToast();
  const [url, setUrl] = useState(initial?.url ?? '');
  const [headers, setHeaders] = useState<WebhookHeader[]>(
    initial?.headers ?? [{ key: '', value: '' }],
  );
  const [events, setEvents] = useState<WebhookEventKind[]>(initial?.events ?? []);
  const [payloadFormat, setPayloadFormat] = useState<PayloadFormat>(
    initial?.payloadFormat ?? 'json',
  );
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);

  // ── Header helpers ──────────────────────────────────────────────

  const updateHeader = (index: number, field: 'key' | 'value', val: string) => {
    setHeaders((prev) => prev.map((h, i) => (i === index ? { ...h, [field]: val } : h)));
  };

  const addHeader = () => setHeaders((prev) => [...prev, { key: '', value: '' }]);

  const removeHeader = (index: number) => {
    setHeaders((prev) => prev.filter((_, i) => i !== index));
  };

  // ── Event toggle ────────────────────────────────────────────────

  const toggleEvent = (ev: WebhookEventKind) => {
    setEvents((prev) =>
      prev.includes(ev) ? prev.filter((e) => e !== ev) : [...prev, ev],
    );
  };

  // ── Actions ─────────────────────────────────────────────────────

  const handleTest = useCallback(async () => {
    if (!url) {
      addToast('warning', 'Please enter a POST URL first.');
      return;
    }
    setTesting(true);
    try {
      const headersMap = Object.fromEntries(
        headers.filter((h) => h.key.trim()).map((h) => [h.key, h.value]),
      );
      const { data } = await api.post<TestResult>('/api/integrations/webhook/test', {
        url,
        headers: headersMap,
        events,
        payload_format: payloadFormat,
      });
      addToast(data.ok ? 'success' : 'error', data.message);
    } catch {
      addToast('error', 'Failed to test webhook.');
    } finally {
      setTesting(false);
    }
  }, [url, headers, events, payloadFormat, addToast]);

  const handleSave = useCallback(async () => {
    if (!url) {
      addToast('warning', 'POST URL is required.');
      return;
    }
    setSaving(true);
    try {
      const headersMap = Object.fromEntries(
        headers.filter((h) => h.key.trim()).map((h) => [h.key, h.value]),
      );
      await api.post('/api/integrations', {
        type: 'webhook',
        config: {
          url,
          headers: headersMap,
          events,
          payload_format: payloadFormat,
        },
      });
      onSave({ url, headers, events, payloadFormat });
      addToast('success', 'Webhook integration saved.');
    } catch {
      addToast('error', 'Failed to save webhook integration.');
    } finally {
      setSaving(false);
    }
  }, [url, headers, events, payloadFormat, onSave, addToast]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
          aria-label="Back"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <h3 className="text-lg font-semibold text-gray-900">Webhook Integration</h3>
      </div>

      {/* POST URL */}
      <div>
        <label htmlFor="webhook-url" className="block text-sm font-medium text-gray-700 mb-1">
          POST URL
        </label>
        <input
          id="webhook-url"
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://example.com/webhook"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
      </div>

      {/* Headers Key-Value Editor */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Headers</label>
        <div className="space-y-2">
          {headers.map((header, idx) => (
            <div key={idx} className="flex items-center gap-2">
              <input
                type="text"
                value={header.key}
                onChange={(e) => updateHeader(idx, 'key', e.target.value)}
                placeholder="Header name"
                className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
              <input
                type="text"
                value={header.value}
                onChange={(e) => updateHeader(idx, 'value', e.target.value)}
                placeholder="Header value"
                className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
              <button
                onClick={() => removeHeader(idx)}
                className="rounded-lg p-2 text-gray-400 hover:bg-red-50 hover:text-red-500 transition-colors"
                aria-label="Remove header"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
        </div>
        <button
          onClick={addHeader}
          className="mt-2 text-sm text-brand-600 hover:text-brand-700 font-medium"
        >
          + Add Header
        </button>
      </div>

      {/* Event Checkboxes */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Events</label>
        <div className="flex flex-wrap gap-4">
          {EVENT_OPTIONS.map((opt) => (
            <label key={opt.value} className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
              <input
                type="checkbox"
                checked={events.includes(opt.value)}
                onChange={() => toggleEvent(opt.value)}
                className="rounded border-gray-300 text-brand-600 focus:ring-brand-500"
              />
              {opt.label}
            </label>
          ))}
        </div>
      </div>

      {/* Payload Format */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Payload Format</label>
        <div className="flex gap-4">
          {FORMAT_OPTIONS.map((opt) => (
            <label key={opt.value} className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
              <input
                type="radio"
                name="payload-format"
                checked={payloadFormat === opt.value}
                onChange={() => setPayloadFormat(opt.value)}
                className="border-gray-300 text-brand-600 focus:ring-brand-500"
              />
              {opt.label}
            </label>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3 pt-2">
        <Button variant="secondary" onClick={handleTest} loading={testing}>
          Test Webhook
        </Button>
        <Button onClick={handleSave} loading={saving}>
          Save
        </Button>
      </div>
    </div>
  );
}
