"use client";

import { useEffect, useState } from "react";

interface ShortcutEntry {
  keys: string;
  description: string;
}

interface ShortcutSection {
  title: string;
  shortcuts: ShortcutEntry[];
}

const sections: ShortcutSection[] = [
  {
    title: "NAVIGATION",
    shortcuts: [
      { keys: "Ctrl+K", description: "Command palette" },
      { keys: "/", description: "Focus search" },
      { keys: "?", description: "Shortcuts" },
      { keys: "Esc", description: "Close modal" },
    ],
  },
  {
    title: "PIPELINE BUILDER",
    shortcuts: [
      { keys: "Ctrl+S", description: "Save" },
      { keys: "Ctrl+Z", description: "Undo" },
      { keys: "Ctrl+Shift+Z", description: "Redo" },
    ],
  },
  {
    title: "ANNOTATION STUDIO",
    shortcuts: [
      { keys: "B", description: "Bbox" },
      { keys: "P", description: "Polygon" },
      { keys: "K", description: "Keypoint" },
      { keys: "L", description: "Label" },
      { keys: "Del", description: "Delete" },
      { keys: "\u2190 / \u2192", description: "Prev / Next" },
    ],
  },
  {
    title: "COPILOT",
    shortcuts: [{ keys: "Ctrl+Enter", description: "Send message" }],
  },
];

export default function ShortcutsModal() {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    function handleOpen() {
      setIsOpen(true);
    }

    function handleClose() {
      setIsOpen(false);
    }

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setIsOpen(false);
      }
    }

    window.addEventListener("open-shortcuts-modal", handleOpen);
    window.addEventListener("close-modals", handleClose);
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("open-shortcuts-modal", handleOpen);
      window.removeEventListener("close-modals", handleClose);
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[150] flex items-center justify-center bg-black/50"
      onClick={() => setIsOpen(false)}
    >
      <div
        className="w-full max-w-lg rounded-xl bg-white p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-4 text-lg font-semibold text-gray-900">
          Keyboard Shortcuts
        </h2>

        <div className="grid grid-cols-2 gap-6">
          {sections.map((section) => (
            <div key={section.title}>
              <h3 className="mb-2 text-xs font-bold uppercase tracking-wider text-gray-500">
                {section.title}
              </h3>
              <ul className="space-y-1">
                {section.shortcuts.map((shortcut) => (
                  <li
                    key={shortcut.description}
                    className="flex items-center justify-between text-sm"
                  >
                    <span className="text-gray-700">{shortcut.description}</span>
                    <kbd className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-xs text-gray-600">
                      {shortcut.keys}
                    </kbd>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
