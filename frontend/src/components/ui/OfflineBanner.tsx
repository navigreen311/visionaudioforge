"use client";

import { useEffect, useState } from "react";

export default function OfflineBanner() {
  const [isOnline, setIsOnline] = useState(true);
  const [showOnline, setShowOnline] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;

    setMounted(true);
    setIsOnline(navigator.onLine);

    const handleOnline = () => {
      setIsOnline(true);
      setShowOnline(true);
      setTimeout(() => setShowOnline(false), 3000);
    };

    const handleOffline = () => {
      setIsOnline(false);
      setShowOnline(false);
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  if (!mounted) return null;

  if (!isOnline) {
    return (
      <div className="fixed top-0 left-0 right-0 z-[200] flex items-center justify-center bg-red-600 px-4 py-2 text-sm font-medium text-white shadow-md animate-in slide-in-from-top">
        Connection lost &mdash; reconnecting...
      </div>
    );
  }

  if (showOnline) {
    return (
      <div className="fixed top-0 left-0 right-0 z-[200] flex items-center justify-center bg-green-600 px-4 py-2 text-sm font-medium text-white shadow-md animate-in slide-in-from-top">
        Back online
      </div>
    );
  }

  return null;
}
