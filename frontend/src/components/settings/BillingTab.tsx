"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import api from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PlanFeature {
  name: string;
  free: string;
  starter: string;
  pro: string;
  enterprise: string;
}

interface UsageMeter {
  label: string;
  current: number;
  limit: number;
  unit: string;
  color: string;
  reset_date: string;
}

interface BillingHistoryItem {
  id: string;
  date: string;
  description: string;
  amount: string;
  status: string;
  invoice_url: string | null;
}

interface BillingData {
  plan: string;
  plan_label: string;
  features: PlanFeature[];
  usage: UsageMeter[];
  history: BillingHistoryItem[];
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

async function fetchBilling(): Promise<BillingData> {
  const { data } = await api.get<BillingData>("/api/settings/billing");
  return data;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const planBadgeVariant: Record<string, string> = {
  free: "neutral",
  starter: "info",
  pro: "success",
  enterprise: "warning",
};

const meterColorMap: Record<string, { bg: string; fill: string }> = {
  blue: { bg: "bg-blue-100", fill: "bg-blue-500" },
  purple: { bg: "bg-purple-100", fill: "bg-purple-500" },
  green: { bg: "bg-green-100", fill: "bg-green-500" },
  amber: { bg: "bg-amber-100", fill: "bg-amber-500" },
  rose: { bg: "bg-rose-100", fill: "bg-rose-500" },
};

function formatResetDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatDisplayDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function PlanCard({ plan, planLabel }: { plan: string; planLabel: string }) {
  const variant = planBadgeVariant[plan] || "neutral";
  const isUpgradeable = plan === "free" || plan === "starter";

  return (
    <Card title="Current Plan">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Badge variant={variant} className="text-sm px-3 py-1">
            {planLabel}
          </Badge>
          {plan === "free" && (
            <span className="text-sm text-gray-500">
              Limited features — upgrade to unlock more
            </span>
          )}
        </div>
        {isUpgradeable && (
          <Button variant="primary" size="md">
            Upgrade to Pro
          </Button>
        )}
      </div>
    </Card>
  );
}

function FeatureComparisonTable({
  features,
  currentPlan,
}: {
  features: PlanFeature[];
  currentPlan: string;
}) {
  const plans: { key: keyof PlanFeature; label: string }[] = [
    { key: "free", label: "Free" },
    { key: "starter", label: "Starter" },
    { key: "pro", label: "Pro" },
    { key: "enterprise", label: "Enterprise" },
  ];

  return (
    <Card title="Feature Comparison">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Feature
              </th>
              {plans.map((p) => (
                <th
                  key={p.key}
                  className={`px-6 py-3 text-center text-xs font-medium uppercase tracking-wider ${
                    p.key === currentPlan
                      ? "text-brand-700 bg-brand-50"
                      : "text-gray-500"
                  }`}
                >
                  {p.label}
                  {p.key === currentPlan && (
                    <span className="ml-1 text-[10px] font-normal normal-case">
                      (current)
                    </span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {features.map((feature) => (
              <tr key={feature.name} className="hover:bg-gray-50">
                <td className="px-6 py-3 text-sm font-medium text-gray-900 whitespace-nowrap">
                  {feature.name}
                </td>
                {plans.map((p) => (
                  <td
                    key={p.key}
                    className={`px-6 py-3 text-sm text-center whitespace-nowrap ${
                      p.key === currentPlan
                        ? "text-brand-700 font-medium bg-brand-50/50"
                        : "text-gray-600"
                    }`}
                  >
                    {feature[p.key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function UsageMeters({ meters }: { meters: UsageMeter[] }) {
  return (
    <Card title="Usage This Period">
      <div className="space-y-5">
        {meters.map((meter) => {
          const pct =
            meter.limit > 0
              ? Math.min((meter.current / meter.limit) * 100, 100)
              : 0;
          const colors = meterColorMap[meter.color] || meterColorMap.blue;
          const isHigh = pct >= 80;
          const isFull = pct >= 100;

          return (
            <div key={meter.label}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-gray-700">
                  {meter.label}
                </span>
                <div className="flex items-center gap-2">
                  <span
                    className={`text-sm font-semibold ${
                      isFull
                        ? "text-red-600"
                        : isHigh
                          ? "text-amber-600"
                          : "text-gray-900"
                    }`}
                  >
                    {meter.current.toLocaleString()} / {meter.limit.toLocaleString()}{" "}
                    {meter.unit}
                  </span>
                </div>
              </div>
              <div
                className={`w-full h-2.5 rounded-full ${colors.bg}`}
                role="progressbar"
                aria-valuenow={meter.current}
                aria-valuemin={0}
                aria-valuemax={meter.limit}
                aria-label={`${meter.label}: ${meter.current} of ${meter.limit} ${meter.unit}`}
              >
                <div
                  className={`h-2.5 rounded-full transition-all duration-500 ${
                    isFull
                      ? "bg-red-500"
                      : isHigh
                        ? "bg-amber-500"
                        : colors.fill
                  }`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <p className="text-xs text-gray-400 mt-1">
                Resets {formatResetDate(meter.reset_date)}
              </p>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

function BillingHistory({
  history,
  plan,
}: {
  history: BillingHistoryItem[];
  plan: string;
}) {
  if (plan === "free") {
    return (
      <Card title="Billing History">
        <div className="text-center py-8">
          <svg
            className="mx-auto h-10 w-10 text-gray-300"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M9 14l6-6m-5.5.5h.01m4.99 5h.01M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l3.5-2 3.5 2 3.5-2 3.5 2z"
            />
          </svg>
          <p className="mt-2 text-sm font-medium text-gray-600">
            No billing history
          </p>
          <p className="text-xs text-gray-400 mt-1">
            Upgrade your plan to see invoices here.
          </p>
        </div>
      </Card>
    );
  }

  if (history.length === 0) {
    return (
      <Card title="Billing History">
        <p className="text-sm text-gray-500 text-center py-6">
          No invoices yet.
        </p>
      </Card>
    );
  }

  const statusBadge: Record<string, string> = {
    paid: "success",
    pending: "warning",
    failed: "error",
    refunded: "info",
  };

  return (
    <Card title="Billing History">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Date
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Description
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Amount
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Invoice
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {history.map((item) => (
              <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4 text-sm text-gray-900 whitespace-nowrap">
                  {formatDisplayDate(item.date)}
                </td>
                <td className="px-6 py-4 text-sm text-gray-700 whitespace-nowrap">
                  {item.description}
                </td>
                <td className="px-6 py-4 text-sm font-medium text-gray-900 whitespace-nowrap">
                  {item.amount}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <Badge variant={statusBadge[item.status] || "neutral"}>
                    {item.status.charAt(0).toUpperCase() + item.status.slice(1)}
                  </Badge>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {item.invoice_url ? (
                    <a
                      href={item.invoice_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-brand-600 hover:text-brand-700 font-medium inline-flex items-center gap-1"
                    >
                      <svg
                        className="h-4 w-4"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                        />
                      </svg>
                      Download
                    </a>
                  ) : (
                    <span className="text-sm text-gray-400">--</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function BillingTab() {
  const { data, isLoading, isError } = useQuery<BillingData>({
    queryKey: ["settings-billing"],
    queryFn: fetchBilling,
  });

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        Failed to load billing data. Please try again.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PlanCard plan={data.plan} planLabel={data.plan_label} />
      <FeatureComparisonTable
        features={data.features}
        currentPlan={data.plan}
      />
      <UsageMeters meters={data.usage} />
      <BillingHistory history={data.history} plan={data.plan} />
    </div>
  );
}
