"use client";

import React from "react";
import Card from "@/components/ui/Card";
import EmptyState from "@/components/ui/EmptyState";

interface PlaceholderTabProps {
  title: string;
  description: string;
}

function PlaceholderTab({ title, description }: PlaceholderTabProps) {
  return (
    <Card>
      <EmptyState title={title} description={description} />
    </Card>
  );
}

export function BillingTab() {
  return (
    <PlaceholderTab
      title="Billing"
      description="Manage your subscription, payment methods, and invoices."
    />
  );
}

export function SecurityTab() {
  return (
    <PlaceholderTab
      title="Security"
      description="Configure two-factor authentication, SSO, and session management."
    />
  );
}

export function NotificationsTab() {
  return (
    <PlaceholderTab
      title="Notifications"
      description="Choose how and when you receive notifications."
    />
  );
}

export function StorageTab() {
  return (
    <PlaceholderTab
      title="Storage"
      description="Manage data storage, retention policies, and cleanup rules."
    />
  );
}

export function AuditLogTab() {
  return (
    <PlaceholderTab
      title="Audit Log"
      description="Review activity history and access logs for your workspace."
    />
  );
}

export function AppearanceTab() {
  return (
    <PlaceholderTab
      title="Appearance"
      description="Customize theme, branding, and UI preferences."
    />
  );
}
