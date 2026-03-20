"use client";

import React, { useState } from "react";
import Tabs from "@/components/ui/Tabs";
import AlertInbox from "@/components/alerts/AlertInbox";
import RuleBuilder from "@/components/alerts/RuleBuilder";
import AlertStats from "@/components/alerts/AlertStats";

const TABS = [
  { id: "live", label: "Live Alerts" },
  { id: "rules", label: "Rules" },
  { id: "stats", label: "Statistics" },
];

export default function AlertsPage() {
  const [activeTab, setActiveTab] = useState("live");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Alerts</h1>
        <p className="mt-1 text-sm text-gray-500">
          Monitor alerts, configure rules, and review statistics.
        </p>
      </div>

      <Tabs tabs={TABS} activeTab={activeTab} onChange={setActiveTab} />

      <div>
        {activeTab === "live" && <AlertInbox />}
        {activeTab === "rules" && <RuleBuilder />}
        {activeTab === "stats" && <AlertStats />}
      </div>
    </div>
  );
}
