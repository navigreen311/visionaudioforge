'use client';

import { useCallback, useEffect, useState } from 'react';
import Card from '@/components/ui/Card';
import StatusIndicator from '@/components/ui/StatusIndicator';
import Button from '@/components/ui/Button';
import api from '@/lib/api';
import { SlackIntegration } from './integrations';
import { WebhookIntegration } from './integrations';
import { S3Integration } from './integrations';
import { EmailIntegration } from './integrations';
import type {
  ConnectionStatus,
  IntegrationType,
  SlackConfig,
  WebhookConfig,
  S3Config,
  EmailConfig,
} from './integrations/types';

// ── Icon components ───────────────────────────────────────────────

function SlackIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zm1.271 0a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zm0 1.271a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zm-1.27 0a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.163 0a2.528 2.528 0 0 1 2.523 2.522v6.312zM15.163 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.163 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zm0-1.27a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.315A2.528 2.528 0 0 1 24 15.163a2.528 2.528 0 0 1-2.522 2.523h-6.315z" />
    </svg>
  );
}

function WebhookIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244" />
    </svg>
  );
}

function StorageIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" />
    </svg>
  );
}

function EmailIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75" />
    </svg>
  );
}

// ── Card definition ───────────────────────────────────────────────

interface IntegrationCardDef {
  type: IntegrationType;
  name: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
}

const INTEGRATION_CARDS: IntegrationCardDef[] = [
  {
    type: 'slack',
    name: 'Slack',
    description: 'Send alerts and notifications to Slack channels via incoming webhooks.',
    icon: SlackIcon,
  },
  {
    type: 'webhook',
    name: 'Webhook',
    description: 'Push event payloads to external HTTP endpoints in real time.',
    icon: WebhookIcon,
  },
  {
    type: 's3',
    name: 'Object Storage',
    description: 'Connect AWS S3, Google Cloud Storage, or Azure Blob for asset storage.',
    icon: StorageIcon,
  },
  {
    type: 'email',
    name: 'Email SMTP',
    description: 'Configure SMTP settings for email notifications and reports.',
    icon: EmailIcon,
  },
];

// ── Main Component ────────────────────────────────────────────────

export default function IntegrationsTab() {
  const [statuses, setStatuses] = useState<Record<IntegrationType, ConnectionStatus>>({
    slack: 'not_connected',
    webhook: 'not_connected',
    s3: 'not_connected',
    email: 'not_connected',
  });
  const [activeIntegration, setActiveIntegration] = useState<IntegrationType | null>(null);
  const [loading, setLoading] = useState(true);

  // Fetch current integration statuses on mount
  useEffect(() => {
    let cancelled = false;
    async function fetchStatuses() {
      try {
        const { data } = await api.get<
          { type: IntegrationType; status: ConnectionStatus }[]
        >('/api/integrations');
        if (cancelled) return;
        const next = { ...statuses };
        for (const rec of data) {
          if (rec.type in next) {
            next[rec.type] = rec.status;
          }
        }
        setStatuses(next);
      } catch {
        // keep defaults
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchStatuses();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const markConnected = useCallback((type: IntegrationType) => {
    setStatuses((prev) => ({ ...prev, [type]: 'connected' as ConnectionStatus }));
    setActiveIntegration(null);
  }, []);

  const handleBack = useCallback(() => setActiveIntegration(null), []);

  // ── Detail views ──────────────────────────────────────────────

  if (activeIntegration === 'slack') {
    return (
      <Card>
        <SlackIntegration
          onSave={() => markConnected('slack')}
          onBack={handleBack}
        />
      </Card>
    );
  }

  if (activeIntegration === 'webhook') {
    return (
      <Card>
        <WebhookIntegration
          onSave={() => markConnected('webhook')}
          onBack={handleBack}
        />
      </Card>
    );
  }

  if (activeIntegration === 's3') {
    return (
      <Card>
        <S3Integration
          onSave={() => markConnected('s3')}
          onBack={handleBack}
        />
      </Card>
    );
  }

  if (activeIntegration === 'email') {
    return (
      <Card>
        <EmailIntegration
          onSave={() => markConnected('email')}
          onBack={handleBack}
        />
      </Card>
    );
  }

  // ── Grid view ─────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600" />
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {INTEGRATION_CARDS.map((card) => {
        const status = statuses[card.type];
        const isConnected = status === 'connected';
        const Icon = card.icon;

        return (
          <Card key={card.type}>
            <div className="flex items-start gap-4">
              {/* Icon */}
              <div className="flex-shrink-0 rounded-lg bg-gray-100 p-3">
                <Icon className="h-6 w-6 text-gray-700" />
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h4 className="text-sm font-semibold text-gray-900">{card.name}</h4>
                  <StatusIndicator
                    status={isConnected ? 'online' : 'offline'}
                    label={isConnected ? 'Connected' : 'Not Connected'}
                  />
                </div>
                <p className="text-sm text-gray-500 mb-3">{card.description}</p>
                <Button
                  size="sm"
                  variant={isConnected ? 'secondary' : 'primary'}
                  onClick={() => setActiveIntegration(card.type)}
                >
                  {isConnected ? 'Configure' : 'Connect'}
                </Button>
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
}
