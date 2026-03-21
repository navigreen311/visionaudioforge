"use client";

import { useCallback, useMemo, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import DataTable from "@/components/ui/DataTable";
import Modal from "@/components/ui/Modal";
import EmptyState from "@/components/ui/EmptyState";
import SettingsNav from "@/components/settings/SettingsNav";
import GeneralTab from "@/components/settings/GeneralTab";
import {
  BillingTab,
  SecurityTab,
  NotificationsTab,
  StorageTab,
  AuditLogTab,
  AppearanceTab,
} from "@/components/settings/PlaceholderTabs";

// ---------------------------------------------------------------------------
// API Keys Tab (kept inline — already existed)
// ---------------------------------------------------------------------------

function APIKeysTab() {
  const [showModal, setShowModal] = useState(false);
  const [keyName, setKeyName] = useState("");
  const [keys] = useState<
    { name: string; prefix: string; created: string }[]
  >([]);

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold text-gray-900">API Keys</h3>
        <Button onClick={() => setShowModal(true)}>Create API Key</Button>
      </div>

      {keys.length === 0 ? (
        <Card>
          <EmptyState
            title="No API Keys"
            description="Create an API key to authenticate with the VisionAudioForge API."
            action={{
              label: "Create API Key",
              onClick: () => setShowModal(true),
            }}
          />
        </Card>
      ) : (
        <Card>
          <DataTable
            columns={[
              { key: "name", label: "Name", sortable: true },
              {
                key: "prefix",
                label: "Key",
                render: (v) => (
                  <code className="text-xs bg-gray-100 px-2 py-0.5 rounded">
                    {String(v)}...
                  </code>
                ),
              },
              { key: "created", label: "Created", sortable: true },
              {
                key: "name",
                label: "Actions",
                render: () => (
                  <Button variant="danger" size="sm">
                    Revoke
                  </Button>
                ),
              },
            ]}
            data={keys}
          />
        </Card>
      )}

      <Modal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title="Create API Key"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowModal(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                setKeyName("");
                setShowModal(false);
              }}
            >
              Create
            </Button>
          </>
        }
      >
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Key Name
          </label>
          <input
            type="text"
            value={keyName}
            onChange={(e) => setKeyName(e.target.value)}
            placeholder="e.g., Production API Key"
            className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </div>
      </Modal>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Users Tab (kept inline — already existed)
// ---------------------------------------------------------------------------

function UsersTab() {
  const [users] = useState<
    { email: string; role: string; lastLogin: string }[]
  >([]);

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold text-gray-900">Users</h3>
        <Button>Invite User</Button>
      </div>

      {users.length === 0 ? (
        <Card>
          <EmptyState
            title="No users yet"
            description="Invite team members to collaborate in your workspace."
          />
        </Card>
      ) : (
        <Card>
          <DataTable
            columns={[
              { key: "email", label: "Email", sortable: true },
              {
                key: "role",
                label: "Role",
                render: (v) => <Badge variant="info">{String(v)}</Badge>,
              },
              { key: "lastLogin", label: "Last Login", sortable: true },
              {
                key: "email",
                label: "Actions",
                render: () => (
                  <div className="flex gap-2">
                    <Button variant="ghost" size="sm">
                      Change Role
                    </Button>
                    <Button variant="danger" size="sm">
                      Remove
                    </Button>
                  </div>
                ),
              },
            ]}
            data={users}
          />
        </Card>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Integrations Tab (kept inline — already existed)
// ---------------------------------------------------------------------------

function IntegrationsTab() {
  const integrations = [
    {
      name: "Slack",
      description: "Send notifications and alerts to Slack channels.",
      enabled: false,
    },
    {
      name: "Email",
      description: "Configure email notifications for events.",
      enabled: false,
    },
    {
      name: "Webhook",
      description: "Send event data to custom webhook endpoints.",
      enabled: false,
    },
  ];

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">Integrations</h3>
      <div className="space-y-3">
        {integrations.map((int) => (
          <Card key={int.name}>
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium text-gray-900">{int.name}</h4>
                <p className="text-sm text-gray-500">{int.description}</p>
              </div>
              <div className="flex items-center gap-3">
                <Badge variant="neutral">Coming Soon</Badge>
                <label className="relative inline-flex items-center cursor-not-allowed opacity-50">
                  <input
                    type="checkbox"
                    disabled
                    className="sr-only peer"
                  />
                  <div className="w-9 h-5 bg-gray-200 rounded-full peer-checked:bg-brand-600 after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all" />
                </label>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab registry
// ---------------------------------------------------------------------------

const TAB_COMPONENTS: Record<string, React.ComponentType> = {
  general: GeneralTab,
  billing: BillingTab,
  "api-keys": APIKeysTab,
  users: UsersTab,
  security: SecurityTab,
  notifications: NotificationsTab,
  storage: StorageTab,
  "audit-log": AuditLogTab,
  integrations: IntegrationsTab,
  appearance: AppearanceTab,
};

// ---------------------------------------------------------------------------
// Settings Page
// ---------------------------------------------------------------------------

export default function SettingsPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const initialTab = searchParams.get("tab") || "general";
  const [activeTab, setActiveTab] = useState(initialTab);

  const handleTabChange = useCallback(
    (tab: string) => {
      setActiveTab(tab);
      const params = new URLSearchParams(searchParams.toString());
      params.set("tab", tab);
      router.replace(`?${params.toString()}`, { scroll: false });
    },
    [router, searchParams],
  );

  const ActiveComponent = useMemo(
    () => TAB_COMPONENTS[activeTab] || GeneralTab,
    [activeTab],
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-sm text-gray-500 mt-1">
          Manage your workspace configuration
        </p>
      </div>

      <div className="flex gap-8">
        <SettingsNav activeTab={activeTab} onTabChange={handleTabChange} />
        <div className="min-w-0 flex-1">
          <ActiveComponent />
        </div>
      </div>
    </div>
  );
}
