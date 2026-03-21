"use client";

import React, { useEffect, useState, useCallback } from "react";
import Card from "@/components/ui/Card";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface ScenarioTemplate {
  id: string;
  name: string;
  description: string;
  scenarioType: string;
  parameters: Record<string, string | number | boolean>;
  createdAt: string;
}

interface ScenarioTemplatesProps {
  onLoadTemplate: (template: ScenarioTemplate) => void;
}

interface SaveTemplateModalProps {
  open: boolean;
  onClose: () => void;
  onSave: (name: string, description: string) => void;
  defaultName?: string;
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const STORAGE_KEY = "vaf_sim_templates";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function loadTemplates(): ScenarioTemplate[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as ScenarioTemplate[];
  } catch {
    return [];
  }
}

function saveTemplates(templates: ScenarioTemplate[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(templates));
  } catch {
    /* storage full or unavailable — silently ignore */
  }
}

function generateId(): string {
  return `tpl_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

/* ------------------------------------------------------------------ */
/*  Save-as-Template Modal                                             */
/* ------------------------------------------------------------------ */

export function SaveTemplateModal({
  open,
  onClose,
  onSave,
  defaultName = "",
}: SaveTemplateModalProps) {
  const [name, setName] = useState(defaultName);
  const [description, setDescription] = useState("");

  useEffect(() => {
    if (open) {
      setName(defaultName);
      setDescription("");
    }
  }, [open, defaultName]);

  if (!open) return null;

  const handleSave = () => {
    if (!name.trim()) return;
    onSave(name.trim(), description.trim());
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h3 className="text-base font-semibold text-gray-900">
          Save as Template
        </h3>

        <div className="mt-4 space-y-3">
          <div>
            <label
              htmlFor="tpl-name"
              className="block text-sm font-medium text-gray-700"
            >
              Template Name
            </label>
            <input
              id="tpl-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="e.g. High-load stress test"
            />
          </div>
          <div>
            <label
              htmlFor="tpl-desc"
              className="block text-sm font-medium text-gray-700"
            >
              Description
            </label>
            <textarea
              id="tpl-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="Describe what this template tests..."
            />
          </div>
        </div>

        <div className="mt-5 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!name.trim()}
            className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export default function ScenarioTemplates({
  onLoadTemplate,
}: ScenarioTemplatesProps) {
  const [templates, setTemplates] = useState<ScenarioTemplate[]>([]);
  const [expanded, setExpanded] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");

  /* Load from localStorage on mount */
  useEffect(() => {
    setTemplates(loadTemplates());
  }, []);

  /* Persist whenever templates change */
  const persist = useCallback((next: ScenarioTemplate[]) => {
    setTemplates(next);
    saveTemplates(next);
  }, []);

  const handleDelete = useCallback(
    (id: string) => {
      persist(templates.filter((t) => t.id !== id));
      if (editingId === id) setEditingId(null);
    },
    [templates, persist, editingId]
  );

  const startEdit = useCallback((tpl: ScenarioTemplate) => {
    setEditingId(tpl.id);
    setEditName(tpl.name);
    setEditDesc(tpl.description);
  }, []);

  const commitEdit = useCallback(() => {
    if (!editingId || !editName.trim()) return;
    persist(
      templates.map((t) =>
        t.id === editingId
          ? { ...t, name: editName.trim(), description: editDesc.trim() }
          : t
      )
    );
    setEditingId(null);
  }, [editingId, editName, editDesc, templates, persist]);

  const cancelEdit = useCallback(() => {
    setEditingId(null);
  }, []);

  return (
    <Card>
      {/* Collapsible header */}
      <button
        onClick={() => setExpanded((prev) => !prev)}
        className="flex w-full items-center justify-between text-left"
      >
        <h3 className="text-base font-semibold text-gray-900">
          Scenario Templates
          {templates.length > 0 && (
            <span className="ml-2 text-xs font-normal text-gray-400">
              ({templates.length})
            </span>
          )}
        </h3>
        <svg
          className={`h-5 w-5 text-gray-400 transition-transform ${
            expanded ? "rotate-180" : ""
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {expanded && (
        <div className="mt-4">
          {templates.length === 0 && (
            <div className="flex flex-col items-center py-8 text-gray-400">
              <svg
                className="mb-2 h-8 w-8"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                />
              </svg>
              <p className="text-sm">No templates saved</p>
              <p className="text-xs">
                Save a scenario to create reusable templates.
              </p>
            </div>
          )}

          {templates.length > 0 && (
            <ul className="divide-y divide-gray-100">
              {templates.map((tpl) => (
                <li key={tpl.id} className="py-3 first:pt-0 last:pb-0">
                  {editingId === tpl.id ? (
                    /* Inline edit form */
                    <div className="space-y-2">
                      <input
                        type="text"
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      />
                      <textarea
                        value={editDesc}
                        onChange={(e) => setEditDesc(e.target.value)}
                        rows={2}
                        className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={commitEdit}
                          disabled={!editName.trim()}
                          className="rounded bg-blue-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-blue-700 transition-colors disabled:opacity-50"
                        >
                          Save
                        </button>
                        <button
                          onClick={cancelEdit}
                          className="rounded border border-gray-300 px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    /* Template row */
                    <div className="flex items-start gap-3">
                      <div className="min-w-0 flex-1">
                        <p className="font-medium text-gray-900">
                          {tpl.name}
                        </p>
                        {tpl.description && (
                          <p className="mt-0.5 text-xs text-gray-500">
                            {tpl.description}
                          </p>
                        )}
                      </div>
                      <div className="flex gap-1.5">
                        <button
                          onClick={() => onLoadTemplate(tpl)}
                          className="rounded border border-blue-300 bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100 transition-colors"
                        >
                          Run
                        </button>
                        <button
                          onClick={() => startEdit(tpl)}
                          className="rounded border border-gray-300 px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(tpl.id)}
                          className="rounded border border-red-300 bg-red-50 px-2.5 py-1 text-xs font-medium text-red-700 hover:bg-red-100 transition-colors"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/*  Helper to create a template from scenario results                  */
/* ------------------------------------------------------------------ */

export function createTemplateFromResults(
  name: string,
  description: string,
  scenarioType: string,
  parameters: Record<string, string | number | boolean>
): ScenarioTemplate {
  const template: ScenarioTemplate = {
    id: generateId(),
    name,
    description,
    scenarioType,
    parameters,
    createdAt: new Date().toISOString(),
  };
  const existing = loadTemplates();
  saveTemplates([...existing, template]);
  return template;
}
