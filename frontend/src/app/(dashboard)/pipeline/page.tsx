"use client";

import { useCallback, useEffect, useState } from "react";
import { Edge, Node, useEdgesState, useNodesState } from "reactflow";

import NodeConfig from "@/components/pipeline/NodeConfig";
import NodePalette from "@/components/pipeline/NodePalette";
import PipelineCanvas from "@/components/pipeline/PipelineCanvas";

interface PipelineRun {
  id: string;
  status: string;
  created_at: string;
  duration_ms?: number;
}

interface PipelineTemplate {
  key: string;
  name: string;
  description: string;
  category: string;
  definition: { nodes: any[]; edges: any[] };
}

export default function PipelinePage() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [pipelineName, setPipelineName] = useState("Untitled Pipeline");
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [validationMsg, setValidationMsg] = useState<string | null>(null);

  // Modal states
  const [showGenerateModal, setShowGenerateModal] = useState(false);
  const [generateDescription, setGenerateDescription] = useState("");
  const [generating, setGenerating] = useState(false);

  const [showTemplatesPanel, setShowTemplatesPanel] = useState(false);
  const [templates, setTemplates] = useState<PipelineTemplate[]>([]);
  const [loadingTemplates, setLoadingTemplates] = useState(false);

  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [scheduleFrequency, setScheduleFrequency] = useState("daily");
  const [scheduleTime, setScheduleTime] = useState("00:00");
  const [scheduleCron, setScheduleCron] = useState("0 0 * * *");

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
    (definition: { nodes: any[]; edges: any[] }) => {
      const newNodes: Node[] = definition.nodes.map(
        (n: any, i: number) => ({
          id: n.id,
          type: "default",
          position: { x: 100 + i * 250, y: 100 + (i % 2) * 80 },
          data: {
            label: n.type.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase()),
            nodeType: n.type,
            params: n.params || {},
          },
        }),
      );
      const newEdges: Edge[] = definition.edges.map(
        (e: any, i: number) => ({
          id: `e-${i}-${e.from}-${e.to}`,
          source: e.from,
          target: e.to,
        }),
      );
      setNodes(newNodes);
      setEdges(newEdges);
    },
    [setNodes, setEdges],
  );

  // --- Generate from Description ---
  const handleGenerate = async () => {
    if (!generateDescription.trim()) return;
    setGenerating(true);
    try {
      const resp = await fetch("/api/pipeline/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description: generateDescription }),
      });
      if (resp.ok) {
        const data = await resp.json();
        loadDefinitionToCanvas(data.definition);
        setShowGenerateModal(false);
        setGenerateDescription("");
        setValidationMsg("Pipeline generated from description!");
      } else {
        setValidationMsg("Generation failed");
      }
    } catch {
      setValidationMsg("Generation request failed");
    }
    setGenerating(false);
    setTimeout(() => setValidationMsg(null), 5000);
  };

  // --- Templates ---
  const handleLoadTemplates = async () => {
    setShowTemplatesPanel(!showTemplatesPanel);
    if (!showTemplatesPanel && templates.length === 0) {
      setLoadingTemplates(true);
      try {
        const resp = await fetch("/api/pipeline/templates");
        if (resp.ok) {
          const data = await resp.json();
          setTemplates(data);
        }
      } catch {
        setValidationMsg("Failed to load templates");
        setTimeout(() => setValidationMsg(null), 3000);
      }
      setLoadingTemplates(false);
    }
  };

  const handleSelectTemplate = (template: PipelineTemplate) => {
    loadDefinitionToCanvas(template.definition);
    setPipelineName(template.name);
    setShowTemplatesPanel(false);
    setValidationMsg(`Loaded template: ${template.name}`);
    setTimeout(() => setValidationMsg(null), 3000);
  };

  // --- Schedule ---
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
        setValidationMsg(`Scheduled! Next run: ${data.next_run}`);
        setShowScheduleModal(false);
      } else {
        const err = await resp.json();
        setValidationMsg(`Schedule failed: ${err.detail}`);
      }
    } catch {
      setValidationMsg("Schedule request failed");
    }
    setTimeout(() => setValidationMsg(null), 5000);
  };

  // Toolbar actions
  const handleValidate = async () => {
    try {
      const resp = await fetch("/api/pipeline/validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ definition: buildDefinition() }),
      });
      const data = await resp.json();
      if (data.valid) {
        setValidationMsg("Pipeline is valid!");
      } else {
        setValidationMsg(`Errors: ${data.errors.join(", ")}`);
      }
    } catch {
      setValidationMsg("Validation request failed");
    }
    setTimeout(() => setValidationMsg(null), 5000);
  };

  const handleSave = async () => {
    try {
      const resp = await fetch("/api/pipeline/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: pipelineName,
          definition: buildDefinition(),
          workspace_id: "00000000-0000-0000-0000-000000000000",
        }),
      });
      if (resp.ok) {
        setValidationMsg("Pipeline saved!");
      } else {
        const err = await resp.json();
        setValidationMsg(`Save failed: ${JSON.stringify(err.detail)}`);
      }
    } catch {
      setValidationMsg("Save request failed");
    }
    setTimeout(() => setValidationMsg(null), 5000);
  };

  const handleRun = async () => {
    setValidationMsg("Running pipeline...");
    setValidationMsg("Pipeline run dispatched (requires saved pipeline)");
    setTimeout(() => setValidationMsg(null), 3000);
  };

  const handleClear = () => {
    setNodes([]);
    setEdges([]);
    setSelectedNode(null);
  };

  const handleNodeParamsUpdate = useCallback(
    (nodeId: string, params: Record<string, unknown>) => {
      setNodes((nds) =>
        nds.map((n) =>
          n.id === nodeId ? { ...n, data: { ...n.data, params } } : n,
        ),
      );
    },
    [setNodes],
  );

  return (
    <div className="flex flex-col h-[calc(100vh-64px)]">
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-4 py-2 bg-white border-b border-gray-200">
        <input
          type="text"
          value={pipelineName}
          onChange={(e) => setPipelineName(e.target.value)}
          className="text-lg font-semibold text-gray-800 bg-transparent border-none focus:outline-none focus:ring-0"
        />
        <div className="flex-1" />
        <button
          onClick={() => setShowGenerateModal(true)}
          className="px-3 py-1.5 text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 rounded-md transition-colors"
        >
          Generate from Description
        </button>
        <button
          onClick={handleLoadTemplates}
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

      {/* Main area: palette + canvas + config + optional templates panel */}
      <div className="flex flex-1 overflow-hidden">
        <NodePalette />
        <PipelineCanvas
          onNodeSelect={setSelectedNode}
          onNodeParamsUpdate={handleNodeParamsUpdate}
          nodesState={[nodes, setNodes, onNodesChange]}
          edgesState={[edges, setEdges, onEdgesChange]}
        />
        <NodeConfig node={selectedNode} onUpdate={handleNodeParamsUpdate} />

        {/* Templates side panel */}
        {showTemplatesPanel && (
          <div className="w-80 bg-white border-l border-gray-200 overflow-y-auto p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-800">
                Pipeline Templates
              </h3>
              <button
                onClick={() => setShowTemplatesPanel(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                X
              </button>
            </div>
            {loadingTemplates ? (
              <div className="text-sm text-gray-400">Loading templates...</div>
            ) : (
              <div className="grid grid-cols-1 gap-3">
                {templates.map((t) => (
                  <button
                    key={t.key}
                    onClick={() => handleSelectTemplate(t)}
                    className="text-left p-3 border border-gray-200 rounded-lg hover:border-purple-300 hover:bg-purple-50 transition-colors"
                  >
                    <div className="font-medium text-sm text-gray-800">
                      {t.name}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {t.description}
                    </div>
                    <span className="inline-block mt-2 px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-600 rounded">
                      {t.category}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Generate from Description Modal */}
      {showGenerateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">
              Generate Pipeline from Description
            </h3>
            <textarea
              value={generateDescription}
              onChange={(e) => setGenerateDescription(e.target.value)}
              placeholder='Describe what you want, e.g. "detect objects in images and send alert"'
              className="w-full h-32 border border-gray-300 rounded-lg p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-purple-400"
            />
            <div className="flex justify-end gap-3 mt-4">
              <button
                onClick={() => {
                  setShowGenerateModal(false);
                  setGenerateDescription("");
                }}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
              >
                Cancel
              </button>
              <button
                onClick={handleGenerate}
                disabled={generating || !generateDescription.trim()}
                className="px-4 py-2 text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 rounded-md disabled:opacity-50 transition-colors"
              >
                {generating ? "Generating..." : "Generate"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Schedule Modal */}
      {showScheduleModal && (
        <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50">
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
                <span className="text-xs text-gray-500">Cron expression: </span>
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
    </div>
  );
}
