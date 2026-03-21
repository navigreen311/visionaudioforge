'use client';

import { useCallback, useEffect, useState } from 'react';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';

// ── Types ───────────────────────────────────────────────────────────

interface NotificationChannel {
  inApp: boolean;
  email: boolean;
  slack: boolean;
}

interface NotificationEvent {
  key: string;
  label: string;
  channels: NotificationChannel;
}

interface NotificationCategory {
  key: string;
  label: string;
  events: NotificationEvent[];
}

interface NotificationPreferences {
  categories: NotificationCategory[];
}

interface IntegrationStatus {
  slack: boolean;
  email: boolean;
  webhook: boolean;
}

// ── Defaults ────────────────────────────────────────────────────────

const DEFAULT_CATEGORIES: NotificationCategory[] = [
  {
    key: 'alerts',
    label: 'Alerts',
    events: [
      { key: 'alert_critical', label: 'Critical alert triggered', channels: { inApp: true, email: true, slack: false } },
      { key: 'alert_warning', label: 'Warning alert triggered', channels: { inApp: true, email: false, slack: false } },
      { key: 'alert_acknowledged', label: 'Alert acknowledged', channels: { inApp: true, email: false, slack: false } },
    ],
  },
  {
    key: 'pipeline',
    label: 'Pipeline',
    events: [
      { key: 'pipeline_completed', label: 'Pipeline completed', channels: { inApp: true, email: false, slack: false } },
      { key: 'pipeline_failed', label: 'Pipeline failed', channels: { inApp: true, email: true, slack: false } },
      { key: 'pipeline_scheduled', label: 'Pipeline scheduled', channels: { inApp: false, email: false, slack: false } },
    ],
  },
  {
    key: 'models',
    label: 'Models',
    events: [
      { key: 'model_training_completed', label: 'Training completed', channels: { inApp: true, email: false, slack: false } },
      { key: 'model_deployed', label: 'Model deployed', channels: { inApp: true, email: true, slack: false } },
    ],
  },
  {
    key: 'system',
    label: 'System',
    events: [
      { key: 'system_weekly_digest', label: 'Weekly digest', channels: { inApp: false, email: true, slack: false } },
      { key: 'system_sla_violation', label: 'SLA violation', channels: { inApp: true, email: true, slack: false } },
      { key: 'system_storage_threshold', label: 'Storage usage > 80%', channels: { inApp: true, email: true, slack: false } },
    ],
  },
];

// ── Toggle component ────────────────────────────────────────────────

interface ToggleProps {
  checked: boolean;
  disabled?: boolean;
  tooltip?: string;
  onChange: (checked: boolean) => void;
}

function Toggle({ checked, disabled = false, tooltip, onChange }: ToggleProps) {
  return (
    <div className="relative group">
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 ${
          disabled ? 'cursor-not-allowed opacity-40' : ''
        } ${checked ? 'bg-brand-600' : 'bg-gray-200'}`}
      >
        <span
          className={`pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow ring-0 transition-transform duration-200 ease-in-out ${
            checked ? 'translate-x-4' : 'translate-x-0'
          }`}
        />
      </button>
      {tooltip && disabled && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-10">
          <div className="rounded-md bg-gray-900 px-3 py-1.5 text-xs text-white whitespace-nowrap shadow-lg">
            {tooltip}
            <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900" />
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main component ──────────────────────────────────────────────────

export default function NotificationsTab() {
  const [categories, setCategories] = useState<NotificationCategory[]>(DEFAULT_CATEGORIES);
  const [slackConnected, setSlackConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  // Fetch current preferences + integration status
  useEffect(() => {
    let cancelled = false;

    async function fetchData() {
      try {
        const [prefsRes, intRes] = await Promise.all([
          fetch('/api/settings/notifications'),
          fetch('/api/settings/integrations'),
        ]);

        if (!cancelled && prefsRes.ok) {
          const prefs: NotificationPreferences = await prefsRes.json();
          if (prefs.categories?.length) {
            setCategories(prefs.categories);
          }
        }

        if (!cancelled && intRes.ok) {
          const integrations: IntegrationStatus = await intRes.json();
          setSlackConnected(integrations.slack ?? false);
        }
      } catch {
        // Use defaults on fetch failure
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchData();
    return () => { cancelled = true; };
  }, []);

  // Toggle handler
  const handleToggle = useCallback(
    (categoryKey: string, eventKey: string, channel: keyof NotificationChannel) => {
      setCategories((prev) =>
        prev.map((cat) => {
          if (cat.key !== categoryKey) return cat;
          return {
            ...cat,
            events: cat.events.map((evt) => {
              if (evt.key !== eventKey) return evt;
              return {
                ...evt,
                channels: { ...evt.channels, [channel]: !evt.channels[channel] },
              };
            }),
          };
        }),
      );
      setDirty(true);
      setSaveMessage(null);
    },
    [],
  );

  // Save handler
  const handleSave = useCallback(async () => {
    setSaving(true);
    setSaveMessage(null);
    try {
      const res = await fetch('/api/settings/notifications', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ categories }),
      });
      if (res.ok) {
        setDirty(false);
        setSaveMessage('Preferences saved.');
      } else {
        setSaveMessage('Failed to save preferences.');
      }
    } catch {
      setSaveMessage('Failed to save preferences.');
    } finally {
      setSaving(false);
    }
  }, [categories]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-brand-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Notification Preferences</h3>
          <p className="text-sm text-gray-500 mt-0.5">
            Choose how you want to be notified for each event type.
          </p>
        </div>
        {!slackConnected && (
          <Badge variant="warning">Slack not connected</Badge>
        )}
      </div>

      {categories.map((category) => (
        <Card key={category.key} title={category.label}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  <th className="pb-3 pr-4">Event</th>
                  <th className="pb-3 px-4 text-center w-20">In-App</th>
                  <th className="pb-3 px-4 text-center w-20">Email</th>
                  <th className="pb-3 px-4 text-center w-20">Slack</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {category.events.map((event) => (
                  <tr key={event.key}>
                    <td className="py-3 pr-4 text-gray-700">{event.label}</td>
                    <td className="py-3 px-4">
                      <div className="flex justify-center">
                        <Toggle
                          checked={event.channels.inApp}
                          onChange={() => handleToggle(category.key, event.key, 'inApp')}
                        />
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex justify-center">
                        <Toggle
                          checked={event.channels.email}
                          onChange={() => handleToggle(category.key, event.key, 'email')}
                        />
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex justify-center">
                        <Toggle
                          checked={event.channels.slack}
                          disabled={!slackConnected}
                          tooltip={!slackConnected ? 'Connect Slack in Integrations to enable' : undefined}
                          onChange={() => handleToggle(category.key, event.key, 'slack')}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ))}

      <div className="flex items-center gap-4">
        <Button
          variant="primary"
          size="md"
          loading={saving}
          disabled={!dirty}
          onClick={handleSave}
        >
          Save preferences
        </Button>
        {saveMessage && (
          <span className={`text-sm ${saveMessage.includes('Failed') ? 'text-red-600' : 'text-green-600'}`}>
            {saveMessage}
          </span>
        )}
      </div>
    </div>
  );
}
