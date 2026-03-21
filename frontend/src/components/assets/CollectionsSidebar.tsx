"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface Collection {
  id: string;
  name: string;
  color: string;
  assetIds: string[];
}

export type FilterKey = "all" | "image" | "video" | "audio" | `collection:${string}`;

export interface AssetCounts {
  total: number;
  image: number;
  video: number;
  audio: number;
  /** Map of collection id -> count */
  collections: Record<string, number>;
}

interface CollectionsSidebarProps {
  activeFilter: FilterKey;
  onFilterChange: (filter: FilterKey) => void;
  assetCounts: AssetCounts;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STORAGE_KEY = "vaf_collections";

const PRESET_COLORS = [
  "#6366f1", // indigo
  "#ec4899", // pink
  "#f59e0b", // amber
  "#10b981", // emerald
  "#3b82f6", // blue
  "#ef4444", // red
  "#8b5cf6", // violet
  "#14b8a6", // teal
];

// ---------------------------------------------------------------------------
// localStorage helpers (try/catch)
// ---------------------------------------------------------------------------

function loadCollections(): Collection[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed as Collection[];
  } catch {
    return [];
  }
}

function saveCollections(collections: Collection[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(collections));
  } catch {
    // quota exceeded or unavailable — silently ignore
  }
}

// ---------------------------------------------------------------------------
// Icons
// ---------------------------------------------------------------------------

function FolderIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
      />
    </svg>
  );
}

function ImageIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
      />
    </svg>
  );
}

function AudioIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"
      />
    </svg>
  );
}

function VideoIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
      />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Context menu
// ---------------------------------------------------------------------------

interface ContextMenuState {
  collectionId: string;
  x: number;
  y: number;
}

function ContextMenu({
  x,
  y,
  onRename,
  onDelete,
  onClose,
}: {
  x: number;
  y: number;
  onRename: () => void;
  onDelete: () => void;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onClose();
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [onClose]);

  return (
    <div
      ref={ref}
      className="fixed z-50 min-w-[140px] rounded-lg border border-gray-200 bg-white py-1 shadow-lg"
      style={{ top: y, left: x }}
    >
      <button
        onClick={onRename}
        className="flex w-full items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
      >
        Rename
      </button>
      <button
        onClick={onDelete}
        className="flex w-full items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
      >
        Delete
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sidebar item
// ---------------------------------------------------------------------------

function SidebarItem({
  active,
  onClick,
  icon,
  label,
  count,
  colorDot,
  onContextMenu,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
  count: number;
  colorDot?: string;
  onContextMenu?: (e: React.MouseEvent) => void;
}) {
  return (
    <button
      onClick={onClick}
      onContextMenu={onContextMenu}
      className={`flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors ${
        active
          ? "bg-brand-50 text-brand-700 font-medium"
          : "text-gray-700 hover:bg-gray-100"
      }`}
    >
      {colorDot ? (
        <span
          className="inline-block h-2.5 w-2.5 flex-shrink-0 rounded-full"
          style={{ backgroundColor: colorDot }}
        />
      ) : (
        <span className="flex-shrink-0 text-gray-400">{icon}</span>
      )}
      <span className="flex-1 truncate text-left">{label}</span>
      <span
        className={`text-xs tabular-nums ${
          active ? "text-brand-500" : "text-gray-400"
        }`}
      >
        {count}
      </span>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function CollectionsSidebar({
  activeFilter,
  onFilterChange,
  assetCounts,
}: CollectionsSidebarProps) {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null);
  const [creatingNew, setCreatingNew] = useState(false);
  const [newName, setNewName] = useState("");
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const newInputRef = useRef<HTMLInputElement>(null);
  const renameInputRef = useRef<HTMLInputElement>(null);

  // Load collections from localStorage on mount
  useEffect(() => {
    setCollections(loadCollections());
  }, []);

  // Persist whenever collections change (skip initial empty load)
  const didMount = useRef(false);
  useEffect(() => {
    if (!didMount.current) {
      didMount.current = true;
      return;
    }
    saveCollections(collections);
  }, [collections]);

  // Focus new/rename inputs
  useEffect(() => {
    if (creatingNew) newInputRef.current?.focus();
  }, [creatingNew]);
  useEffect(() => {
    if (renamingId) renameInputRef.current?.focus();
  }, [renamingId]);

  // ------ handlers ------

  const handleCreateCollection = useCallback(() => {
    const trimmed = newName.trim();
    if (!trimmed) {
      setCreatingNew(false);
      setNewName("");
      return;
    }
    const color = PRESET_COLORS[collections.length % PRESET_COLORS.length];
    const newCollection: Collection = {
      id: `col_${Date.now()}`,
      name: trimmed,
      color,
      assetIds: [],
    };
    setCollections((prev) => [...prev, newCollection]);
    setNewName("");
    setCreatingNew(false);
  }, [newName, collections.length]);

  const handleRename = useCallback(() => {
    const trimmed = renameValue.trim();
    if (!trimmed || !renamingId) {
      setRenamingId(null);
      setRenameValue("");
      return;
    }
    setCollections((prev) =>
      prev.map((c) => (c.id === renamingId ? { ...c, name: trimmed } : c))
    );
    setRenamingId(null);
    setRenameValue("");
  }, [renameValue, renamingId]);

  const handleDeleteCollection = useCallback(
    (id: string) => {
      setCollections((prev) => prev.filter((c) => c.id !== id));
      setContextMenu(null);
      // If the deleted collection was active, switch to "all"
      if (activeFilter === `collection:${id}`) {
        onFilterChange("all");
      }
    },
    [activeFilter, onFilterChange]
  );

  const openContextMenu = useCallback(
    (e: React.MouseEvent, collectionId: string) => {
      e.preventDefault();
      setContextMenu({ collectionId, x: e.clientX, y: e.clientY });
    },
    []
  );

  const startRename = useCallback(
    (id: string) => {
      const col = collections.find((c) => c.id === id);
      if (col) {
        setRenameValue(col.name);
        setRenamingId(id);
      }
      setContextMenu(null);
    },
    [collections]
  );

  return (
    <aside className="flex h-full w-60 flex-col border-r border-gray-200 bg-white">
      {/* Header */}
      <div className="border-b border-gray-200 px-4 py-3">
        <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">
          Library
        </h2>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {/* All Assets */}
        <SidebarItem
          active={activeFilter === "all"}
          onClick={() => onFilterChange("all")}
          icon={<FolderIcon />}
          label="All Assets"
          count={assetCounts.total}
        />

        {/* Type filters */}
        <div className="pt-1">
          <SidebarItem
            active={activeFilter === "image"}
            onClick={() => onFilterChange("image")}
            icon={<ImageIcon />}
            label="Images"
            count={assetCounts.image}
          />
          <SidebarItem
            active={activeFilter === "audio"}
            onClick={() => onFilterChange("audio")}
            icon={<AudioIcon />}
            label="Audio"
            count={assetCounts.audio}
          />
          <SidebarItem
            active={activeFilter === "video"}
            onClick={() => onFilterChange("video")}
            icon={<VideoIcon />}
            label="Videos"
            count={assetCounts.video}
          />
        </div>

        {/* Separator */}
        <div className="my-2 border-t border-gray-200" />

        {/* Collections header */}
        <div className="flex items-center justify-between px-3 py-1">
          <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">
            Collections
          </span>
          <button
            onClick={() => setCreatingNew(true)}
            className="rounded p-0.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
            title="New Collection"
          >
            <PlusIcon />
          </button>
        </div>

        {/* Collection items */}
        {collections.map((col) => {
          if (renamingId === col.id) {
            return (
              <div key={col.id} className="px-3 py-1">
                <input
                  ref={renameInputRef}
                  type="text"
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  onBlur={handleRename}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleRename();
                    if (e.key === "Escape") {
                      setRenamingId(null);
                      setRenameValue("");
                    }
                  }}
                  className="w-full rounded border border-brand-400 bg-white px-2 py-1 text-sm text-gray-700 focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>
            );
          }

          const count = assetCounts.collections[col.id] ?? 0;
          return (
            <SidebarItem
              key={col.id}
              active={activeFilter === `collection:${col.id}`}
              onClick={() => onFilterChange(`collection:${col.id}`)}
              icon={null}
              label={col.name}
              count={count}
              colorDot={col.color}
              onContextMenu={(e) => openContextMenu(e, col.id)}
            />
          );
        })}

        {/* Inline new collection input */}
        {creatingNew && (
          <div className="px-3 py-1">
            <input
              ref={newInputRef}
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onBlur={handleCreateCollection}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleCreateCollection();
                if (e.key === "Escape") {
                  setCreatingNew(false);
                  setNewName("");
                }
              }}
              placeholder="Collection name..."
              className="w-full rounded border border-brand-400 bg-white px-2 py-1 text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>
        )}

        {/* "+ New Collection" button (when not creating) */}
        {!creatingNew && (
          <button
            onClick={() => setCreatingNew(true)}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
          >
            <PlusIcon />
            <span>New Collection</span>
          </button>
        )}
      </div>

      {/* Context menu */}
      {contextMenu && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          onRename={() => startRename(contextMenu.collectionId)}
          onDelete={() => handleDeleteCollection(contextMenu.collectionId)}
          onClose={() => setContextMenu(null)}
        />
      )}
    </aside>
  );
}
