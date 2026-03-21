"use client";

import React from "react";

interface NavItem {
  id: string;
  label: string;
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    title: "WORKSPACE",
    items: [
      { id: "general", label: "General" },
      { id: "billing", label: "Billing" },
    ],
  },
  {
    title: "SECURITY & ACCESS",
    items: [
      { id: "api-keys", label: "API Keys" },
      { id: "users", label: "Users" },
      { id: "security", label: "Security" },
    ],
  },
  {
    title: "NOTIFICATIONS",
    items: [{ id: "notifications", label: "Notifications" }],
  },
  {
    title: "DATA",
    items: [
      { id: "storage", label: "Storage" },
      { id: "audit-log", label: "Audit Log" },
    ],
  },
  {
    title: "DEVELOPER",
    items: [
      { id: "integrations", label: "Integrations" },
      { id: "appearance", label: "Appearance" },
    ],
  },
];

interface SettingsNavProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

export default function SettingsNav({ activeTab, onTabChange }: SettingsNavProps) {
  return (
    <nav className="sticky top-6 w-[200px] shrink-0 space-y-6">
      {NAV_GROUPS.map((group) => (
        <div key={group.title}>
          <h4 className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-gray-400">
            {group.title}
          </h4>
          <ul className="space-y-0.5">
            {group.items.map((item) => {
              const isActive = activeTab === item.id;
              return (
                <li key={item.id}>
                  <button
                    onClick={() => onTabChange(item.id)}
                    className={`flex w-full items-center rounded-r-md px-3 py-2 text-sm font-medium transition-colors ${
                      isActive
                        ? "border-l-2 border-brand-600 bg-brand-50 text-brand-700"
                        : "border-l-2 border-transparent text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                    }`}
                  >
                    {item.label}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}
