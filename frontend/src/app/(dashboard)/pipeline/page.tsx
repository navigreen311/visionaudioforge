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

export default function PipelinePage() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [pipelineName, setPipelineName] = useState("Untitled Pipeline");
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [validationMsg, setValidationMsg] = useState<string | null>(null);

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
    // For demo purposes — needs a saved pipeline ID in production
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
          nodesState={[nodes, setNodes, onNodesChange]}
          edgesState={[edges, setEdges, onEdgesChange]}
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
    </div>
  );
}
