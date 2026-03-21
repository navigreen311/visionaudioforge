"use client";

import { useCallback, useRef, useState } from "react";
import { Edge, Node, useEdgesState, useNodesState } from "reactflow";

import GenerateModal from "@/components/pipeline/GenerateModal";
import NodeConfig from "@/components/pipeline/NodeConfig";
import NodePalette from "@/components/pipeline/NodePalette";
import PipelineCanvas from "@/components/pipeline/PipelineCanvas";
import SavedPipelinesDrawer from "@/components/pipeline/SavedPipelinesDrawer";
import TemplatesModal from "@/components/pipeline/TemplatesModal";
import { PipelineTemplate } from "@/lib/pipeline-templates";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PipelineRun {
  id: string;
  status: string;
  created_at: string;
  duration_ms?: number;
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function PipelinePage() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);

  // Pipeline name (editable inline)
  const [pipelineName, setPipelineName] = useState("Untitled Pipeline");
  const [isEditingName, setIsEditingName] = useState(false);
  const nameInputRef = useRef<HTMLInputElement>(null);

  const [runs] = useState<PipelineRun[]>([]);
  const [validationMsg, setValidationMsg] = useState<string | null>(null);

  // Dirty tracking
  const [isDirty, setIsDirty] = useState(false);

  // Modal / drawer states
  const [showSavedDrawer, setShowSavedDrawer] = useState(false);
  const [showTemplatesModal, setShowTemplatesModal] = useState(false);
  const [showGenerateModal, setShowGenerateModal] = useState(false);

  // Schedule modal (inline)
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [scheduleFrequency, setScheduleFrequency] = useState("daily");
  const [scheduleTime, setScheduleTime] = useState("00:00");
  const [scheduleCron, setScheduleCron] = useState("0 0 * * *");

  // ---- Helpers ----

  const flash = (msg: string, durationMs = 5000) => {
    setValidationMsg(msg);
    setTimeout(() => setValidationMsg(null), durationMs);
  };

  // Build definition from React Flow state
  const buildDefinition = useCallback(() => {
    return {
      nodes: nodes.map((n) => ({
        id: n.id,
        type: n.data.nodeType || "unknown",
        params: n.data.params || {},
      })),
      edges: edges.map((e) => ({
        from: e.source,
        to: e.target,
        from_port: "output",
        to_port: "input",
      })),
    };
  }, [nodes, edges]);

  // Load a pipeline definition into the canvas
  const loadDefinitionToCanvas = useCallback(
    (definition: {
      nodes: Array<Record<string, unknown>>;
      edges: Array<Record<string, unknown>>;
    }) => {
      const newNodes: Node[] = definition.nodes.map(
        (n: Record<string, unknown>, i: number) => ({
          id: (n.id as string) || `node_${i}_${Date.now()}`,
          type: "pipeline",
          position: (n.position as { x: number; y: number }) || {
            x: 100 + i * 250,
            y: 100 + (i % 2) * 80,
          },
          data: {
            label: ((n.type as string) || "unknown")
              .replace(/_/g, " ")
              .replace(/\b\w/g, (c: string) => c.toUpperCase()),
            category: (n.category as string) || "Action",
            nodeType: (n.type as string) || "unknown",
            params:
              (n.params as Record<string, unknown>) ||
              (n.config as Record<string, unknown>) ||
              {},
          },
        })
      );
      const newEdges: Edge[] = definition.edges.map(
        (e: Record<string, unknown>, i: number) => ({
          id:
            (e.id as string) ||
            `e-${i}-${e.from || e.source}-${e.to || e.target}`,
          source: (e.from as string) || (e.source as string) || "",
          target: (e.to as string) || (e.target as string) || "",
        })
      );
      setNodes(newNodes);
      setEdges(newEdges);
      setIsDirty(false);
    },
    [setNodes, setEdges]
  );

  // ---- Pipeline name editing ----

  const handleNameClick = () => {
    setIsEditingName(true);
    setTimeout(() => nameInputRef.current?.select(), 0);
  };

  const handleNameBlur = () => {
    setIsEditingName(false);
    if (!pipelineName.trim()) {
      setPipelineName("Untitled Pipeline");
    }
  };

  const handleNameKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      nameInputRef.current?.blur();
    }
    if (e.key === "Escape") {
      setIsEditingName(false);
    }
  };

  // ---- Saved Pipelines Drawer ----

  const handleLoadSavedPipeline = (pipeline: {
    name: string;
    definition: {
      nodes: Array<Record<string, unknown>>;
      edges: Array<Record<string, unknown>>;
    };
  }) => {
    setPipelineName(pipeline.name);
    loadDefinitionToCanvas(pipeline.definition);
    setShowSavedDrawer(false);
    flash("Pipeline loaded");
  };

  // ---- Templates Modal ----

  const handleSelectTemplate = (template: PipelineTemplate) => {
    const definition = {
      nodes: template.nodes.map((n) => ({
        id: n.id,
        type: n.type,
        position: n.position,
        config: n.config,
      })),
      edges: template.edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
      })),
    };
    loadDefinitionToCanvas(definition);
    setPipelineName(template.name);
    flash(`Loaded template: ${template.name}`);
  };

  // ---- Generate Modal ----

  const handleGenerated = (pipeline: {
    nodes: Array<Record<string, unknown>>;
    edges: Array<Record<string, unknown>>;
  }) => {
    loadDefinitionToCanvas(pipeline);
    flash("Pipeline generated from description!");
  };

  // ---- Schedule helpers ----

  const updateCronFromUI = (frequency: string, time: string) => {
    const [hours, minutes] = time.split(":").map(Number);
    switch (frequency) {
      case "hourly":
        setScheduleCron(`${minutes} * * * *`);
        break;
      case "daily":
        setScheduleCron(`${minutes} ${hours} * * *`);
        break;
      case "weekly":
        setScheduleCron(`${minutes} ${hours} * * 1`);
        break;
      case "monthly":
        setScheduleCron(`${minutes} ${hours} 1 * *`);
        break;
      default:
        setScheduleCron(`${minutes} ${hours} * * *`);
    }
  };

  const handleSchedule = async () => {
    try {
      const resp = await fetch("/api/pipeline/schedule", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pipeline_id: "00000000-0000-0000-0000-000000000000",
          cron: scheduleCron,
        }),
      });
      if (resp.ok) {
        const data = await resp.json();
        flash(`Scheduled! Next run: ${data.next_run}`);
        setShowScheduleModal(false);
      } else {
        const err = await resp.json();
        flash(`Schedule failed: ${err.detail}`);
      }
    } catch {
      flash("Schedule request failed");
    }
  };

  // ---- Toolbar actions ----

  const handleValidate = async () => {
    try {
      const resp = await fetch("/api/pipeline/validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ definition: buildDefinition() }),
      });
      const data = await resp.json();
      if (data.valid) {
        flash("Pipeline is valid!");
      } else {
        flash(`Errors: ${data.errors.join(", ")}`);
      }
    } catch {
      flash("Validation request failed");
    }
  };

  const handleSave = async () => {
    try {
      const resp = await fetch("/api/pipeline/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: pipelineName,
          definition: buildDefinition(),
          workspace_id: "00000000-0000-0000-0000-000000000000",
        }),
      });
      if (resp.ok) {
        setIsDirty(false);
        flash("Pipeline saved!");
      } else {
        const err = await resp.json();
        flash(`Save failed: ${JSON.stringify(err.detail)}`);
      }
    } catch {
      flash("Save request failed");
    }
  };

  const handleRun = () => {
    flash("Pipeline run dispatched (requires saved pipeline)", 3000);
  };

  const handleClear = () => {
    setNodes([]);
    setEdges([]);
    setSelectedNode(null);
    setIsDirty(false);
  };

  const handleNodeParamsUpdate = useCallback(
    (nodeId: string, params: Record<string, unknown>) => {
      setNodes((nds) =>
        nds.map((n) =>
          n.id === nodeId ? { ...n, data: { ...n.data, params } } : n
        )
      );
      setIsDirty(true);
    },
    [setNodes]
  );

  // Mark dirty when nodes/edges change
  const wrappedOnNodesChange: typeof onNodesChange = useCallback(
    (changes) => {
      onNodesChange(changes);
      setIsDirty(true);
    },
    [onNodesChange]
  );

  const wrappedOnEdgesChange: typeof onEdgesChange = useCallback(
    (changes) => {
      onEdgesChange(changes);
      setIsDirty(true);
    },
    [onEdgesChange]
  );

  const canvasEmpty = nodes.length === 0;

  return (
    <div className="flex flex-col h-[calc(100vh-64px)]">
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-4 py-2 bg-white border-b border-gray-200">
        {/* Saved Pipelines button */}
        <button
          onClick={() => setShowSavedDrawer(true)}
          className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-gray-700 transition-colors"
          title="Saved Pipelines"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 6h16M4 12h16M4 18h7"
            />
          </svg>
        </button>

        {/* Editable pipeline name */}
        {isEditingName ? (
          <input
            ref={nameInputRef}
            type="text"
            value={pipelineName}
            onChange={(e) => {
              setPipelineName(e.target.value);
              setIsDirty(true);
            }}
            onBlur={handleNameBlur}
            onKeyDown={handleNameKeyDown}
            className="text-lg font-semibold text-gray-800 bg-white border border-brand-300 rounded px-2 py-0.5 focus:outline-none focus:ring-2 focus:ring-brand-400"
            autoFocus
          />
        ) : (
          <button
            onClick={handleNameClick}
            className="text-lg font-semibold text-gray-800 hover:text-brand-600 transition-colors flex items-center gap-1.5 group"
            title="Click to rename"
          >
            {pipelineName}
            <svg
              className="w-3.5 h-3.5 text-gray-300 group-hover:text-brand-400 transition-colors"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
              />
            </svg>
          </button>
        )}
        {isDirty && (
          <span className="text-xs text-gray-400 italic">unsaved</span>
        )}

        <div className="flex-1" />

        <button
          onClick={() => setShowGenerateModal(true)}
          className="px-3 py-1.5 text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 rounded-md transition-colors"
        >
          Generate from Description
        </button>
        <button
          onClick={() => setShowTemplatesModal(true)}
          className="px-3 py-1.5 text-sm font-medium text-purple-700 bg-purple-50 hover:bg-purple-100 rounded-md transition-colors"
        >
          Templates
        </button>
        <button
          onClick={() => setShowScheduleModal(true)}
          className="px-3 py-1.5 text-sm font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-md transition-colors"
        >
          Schedule
        </button>
        <button
          onClick={handleValidate}
          className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
        >
          Validate
        </button>
        <button
          onClick={handleSave}
          className="px-3 py-1.5 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-md transition-colors"
        >
          Save
        </button>
        <button
          onClick={handleRun}
          className="px-3 py-1.5 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-md transition-colors"
        >
          Run
        </button>
        <button
          onClick={handleClear}
          className="px-3 py-1.5 text-sm font-medium text-red-600 bg-red-50 hover:bg-red-100 rounded-md transition-colors"
        >
          Clear
        </button>
        {validationMsg && (
          <span className="text-sm text-gray-600 bg-yellow-50 px-2 py-1 rounded border border-yellow-200">
            {validationMsg}
          </span>
        )}
      </div>

      {/* Main area: palette + canvas + config */}
      <div className="flex flex-1 overflow-hidden">
        <NodePalette />
        <PipelineCanvas
          onNodeSelect={setSelectedNode}
          onNodeParamsUpdate={handleNodeParamsUpdate}
          nodesState={[nodes, setNodes, wrappedOnNodesChange]}
          edgesState={[edges, setEdges, wrappedOnEdgesChange]}
        />
        <NodeConfig node={selectedNode} onUpdate={handleNodeParamsUpdate} />
      </div>

      {/* Run history panel */}
      <div className="h-36 bg-white border-t border-gray-200 overflow-y-auto">
        <div className="px-4 py-2 border-b border-gray-100">
          <h4 className="text-sm font-semibold text-gray-600">Run History</h4>
        </div>
        {runs.length === 0 ? (
          <div className="flex items-center justify-center h-20 text-sm text-gray-400">
            No pipeline runs yet
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b border-gray-100">
                <th className="px-4 py-1 font-medium">Run ID</th>
                <th className="px-4 py-1 font-medium">Status</th>
                <th className="px-4 py-1 font-medium">Duration</th>
                <th className="px-4 py-1 font-medium">Started</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id} className="border-b border-gray-50">
                  <td className="px-4 py-1 font-mono text-xs">
                    {run.id.slice(0, 8)}
                  </td>
                  <td className="px-4 py-1">
                    <span
                      className={`inline-block px-1.5 py-0.5 rounded text-xs font-medium ${
                        run.status === "completed"
                          ? "bg-green-100 text-green-700"
                          : run.status === "failed"
                            ? "bg-red-100 text-red-700"
                            : "bg-yellow-100 text-yellow-700"
                      }`}
                    >
                      {run.status}
                    </span>
                  </td>
                  <td className="px-4 py-1">
                    {run.duration_ms ? `${run.duration_ms}ms` : "-"}
                  </td>
                  <td className="px-4 py-1 text-gray-500">
                    {new Date(run.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* --- Modals & Drawers --- */}

      <SavedPipelinesDrawer
        isOpen={showSavedDrawer}
        onClose={() => setShowSavedDrawer(false)}
        onLoad={handleLoadSavedPipeline}
        hasUnsavedChanges={isDirty}
      />

      <TemplatesModal
        isOpen={showTemplatesModal}
        onClose={() => setShowTemplatesModal(false)}
        onSelect={handleSelectTemplate}
        canvasEmpty={canvasEmpty}
      />

      <GenerateModal
        isOpen={showGenerateModal}
        onClose={() => setShowGenerateModal(false)}
        onGenerated={handleGenerated}
      />

      {/* Schedule Modal (inline) */}
      {showScheduleModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">
              Schedule Pipeline
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Frequency
                </label>
                <select
                  value={scheduleFrequency}
                  onChange={(e) => {
                    setScheduleFrequency(e.target.value);
                    updateCronFromUI(e.target.value, scheduleTime);
                  }}
                  className="w-full border border-gray-300 rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                >
                  <option value="hourly">Hourly</option>
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly (Monday)</option>
                  <option value="monthly">Monthly (1st)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Time
                </label>
                <input
                  type="time"
                  value={scheduleTime}
                  onChange={(e) => {
                    setScheduleTime(e.target.value);
                    updateCronFromUI(scheduleFrequency, e.target.value);
                  }}
                  className="w-full border border-gray-300 rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <span className="text-xs text-gray-500">
                  Cron expression:{" "}
                </span>
                <code className="text-sm font-mono text-gray-700">
                  {scheduleCron}
                </code>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowScheduleModal(false)}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
              >
                Cancel
              </button>
              <button
                onClick={handleSchedule}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
              >
                Schedule
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
