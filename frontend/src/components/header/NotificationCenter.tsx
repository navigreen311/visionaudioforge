"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import api from "@/lib/api";
import NotificationItem from "./NotificationItem";

interface Notification {
  id: string;
  type: string;
  title: string;
  description: string;
  read: boolean;
  created_at: string;
  action_url: string;
}

export default function NotificationCenter() {
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const fetchUnreadCount = useCallback(async () => {
    try {
      const res = await api.get<{ count: number }>(
        "/api/notifications/unread-count"
      );
      setUnreadCount(res.data.count);
    } catch {
      // silently ignore
    }
  }, []);

  const fetchNotifications = useCallback(async () => {
    try {
      const res = await api.get<Notification[]>("/api/notifications");
      setNotifications(res.data);
    } catch {
      // silently ignore
    }
  }, []);

  // Poll unread count every 30s
  useEffect(() => {
    if (typeof window === "undefined") return;
    fetchUnreadCount();
    const interval = setInterval(fetchUnreadCount, 30000);
    return () => clearInterval(interval);
  }, [fetchUnreadCount]);

  // Fetch full list when dropdown opens
  useEffect(() => {
    if (open) {
      fetchNotifications();
    }
  }, [open, fetchNotifications]);

  // Click outside to close
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleMarkRead = async (id: string) => {
    try {
      await api.patch(`/api/notifications/${id}/read`);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch {
      // silently ignore
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await api.post("/api/notifications/read-all");
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
      setUnreadCount(0);
    } catch {
      // silently ignore
    }
  };

  const badgeLabel = unreadCount > 99 ? "99+" : String(unreadCount);

  return (
    <div className="relative" ref={containerRef}>
      {/* Bell button */}
      <button
        onClick={() => setOpen((prev) => !prev)}
        className="relative rounded-lg p-2 text-gray-500 hover:bg-gray-100"
      >
        <svg
          className="h-5 w-5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
          />
        </svg>
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-red-500 px-1 text-[10px] text-white">
            {badgeLabel}
          </span>
        )}
      </button>

      {/* Dropdown panel */}
      {open && (
        <div className="absolute right-0 mt-2 w-[380px] rounded-lg border border-gray-200 bg-white shadow-lg z-50 overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
            <h3 className="text-sm font-semibold text-gray-900">
              Notifications
            </h3>
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="text-xs font-medium text-blue-600 hover:text-blue-800"
              >
                Mark all read
              </button>
            )}
          </div>

          {/* Notification list */}
          <div className="max-h-[480px] overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-gray-400">
                <svg
                  className="mb-2 h-8 w-8"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <p className="text-sm">All caught up!</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {notifications.map((notif) => (
                  <NotificationItem
                    key={notif.id}
                    notification={notif}
                    onMarkRead={handleMarkRead}
                    onClose={() => setOpen(false)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
