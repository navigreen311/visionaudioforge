"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import Sidebar from "@/components/ui/Sidebar";
import UserMenu from "@/components/header/UserMenu";
import NotificationCenter from "@/components/header/NotificationCenter";
import GlobalSearch from "@/components/header/GlobalSearch";
import { useAuthStore } from "@/stores/auth";

/**
 * Shown while the session is resolving and while a redirect is in flight.
 *
 * It renders the chrome and nothing else on purpose: no sidebar links, no
 * notifications, no children. A spinner that replaces the whole page is what
 * keeps protected content from flashing before we know who is looking at it.
 */
function SessionGate({ message }: { message: string }) {
  return (
    <div
      className="flex min-h-screen flex-col items-center justify-center gap-3 bg-gray-50"
      role="status"
      aria-live="polite"
    >
      <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-brand-600" />
      <p className="text-sm text-gray-500">{message}</p>
    </div>
  );
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();
  const router = useRouter();

  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isLoading = useAuthStore((s) => s.isLoading);
  const initialize = useAuthStore((s) => s.initialize);

  // `src/middleware.ts` already turned anonymous visitors away at the edge, but
  // it only sees a cookie it cannot verify. This is the check that runs against
  // a session the backend has actually confirmed.
  useEffect(() => {
    void initialize();
  }, [initialize]);

  useEffect(() => {
    if (isLoading || isAuthenticated) return;
    if (pathname === "/") {
      router.replace("/login");
      return;
    }
    // Read the query string off `location` rather than `useSearchParams`, which
    // would force this layout — and therefore every dashboard page — behind a
    // Suspense boundary at build time.
    const search = typeof window === "undefined" ? "" : window.location.search;
    router.replace(`/login?next=${encodeURIComponent(`${pathname}${search}`)}`);
  }, [isLoading, isAuthenticated, pathname, router]);

  if (isLoading) {
    return <SessionGate message="Checking your session…" />;
  }

  if (!isAuthenticated) {
    return <SessionGate message="Redirecting to sign in…" />;
  }

  // Build breadcrumbs from pathname
  const segments = pathname.split("/").filter(Boolean);
  const breadcrumbs = [
    { label: "Home", href: "/" },
    ...segments.map((seg, i) => ({
      label: seg.charAt(0).toUpperCase() + seg.slice(1),
      href: "/" + segments.slice(0, i + 1).join("/"),
    })),
  ];

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar
        mobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
      />

      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="sticky top-0 z-30 flex items-center gap-4 border-b border-gray-200 bg-white px-4 py-3 shadow-sm lg:px-6">
          {/* Mobile hamburger */}
          <button
            onClick={() => setMobileOpen(true)}
            className="lg:hidden rounded p-1.5 text-gray-500 hover:bg-gray-100"
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>

          {/* Breadcrumbs */}
          <nav className="hidden sm:flex items-center gap-1 text-sm text-gray-500">
            {breadcrumbs.map((bc, i) => (
              <span key={bc.href} className="flex items-center gap-1">
                {i > 0 && <span className="mx-1">/</span>}
                {i < breadcrumbs.length - 1 ? (
                  <Link href={bc.href} className="hover:text-gray-700">
                    {bc.label}
                  </Link>
                ) : (
                  <span className="text-gray-900 font-medium">{bc.label}</span>
                )}
              </span>
            ))}
          </nav>

          <div className="flex-1" />

          {/* Search */}
          <GlobalSearch />

          {/* Notifications */}
          <NotificationCenter />

          {/* User dropdown */}
          <UserMenu />
        </header>

        {/* Main content */}
        <main className="flex-1 p-4 lg:p-8">{children}</main>
      </div>
    </div>
  );
}
