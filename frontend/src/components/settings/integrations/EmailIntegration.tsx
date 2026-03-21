'use client';

import { useCallback, useState } from 'react';
import Button from '@/components/ui/Button';
import { useToast } from '@/components/ui/Toast';
import api from '@/lib/api';
import type { EmailConfig, TestResult } from './types';

interface EmailIntegrationProps {
  initial?: Partial<EmailConfig>;
  onSave: (config: EmailConfig) => void;
  onBack: () => void;
}

export default function EmailIntegration({ initial, onSave, onBack }: EmailIntegrationProps) {
  const { addToast } = useToast();
  const [host, setHost] = useState(initial?.host ?? '');
  const [port, setPort] = useState(initial?.port ?? 587);
  const [username, setUsername] = useState(initial?.username ?? '');
  const [password, setPassword] = useState(initial?.password ?? '');
  const [useTls, setUseTls] = useState(initial?.useTls ?? true);
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);

  const handleTest = useCallback(async () => {
    if (!host) {
      addToast('warning', 'Please enter an SMTP host.');
      return;
    }
    setTesting(true);
    try {
      const { data } = await api.post<TestResult>('/api/integrations/email/test', {
        host,
        port,
        username,
        use_tls: useTls,
      });
      addToast(data.ok ? 'success' : 'error', data.message);
    } catch {
      addToast('error', 'Failed to test email connection.');
    } finally {
      setTesting(false);
    }
  }, [host, port, username, useTls, addToast]);

  const handleSave = useCallback(async () => {
    if (!host) {
      addToast('warning', 'SMTP host is required.');
      return;
    }
    setSaving(true);
    try {
      await api.post('/api/integrations', {
        type: 'email',
        config: { host, port, username, password, use_tls: useTls },
      });
      onSave({ host, port, username, password, useTls });
      addToast('success', 'Email SMTP integration saved.');
    } catch {
      addToast('error', 'Failed to save email integration.');
    } finally {
      setSaving(false);
    }
  }, [host, port, username, password, useTls, onSave, addToast]);

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
        <h3 className="text-lg font-semibold text-gray-900">Email SMTP Integration</h3>
      </div>

      {/* Host */}
      <div>
        <label htmlFor="email-host" className="block text-sm font-medium text-gray-700 mb-1">
          SMTP Host
        </label>
        <input
          id="email-host"
          type="text"
          value={host}
          onChange={(e) => setHost(e.target.value)}
          placeholder="smtp.example.com"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
      </div>

      {/* Port */}
      <div>
        <label htmlFor="email-port" className="block text-sm font-medium text-gray-700 mb-1">
          Port
        </label>
        <input
          id="email-port"
          type="number"
          value={port}
          onChange={(e) => setPort(Number(e.target.value))}
          placeholder="587"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
      </div>

      {/* Username */}
      <div>
        <label htmlFor="email-user" className="block text-sm font-medium text-gray-700 mb-1">
          Username
        </label>
        <input
          id="email-user"
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="user@example.com"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
      </div>

      {/* Password (masked) */}
      <div>
        <label htmlFor="email-pass" className="block text-sm font-medium text-gray-700 mb-1">
          Password
        </label>
        <input
          id="email-pass"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Enter password"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
      </div>

      {/* TLS Toggle */}
      <div className="flex items-center gap-3">
        <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
          <input
            type="checkbox"
            checked={useTls}
            onChange={(e) => setUseTls(e.target.checked)}
            className="rounded border-gray-300 text-brand-600 focus:ring-brand-500"
          />
          Use TLS
        </label>
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
