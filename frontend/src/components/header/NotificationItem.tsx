"use client";

import { useRouter } from "next/navigation";

interface Notification {
  id: string;
  type: string;
  title: string;
  description: string;
  read: boolean;
  created_at: string;
  action_url: string;
}

interface NotificationItemProps {
  notification: Notification;
  onMarkRead: (id: string) => void;
  onClose: () => void;
}

function getRelativeTime(dateStr: string): string {
  const now = new Date();
  const date = new Date(dateStr);
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  if (diffDay < 7) return `${diffDay}d ago`;
  return date.toLocaleDateString();
}

function typeIcon(type: string): { color: string; letter: string } {
  switch (type) {
    case "alert":
      return { color: "#A32D2D", letter: "!" };
    case "pipeline":
      return { color: "#3C3489", letter: "P" };
    case "model":
      return { color: "#0F6E56", letter: "M" };
    case "asset":
      return { color: "#854F0B", letter: "A" };
    case "system":
      return { color: "#6B7280", letter: "S" };
    default:
      return { color: "#6B7280", letter: "N" };
  }
}

export default function NotificationItem({
  notification,
  onMarkRead,
  onClose,
}: NotificationItemProps) {
  const router = useRouter();
  const { color, letter } = typeIcon(notification.type);

  const handleClick = () => {
    if (!notification.read) {
      onMarkRead(notification.id);
    }
    onClose();
    router.push(notification.action_url);
  };

  return (
    <button
      onClick={handleClick}
      className={`flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-gray-50 transition-colors ${
        !notification.read ? "bg-blue-50/40" : ""
      }`}
    >
      {/* Type icon */}
      <div
        className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-white text-xs font-bold"
        style={{ backgroundColor: color }}
      >
        {letter}
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-gray-900 truncate">
          {notification.title}
        </p>
        <p className="text-xs text-gray-500 truncate">
          {notification.description}
        </p>
        <p className="mt-0.5 text-[11px] text-gray-400">
          {getRelativeTime(notification.created_at)}
        </p>
      </div>

      {/* Unread dot */}
      {!notification.read && (
        <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-blue-500" />
      )}
    </button>
  );
}
