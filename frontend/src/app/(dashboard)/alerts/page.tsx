"use client";

import React, { useState } from "react";
import Tabs from "@/components/ui/Tabs";
import AlertInbox from "@/components/alerts/AlertInbox";
import AlertStatsSummary from "@/components/alerts/AlertStatsSummary";
import RuleBuilder from "@/components/alerts/RuleBuilder";
import AlertStats from "@/components/alerts/AlertStats";
import IncidentView from "@/components/alerts/IncidentView";
import EvidenceBundleViewer from "@/components/alerts/EvidenceBundleViewer";
import ChainOfCustodyDisplay from "@/components/alerts/ChainOfCustodyDisplay";

const TABS = [
  { id: "inbox", label: "Inbox" },
  { id: "incidents", label: "Incidents" },
  { id: "evidence", label: "Evidence" },
  { id: "custody", label: "Chain of Custody" },
  { id: "rules", label: "Rules" },
  { id: "stats", label: "Statistics" },
];

export default function AlertsPage() {
  const [activeTab, setActiveTab] = useState("inbox");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Alerts</h1>
        <p className="mt-1 text-sm text-gray-500">
          Monitor alerts, manage incidents, review evidence bundles, and track chain of custody.
        </p>
      </div>

      <AlertStatsSummary />

      <Tabs tabs={TABS} activeTab={activeTab} onChange={setActiveTab} />

      <div>
        {activeTab === "inbox" && <AlertInbox />}
        {activeTab === "incidents" && <IncidentView />}
        {activeTab === "evidence" && <EvidenceBundleViewer />}
        {activeTab === "custody" && <ChainOfCustodyDisplay />}
        {activeTab === "rules" && <RuleBuilder />}
        {activeTab === "stats" && <AlertStats />}
      </div>
    </div>
  );
}
