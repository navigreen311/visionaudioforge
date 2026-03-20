"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/", label: "Dashboard", icon: "D" },
  { href: "/capture", label: "Capture", icon: "Ca" },
  { href: "/vision", label: "Vision", icon: "Vi" },
  { href: "/audio", label: "Audio", icon: "Au" },
  { href: "/transform", label: "Transform", icon: "Tr" },
  { href: "/train", label: "Train", icon: "Tn" },
  { href: "/validate", label: "Validate", icon: "Va" },
  { href: "/search", label: "Search", icon: "Se" },
  { href: "/alerts", label: "Alerts", icon: "Al" },
  { href: "/pipeline", label: "Pipeline", icon: "Pi" },
  { href: "/investigate", label: "Investigate", icon: "In" },
  { href: "/agents", label: "Agents", icon: "Ag" },
  { href: "/assets", label: "Assets", icon: "As" },
  { href: "/evaluation", label: "Evaluation", icon: "Ev" },
  { href: "/settings", label: "Settings", icon: "St" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-brand-900 text-white min-h-screen flex flex-col">
      <div className="p-6 border-b border-brand-700">
        <h1 className="text-lg font-bold tracking-tight">VisionAudioForge</h1>
        <p className="text-xs text-brand-100 mt-1">AI Vision & Audio Platform</p>
      </div>
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? "bg-brand-600 text-white"
                  : "text-brand-100 hover:bg-brand-700 hover:text-white"
              }`}
            >
              <span className="w-7 h-7 rounded bg-brand-700 flex items-center justify-center text-xs font-mono">
                {item.icon}
              </span>
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
