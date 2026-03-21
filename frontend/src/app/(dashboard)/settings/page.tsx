"use client";

import { useState } from "react";
import Tabs from "@/components/ui/Tabs";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import DataTable from "@/components/ui/DataTable";
import Modal from "@/components/ui/Modal";
import EmptyState from "@/components/ui/EmptyState";
import UsersTab from "@/components/settings/UsersTab";

// --- General Tab ---
function GeneralTab() {
  const [workspaceName, setWorkspaceName] = useState("My Workspace");
  const workspaceId = "ws_abc123def456";

  return (
    <div className="space-y-6">
      <Card title="Workspace Settings">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Workspace Name
            </label>
            <div className="flex gap-3">
              <input
                type="text"
                value={workspaceName}
                onChange={(e) => setWorkspaceName(e.target.value)}
                className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
              <Button variant="primary" size="md">
                Save
              </Button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Plan
            </label>
            <Badge variant="info">Free</Badge>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Workspace ID
            </label>
            <div className="flex items-center gap-2">
              <code className="rounded bg-gray-100 px-3 py-1.5 text-sm text-gray-700 font-mono">
                {workspaceId}
              </code>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigator.clipboard.writeText(workspaceId)}
              >
                Copy
              </Button>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}

// --- API Keys Tab ---
function ApiKeysTab() {
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
              { key: "prefix", label: "Key", render: (v) => <code className="text-xs bg-gray-100 px-2 py-0.5 rounded">{String(v)}...</code> },
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

// --- Integrations Tab ---
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

// --- Settings Page ---
export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("general");

  const tabs = [
    { id: "general", label: "General", content: <GeneralTab /> },
    { id: "api-keys", label: "API Keys", content: <ApiKeysTab /> },
    { id: "users", label: "Users", content: <UsersTab /> },
    { id: "integrations", label: "Integrations", content: <IntegrationsTab /> },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-sm text-gray-500 mt-1">
          Manage your workspace configuration
        </p>
      </div>

      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />
    </div>
  );
}
