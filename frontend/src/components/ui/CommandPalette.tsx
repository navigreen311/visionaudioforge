"use client";

import { useEffect, useState, useRef, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { pages, actions, type CommandItem } from "@/lib/command-actions";

const RECENT_KEY = "vaf_recent_commands";
const MAX_RECENT = 5;

function loadRecent(): CommandItem[] {
  try {
    const raw = localStorage.getItem(RECENT_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.slice(0, MAX_RECENT) : [];
  } catch {
    return [];
  }
}

function saveRecent(item: CommandItem) {
  try {
    const existing = loadRecent().filter((r) => r.id !== item.id);
    const updated = [item, ...existing].slice(0, MAX_RECENT);
    localStorage.setItem(RECENT_KEY, JSON.stringify(updated));
  } catch {
    // ignore localStorage errors
  }
}

export default function CommandPalette() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  const recent = useMemo(() => {
    if (!isOpen) return [];
    return loadRecent();
  }, [isOpen]);

  const filteredPages = useMemo(() => {
    if (!query.trim()) return pages;
    const q = query.toLowerCase();
    return pages.filter(
      (p) =>
        p.title.toLowerCase().includes(q) ||
        p.subtitle.toLowerCase().includes(q)
    );
  }, [query]);

  const filteredActions = useMemo(() => {
    if (!query.trim()) return actions;
    const q = query.toLowerCase();
    return actions.filter(
      (a) =>
        a.title.toLowerCase().includes(q) ||
        a.subtitle.toLowerCase().includes(q)
    );
  }, [query]);

  const allItems = useMemo(() => {
    const items: CommandItem[] = [];
    if (!query.trim() && recent.length > 0) {
      items.push(...recent);
    }
    items.push(...filteredPages);
    items.push(...filteredActions);
    return items;
  }, [query, recent, filteredPages, filteredActions]);

  const open = useCallback(() => {
    setIsOpen(true);
    setQuery("");
    setSelectedIndex(0);
  }, []);

  const close = useCallback(() => {
    setIsOpen(false);
    setQuery("");
    setSelectedIndex(0);
  }, []);

  const execute = useCallback(
    (item: CommandItem) => {
      saveRecent(item);
      router.push(item.url);
      close();
    },
    [router, close]
  );

  useEffect(() => {
    function handleOpen() {
      open();
    }

    function handleClose() {
      close();
    }

    function handleKeyDown(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        if (isOpen) {
          close();
        } else {
          open();
        }
      }
    }

    window.addEventListener("open-command-palette", handleOpen);
    window.addEventListener("close-modals", handleClose);
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("open-command-palette", handleOpen);
      window.removeEventListener("close-modals", handleClose);
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, open, close]);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  function handleInputKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => Math.min(prev + 1, allItems.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => Math.max(prev - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (allItems[selectedIndex]) {
        execute(allItems[selectedIndex]);
      }
    } else if (e.key === "Escape") {
      e.preventDefault();
      close();
    }
  }

  if (!isOpen) return null;

  // Compute section boundaries for rendering
  const recentItems = !query.trim() ? recent : [];
  const recentOffset = 0;
  const pagesOffset = recentItems.length;
  const actionsOffset = pagesOffset + filteredPages.length;

  return (
    <div
      className="fixed inset-0 z-[160] flex justify-center bg-black/30"
      onClick={close}
    >
      <div
        className="mt-[20vh] h-fit w-full max-w-xl rounded-xl bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="border-b border-gray-200 p-4">
          <input
            ref={inputRef}
            type="text"
            className="w-full bg-transparent text-sm text-gray-900 placeholder-gray-400 outline-none"
            placeholder="Search pages, run actions, or find anything..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleInputKeyDown}
          />
        </div>

        <div className="max-h-[50vh] overflow-y-auto p-2">
          {recentItems.length > 0 && (
            <div className="mb-2">
              <p className="px-2 py-1 text-xs font-bold uppercase tracking-wider text-gray-500">
                Recent
              </p>
              {recentItems.map((item, i) => {
                const idx = recentOffset + i;
                return (
                  <button
                    key={item.id}
                    className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm ${
                      selectedIndex === idx
                        ? "bg-blue-50 text-blue-700"
                        : "text-gray-700 hover:bg-gray-50"
                    }`}
                    onClick={() => execute(item)}
                    onMouseEnter={() => setSelectedIndex(idx)}
                  >
                    <span className="text-base">{item.icon}</span>
                    <div>
                      <span className="font-medium">{item.title}</span>
                      <span className="ml-2 text-xs text-gray-400">
                        {item.subtitle}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          {filteredPages.length > 0 && (
            <div className="mb-2">
              <p className="px-2 py-1 text-xs font-bold uppercase tracking-wider text-gray-500">
                Pages
              </p>
              {filteredPages.map((item, i) => {
                const idx = pagesOffset + i;
                return (
                  <button
                    key={item.id}
                    className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm ${
                      selectedIndex === idx
                        ? "bg-blue-50 text-blue-700"
                        : "text-gray-700 hover:bg-gray-50"
                    }`}
                    onClick={() => execute(item)}
                    onMouseEnter={() => setSelectedIndex(idx)}
                  >
                    <span className="text-base">{item.icon}</span>
                    <div>
                      <span className="font-medium">{item.title}</span>
                      <span className="ml-2 text-xs text-gray-400">
                        {item.subtitle}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          {filteredActions.length > 0 && (
            <div className="mb-2">
              <p className="px-2 py-1 text-xs font-bold uppercase tracking-wider text-gray-500">
                Actions
              </p>
              {filteredActions.map((item, i) => {
                const idx = actionsOffset + i;
                return (
                  <button
                    key={item.id}
                    className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm ${
                      selectedIndex === idx
                        ? "bg-blue-50 text-blue-700"
                        : "text-gray-700 hover:bg-gray-50"
                    }`}
                    onClick={() => execute(item)}
                    onMouseEnter={() => setSelectedIndex(idx)}
                  >
                    <span className="text-base">{item.icon}</span>
                    <div>
                      <span className="font-medium">{item.title}</span>
                      <span className="ml-2 text-xs text-gray-400">
                        {item.subtitle}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          {allItems.length === 0 && (
            <p className="px-3 py-6 text-center text-sm text-gray-400">
              No results found
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
