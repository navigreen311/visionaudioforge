"use client";

import { useCallback, useState } from "react";
import { Edge, Node, useEdgesState, useNodesState } from "reactflow";

import { readWorkspaceId } from "@/lib/session";

import NodeConfig from "@/components/pipeline/NodeConfig";
import NodePalette from "@/components/pipeline/NodePalette";
import PipelineCanvas from "@/components/pipeline/PipelineCanvas";
import RunHistory, { type PipelineRunRecord } from "@/components/pipeline/RunHistory";
import RunProgressBar from "@/components/pipeline/RunProgressBar";
import ScheduleModal from "@/components/pipeline/ScheduleModal";

interface PipelineTemplate {
  key: string;
  name: string;
  description: string;
  category: string;
  definition: { nodes: Record<string, unknown>[]; edges: Record<string, unknown>[] };
}

interface DefinitionNode {
  id: string;
  type: string;
  params?: Record<string, unknown>;
}

interface DefinitionEdge {
  from: string;
  to: string;
  // Nodes name their real ports — NormalizeNode takes `image` and returns
  // `image`; the audio nodes need `sr`. The canvas used to drop these on load
  // and re-invent them as "output"/"input" on save, so a template loaded and
  // saved unchanged came back
  //   422 Node 'normalize_1' (normalize) missing required param 'image'
  // which reads as a broken template rather than a lossy round trip.
  from_port?: string;
  to_port?: string;
}

export default function PipelinePage() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [pipelineName, setPipelineName] = useState("Untitled Pipeline");
  const [runs, setRuns] = useState<PipelineRunRecord[]>([]);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [validationMsg, setValidationMsg] = useState<string | null>(null);

  // Modal states
  const [showGenerateModal, setShowGenerateModal] = useState(false);
  const [generateDescription, setGenerateDescription] = useState("");
  const [generating, setGenerating] = useState(false);

  const [showTemplatesPanel, setShowTemplatesPanel] = useState(false);
  const [templates, setTemplates] = useState<PipelineTemplate[]>([]);
  const [loadingTemplates, setLoadingTemplates] = useState(false);

  const [showScheduleModal, setShowScheduleModal] = useState(false);

  // The id of the pipeline this canvas was last saved as. It was a hardcoded
  // nil UUID with a comment claiming it "uses saved pipeline id when available",
  // which it never did: Run always posted the nil id, so it either ran nothing
  // or ran whatever the nil id happened to match. Save now records the real one.
  const [currentPipelineId, setCurrentPipelineId] = useState<string | null>(null);

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
        // Carried through from the loaded definition via React Flow's handles.
        // The "output"/"input" fallback applies only to edges drawn by hand in
        // the canvas, which has no port picker yet — those still need the user
        // to set params explicitly, but they no longer corrupt a template that
        // arrived correctly wired.
        from_port: e.sourceHandle || "output",
        to_port: e.targetHandle || "input",
      })),
    };
  }, [nodes, edges]);

  // Load a pipeline definition into the canvas
  const loadDefinitionToCanvas = useCallback(
    (definition: { nodes: DefinitionNode[]; edges: DefinitionEdge[] }) => {
      const newNodes: Node[] = definition.nodes.map(
        (n: DefinitionNode, i: number) => ({
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
        (e: DefinitionEdge, i: number) => ({
          id: `e-${i}-${e.from}-${e.to}`,
          source: e.from,
          target: e.to,
          // Preserve the port names. React Flow round-trips these unchanged,
          // so buildDefinition can hand back what it was given instead of
          // guessing.
          sourceHandle: e.from_port ?? null,
          targetHandle: e.to_port ?? null,
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
    loadDefinitionToCanvas(template.definition as unknown as { nodes: DefinitionNode[]; edges: DefinitionEdge[] });
    setPipelineName(template.name);
    setShowTemplatesPanel(false);
    setValidationMsg(`Loaded template: ${template.name}`);
    setTimeout(() => setValidationMsg(null), 3000);
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
      // Pipelines are workspace-scoped and the route rejects a body without
      // one — the save was returning
      //   422 workspace_id is required - pipelines are workspace-scoped
      // The workspace comes from the authenticated session, never from
      // anything the user can pick: see docs/auth.md.
      const workspaceId = readWorkspaceId();
      if (!workspaceId) {
        setValidationMsg("Save failed: no workspace in this session — sign in again.");
        return;
      }

      const resp = await fetch("/api/pipeline/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: pipelineName,
          definition: buildDefinition(),
          workspace_id: workspaceId,
        }),
      });
      if (resp.ok) {
        const saved = await resp.json();
        if (saved?.id) setCurrentPipelineId(String(saved.id));
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
    if (!currentPipelineId) {
      // Better than posting a nil id and reporting "run started" for a run that
      // never existed.
      setValidationMsg("Save the pipeline before running it.");
      setTimeout(() => setValidationMsg(null), 5000);
      return;
    }
    setValidationMsg("Running pipeline...");
    try {
      const resp = await fetch("/api/pipeline/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pipeline_id: currentPipelineId }),
      });
      if (resp.ok) {
        const data = await resp.json();
        setActiveRunId(data.run_id);
        setValidationMsg("Pipeline run started!");
      } else {
        setValidationMsg("Failed to start pipeline run");
      }
    } catch {
      setValidationMsg("Run request failed");
    }
    setTimeout(() => setValidationMsg(null), 5000);
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
        {/* Every route needs one h1 - it is what a screen reader announces on
            navigation. This shell is full-height by design, so the heading is
            visually hidden rather than laid out. */}
      <h1 className="sr-only">Pipeline Builder</h1>

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
      <ScheduleModal
        pipelineId={currentPipelineId ?? ""}
        open={showScheduleModal}
        onClose={() => setShowScheduleModal(false)}
        onSaved={() => setValidationMsg("Schedule saved!")}
      />

      {/* Live run progress */}
      {activeRunId && (
        <div className="px-4 py-2 border-t border-gray-200 bg-white">
          <RunProgressBar runId={activeRunId} />
        </div>
      )}

      {/* Run history panel */}
      <div className="h-48 bg-white border-t border-gray-200 overflow-y-auto">
        <div className="px-4 py-2 border-b border-gray-100">
          <h4 className="text-sm font-semibold text-gray-600">Run History</h4>
        </div>
        <RunHistory pipelineId={currentPipelineId ?? ""} runs={runs.length > 0 ? runs : undefined} />
      </div>
    </div>
  );
}
