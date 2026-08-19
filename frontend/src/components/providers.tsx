"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactNode, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { ToastProvider } from "@/components/ui/Toast";
import { ConfirmProvider } from "@/providers/ConfirmProvider";
import { installAuthedFetch } from "@/lib/authed-fetch";
import { useAuthStore } from "@/stores/auth";

interface ProvidersProps {
  children: ReactNode;
}

// At module scope, not in an effect: React runs child effects before parent
// ones, so a component that fetches on mount would beat an effect here. This
// runs when the client bundle first evaluates, ahead of any render.
//
// 57 places in the console call `fetch("/api/…")` directly rather than through
// the axios client, and every one was returning 401 once authentication landed.
// See lib/authed-fetch.ts.
installAuthedFetch();

const publicPaths = ["/login", "/register"];

function AuthGuard({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { isAuthenticated, isLoading, initialize } = useAuthStore();

  useEffect(() => {
    initialize();
  }, [initialize]);

  useEffect(() => {
    if (!isLoading && !isAuthenticated && !publicPaths.includes(pathname)) {
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, pathname, router]);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-3">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        <p className="text-sm text-gray-500">Loading...</p>
      </div>
    );
  }

  if (!isAuthenticated && !publicPaths.includes(pathname)) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-3">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        <p className="text-sm text-gray-500">Redirecting to login...</p>
      </div>
    );
  }

  return <>{children}</>;
}

export default function Providers({ children }: ProvidersProps) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30 * 1000,
            retry: 1,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <ConfirmProvider>
          <AuthGuard>{children}</AuthGuard>
        </ConfirmProvider>
      </ToastProvider>
    </QueryClientProvider>
  );
}
