"use client";

import React, { useCallback, useState } from "react";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface KeyRevealModalProps {
  isOpen: boolean;
  onClose: () => void;
  fullKey: string;
  keyName: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function KeyRevealModal({
  isOpen,
  onClose,
  fullKey,
  keyName,
}: KeyRevealModalProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(fullKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for non-secure contexts
      const textarea = document.createElement("textarea");
      textarea.value = fullKey;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [fullKey]);

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => {
        /* prevent closing via overlay / Escape */
      }}
      title={`API Key Created — ${keyName}`}
      footer={
        <Button onClick={onClose} disabled={!copied}>
          I&apos;ve copied the key
        </Button>
      }
    >
      <div className="space-y-4">
        {/* Warning */}
        <div className="rounded-lg border border-yellow-300 bg-yellow-50 p-3">
          <p className="text-sm font-semibold text-yellow-800">
            This key will never be shown again.
          </p>
          <p className="mt-1 text-xs text-yellow-700">
            Copy it now and store it securely. If you lose it you will need to
            create a new key.
          </p>
        </div>

        {/* Key display */}
        <div className="relative">
          <pre className="overflow-x-auto rounded-lg border border-gray-300 bg-gray-900 p-4 text-sm font-mono text-green-400 select-all">
            {fullKey}
          </pre>
          <button
            type="button"
            onClick={handleCopy}
            className="absolute right-2 top-2 rounded bg-gray-700 px-2 py-1 text-xs font-medium text-gray-200 hover:bg-gray-600 transition-colors"
          >
            {copied ? "Copied!" : "Copy"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
