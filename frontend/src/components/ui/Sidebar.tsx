"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import Badge from "./Badge";
import { useAuthStore } from "@/stores/auth";

const navItems = [
  { href: "/", label: "Dashboard", icon: "\uD83D\uDCCA" },
  { href: "/capture", label: "Capture", icon: "\uD83D\uDCF9" },
  { href: "/vision", label: "Vision", icon: "\uD83D\uDC41" },
  { href: "/audio", label: "Audio", icon: "\uD83C\uDFA7" },
  { href: "/transform", label: "Transform", icon: "\uD83D\uDD04" },
  { href: "/train", label: "Train", icon: "\uD83E\uDDE0" },
  { href: "/validate", label: "Validate", icon: "\u2705" },
  { href: "/search", label: "Search", icon: "\uD83D\uDD0D" },
  { href: "/alerts", label: "Alerts", icon: "\uD83D\uDD14" },
  { href: "/pipeline", label: "Pipeline", icon: "\u2699\uFE0F" },
  { href: "/investigate", label: "Investigate", icon: "\uD83D\uDD2C" },
  { href: "/agents", label: "Agents", icon: "\uD83E\uDD16" },
  { href: "/assets", label: "Assets", icon: "\uD83D\uDCC1" },
  { href: "/annotate", label: "Annotate", icon: "\uD83C\uDFA8" },
  { href: "/evaluation", label: "Evaluation", icon: "\uD83D\uDCCB" },
  { href: "/observability", label: "Observability", icon: "\uD83D\uDCE1" },
  { href: "/settings", label: "Settings", icon: "\u2699" },
];

interface SidebarProps {
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}

export default function Sidebar({ mobileOpen, onMobileClose }: SidebarProps) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const user = useAuthStore((s) => s.user);

  const sidebarContent = (
    <aside
      className={`bg-brand-900 text-white min-h-screen flex flex-col transition-all duration-200 ${
        collapsed ? "w-16" : "w-60"
      }`}
    >
      {/* Logo + toggle */}
      <div className="flex items-center justify-between border-b border-brand-700 px-3 py-4">
        {!collapsed && (
          <h1 className="text-lg font-bold tracking-tight truncate">
            VisionAudioForge
          </h1>
        )}
        {collapsed && (
          <h1 className="text-lg font-bold mx-auto">VAF</h1>
        )}
        <button
          onClick={() => setCollapsed((c) => !c)}
          className="hidden lg:flex items-center justify-center rounded p-1 text-brand-100 hover:bg-brand-700 transition-colors"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            {collapsed ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7M19 19l-7-7 7-7" />
            )}
          </svg>
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-2 space-y-0.5 overflow-y-auto">
        {navItems.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onMobileClose}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                isActive
                  ? "bg-brand-600 text-white border-l-2 border-white"
                  : "text-brand-100 hover:bg-brand-700 hover:text-white"
              }`}
              title={collapsed ? item.label : undefined}
            >
              <span className="text-lg flex-shrink-0 w-6 text-center">
                {item.icon}
              </span>
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* User section */}
      {!collapsed && (
        <div className="border-t border-brand-700 p-3">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-full bg-brand-600 flex items-center justify-center text-sm font-medium">
              {user?.email?.charAt(0).toUpperCase() || "U"}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">
                {user?.email || "User"}
              </p>
              <Badge variant="info">{user?.role || "member"}</Badge>
            </div>
          </div>
        </div>
      )}
      {collapsed && (
        <div className="border-t border-brand-700 p-2 flex justify-center">
          <div className="h-8 w-8 rounded-full bg-brand-600 flex items-center justify-center text-sm font-medium">
            {user?.email?.charAt(0).toUpperCase() || "U"}
          </div>
        </div>
      )}
    </aside>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <div className="hidden lg:block">{sidebarContent}</div>

      {/* Mobile sidebar overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div
            className="fixed inset-0 bg-black/50"
            onClick={onMobileClose}
          />
          <div className="fixed inset-y-0 left-0 z-50">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
}
