"use client";

import { useState, useEffect, useCallback } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface StatCard {
  label: string;
  count: number;
  trend: number; // positive = up, negative = down, 0 = flat
}

interface ReviewStatsData {
  pending: StatCard;
  in_review: StatCard;
  completed_today: StatCard;
  overdue: StatCard;
}

interface ReviewStatsProps {
  onFilterChange?: (status: string) => void;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const API = "/api/reviewops";

const CARD_STYLES: Record<string, { bg: string; text: string; ring: string; icon: string; pulse?: boolean }> = {
  pending: {
    bg: "bg-amber-50",
    text: "text-amber-700",
    ring: "ring-amber-200",
    icon: "text-amber-500",
  },
  in_review: {
    bg: "bg-blue-50",
    text: "text-blue-700",
    ring: "ring-blue-200",
    icon: "text-blue-500",
  },
  completed_today: {
    bg: "bg-green-50",
    text: "text-green-700",
    ring: "ring-green-200",
    icon: "text-green-500",
  },
  overdue: {
    bg: "bg-red-50",
    text: "text-red-700",
    ring: "ring-red-200",
    icon: "text-red-500",
    pulse: true,
  },
};

// ---------------------------------------------------------------------------
// Trend Arrow
// ---------------------------------------------------------------------------

function TrendArrow({ trend }: { trend: number }) {
  if (trend === 0) {
    return (
      <span className="text-gray-400 text-xs font-medium ml-1">--</span>
    );
  }

  const isUp = trend > 0;
  return (
    <span
      className={`inline-flex items-center text-xs font-medium ml-1 ${
        isUp ? "text-green-600" : "text-red-600"
      }`}
    >
      <svg
        className={`w-3 h-3 mr-0.5 ${isUp ? "" : "rotate-180"}`}
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M5 15l7-7 7 7" />
      </svg>
      {Math.abs(trend)}%
    </span>
  );
}

// ---------------------------------------------------------------------------
// StatCard Component
// ---------------------------------------------------------------------------

function StatCardItem({
  statKey,
  stat,
  onClick,
}: {
  statKey: string;
  stat: StatCard;
  onClick: () => void;
}) {
  const style = CARD_STYLES[statKey];
  if (!style) return null;

  return (
    <button
      onClick={onClick}
      className={`relative flex flex-col items-start p-4 rounded-xl ring-1 ${style.bg} ${style.ring} hover:ring-2 transition-all cursor-pointer text-left w-full`}
    >
      {style.pulse && stat.count > 0 && (
        <span className="absolute top-2 right-2 flex h-2.5 w-2.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500" />
        </span>
      )}
      <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
        {stat.label}
      </span>
      <div className="flex items-baseline mt-1">
        <span className={`text-2xl font-bold ${style.text}`}>{stat.count}</span>
        <TrendArrow trend={stat.trend} />
      </div>
    </button>
  );
}

// ---------------------------------------------------------------------------
// ReviewStats Component
// ---------------------------------------------------------------------------

export default function ReviewStats({ onFilterChange }: ReviewStatsProps) {
  const [stats, setStats] = useState<ReviewStatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const fetchStats = useCallback(async () => {
    try {
      setError(false);
      const res = await fetch(`${API}/stats`);
      if (res.ok) {
        const data: ReviewStatsData = await res.json();
        setStats(data);
      } else {
        setError(true);
      }
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 30_000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  const handleClick = (status: string) => {
    onFilterChange?.(status);
  };

  if (loading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="h-20 rounded-xl bg-gray-100 animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { key: "pending", label: "Pending", count: 0, trend: 0 },
          { key: "in_review", label: "In Review", count: 0, trend: 0 },
          { key: "completed_today", label: "Completed Today", count: 0, trend: 0 },
          { key: "overdue", label: "Overdue", count: 0, trend: 0 },
        ].map((s) => (
          <StatCardItem
            key={s.key}
            statKey={s.key}
            stat={{ label: s.label, count: s.count, trend: s.trend }}
            onClick={() => handleClick(s.key)}
          />
        ))}
      </div>
    );
  }

  const cards: { key: string; stat: StatCard }[] = [
    { key: "pending", stat: stats.pending },
    { key: "in_review", stat: stats.in_review },
    { key: "completed_today", stat: stats.completed_today },
    { key: "overdue", stat: stats.overdue },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {cards.map(({ key, stat }) => (
        <StatCardItem
          key={key}
          statKey={key}
          stat={stat}
          onClick={() => handleClick(key)}
        />
      ))}
    </div>
  );
}
