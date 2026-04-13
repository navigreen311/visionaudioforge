"use client";

import React, { useState } from "react";

type Role = "Admin" | "Editor" | "Viewer";

interface InviteRow {
  email: string;
  role: Role;
}

const emptyRow = (): InviteRow => ({ email: "", role: "Viewer" });

interface WizardStep4Props {
  onComplete: (invites: InviteRow[]) => void;
  onSkip: () => void;
}

export default function WizardStep4({ onComplete, onSkip }: WizardStep4Props) {
  const [rows, setRows] = useState<InviteRow[]>([emptyRow()]);

  const updateRow = (index: number, field: keyof InviteRow, value: string) => {
    setRows((prev) =>
      prev.map((r, i) =>
        i === index ? { ...r, [field]: value } : r
      )
    );
  };

  const addRow = () => {
    if (rows.length < 3) {
      setRows((prev) => [...prev, emptyRow()]);
    }
  };

  const hasValidEmail = rows.some((r) => r.email.trim().length > 0);

  return (
    <div className="flex flex-col items-center text-center px-6 py-8">
      <h2 className="text-2xl font-bold text-gray-900 mb-2">
        Work better together
      </h2>
      <p className="text-gray-500 mb-8">
        Invite your team to collaborate in your workspace.
      </p>

      <div className="w-full max-w-sm space-y-3 mb-6">
        {rows.map((row, idx) => (
          <div key={idx} className="flex gap-2">
            <input
              type="email"
              placeholder="colleague@example.com"
              value={row.email}
              onChange={(e) => updateRow(idx, "email", e.target.value)}
              className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none"
            />
            <select
              value={row.role}
              onChange={(e) => updateRow(idx, "role", e.target.value)}
              className="rounded-lg border border-gray-300 px-2 py-2 text-sm text-gray-700 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none"
            >
              <option value="Admin">Admin</option>
              <option value="Editor">Editor</option>
              <option value="Viewer">Viewer</option>
            </select>
          </div>
        ))}
      </div>

      {rows.length < 3 && (
        <button
          onClick={addRow}
          className="text-sm text-blue-600 hover:text-blue-700 font-medium mb-8"
        >
          + Add another
        </button>
      )}

      <div className="flex gap-3 mt-2">
        <button
          onClick={onSkip}
          className="rounded-lg border border-gray-300 px-6 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          Skip for now
        </button>
        <button
          disabled={!hasValidEmail}
          onClick={() => onComplete(rows.filter((r) => r.email.trim()))}
          className="rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Send Invites
        </button>
      </div>
    </div>
  );
}
