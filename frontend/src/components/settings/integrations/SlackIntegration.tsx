'use client';

import { useCallback, useState } from 'react';
import Button from '@/components/ui/Button';
import { useToast } from '@/components/ui/Toast';
import api from '@/lib/api';
import type { SlackConfig, TestResult } from './types';

interface SlackIntegrationProps {
  initial?: Partial<SlackConfig>;
  onSave: (config: SlackConfig) => void;
  onBack: () => void;
}

export default function SlackIntegration({ initial, onSave, onBack }: SlackIntegrationProps) {
  const { addToast } = useToast();
  const [webhookUrl, setWebhookUrl] = useState(initial?.webhookUrl ?? '');
  const [channel, setChannel] = useState(initial?.channel ?? '');
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);

  const handleTest = useCallback(async () => {
    if (!webhookUrl) {
      addToast('warning', 'Please enter a webhook URL first.');
      return;
    }
    setTesting(true);
    try {
      const { data } = await api.post<TestResult>('/api/integrations/slack/test', {
        webhook_url: webhookUrl,
        channel,
      });
      addToast(data.ok ? 'success' : 'error', data.message);
    } catch {
      addToast('error', 'Failed to test Slack integration.');
    } finally {
      setTesting(false);
    }
  }, [webhookUrl, channel, addToast]);

  const handleSave = useCallback(async () => {
    if (!webhookUrl) {
      addToast('warning', 'Webhook URL is required.');
      return;
    }
    setSaving(true);
    try {
      await api.post('/api/integrations', {
        type: 'slack',
        config: { webhook_url: webhookUrl, channel },
      });
      onSave({ webhookUrl, channel });
      addToast('success', 'Slack integration saved.');
    } catch {
      addToast('error', 'Failed to save Slack integration.');
    } finally {
      setSaving(false);
    }
  }, [webhookUrl, channel, onSave, addToast]);

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
        <h3 className="text-lg font-semibold text-gray-900">Slack Integration</h3>
      </div>

      {/* Webhook URL */}
      <div>
        <label htmlFor="slack-webhook" className="block text-sm font-medium text-gray-700 mb-1">
          Webhook URL
        </label>
        <input
          id="slack-webhook"
          type="url"
          value={webhookUrl}
          onChange={(e) => setWebhookUrl(e.target.value)}
          placeholder="https://hooks.slack.com/services/..."
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
        <p className="mt-1 text-xs text-gray-500">
          Create an Incoming Webhook in your Slack workspace settings.
        </p>
      </div>

      {/* Channel */}
      <div>
        <label htmlFor="slack-channel" className="block text-sm font-medium text-gray-700 mb-1">
          Channel (optional)
        </label>
        <input
          id="slack-channel"
          type="text"
          value={channel}
          onChange={(e) => setChannel(e.target.value)}
          placeholder="#alerts"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3 pt-2">
        <Button variant="secondary" onClick={handleTest} loading={testing}>
          Test Connection
        </Button>
        <Button onClick={handleSave} loading={saving}>
          Save
        </Button>
      </div>
    </div>
  );
}
