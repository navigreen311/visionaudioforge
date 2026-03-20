"use client";

import { useCallback, useRef, useState } from "react";
import ReactFlow, {
  addEdge,
  Background,
  Connection,
  Controls,
  Edge,
  Handle,
  MiniMap,
  Node,
  NodeProps,
  Position,
  ReactFlowInstance,
  useEdgesState,
  useNodesState,
} from "reactflow";
import "reactflow/dist/style.css";

// ---------------------------------------------------------------------------
// Custom node component
// ---------------------------------------------------------------------------

const CATEGORY_COLORS: Record<string, string> = {
  Input: "border-green-400 bg-green-50",
  Vision: "border-blue-400 bg-blue-50",
  Audio: "border-purple-400 bg-purple-50",
  Search: "border-yellow-400 bg-yellow-50",
  Action: "border-red-400 bg-red-50",
  Transform: "border-orange-400 bg-orange-50",
};

function PipelineNode({ data, selected }: NodeProps) {
  const colorClass =
    CATEGORY_COLORS[data.category] || "border-gray-300 bg-gray-50";
  return (
    <div
      className={`rounded-lg border-2 shadow-sm px-3 py-2 min-w-[140px] ${colorClass} ${
        selected ? "ring-2 ring-brand-500" : ""
      }`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!w-3 !h-3 !bg-gray-400 !border-2 !border-white"
      />
      <div className="flex items-center gap-2">
        <span className="text-xs font-bold text-gray-500 uppercase">
          {data.category}
        </span>
      </div>
      <div className="text-sm font-semibold text-gray-800 mt-0.5">
        {data.label}
      </div>
      <Handle
        type="source"
        position={Position.Right}
        className="!w-3 !h-3 !bg-brand-500 !border-2 !border-white"
      />
    </div>
  );
}

const nodeTypes = { pipeline: PipelineNode };

// ---------------------------------------------------------------------------
// Canvas component
// ---------------------------------------------------------------------------

interface PipelineCanvasProps {
  onNodeSelect: (node: Node | null) => void;
  onNodeParamsUpdate: (nodeId: string, params: Record<string, unknown>) => void;
  nodesState: [Node[], React.Dispatch<React.SetStateAction<Node[]>>, (changes: any) => void];
  edgesState: [Edge[], React.Dispatch<React.SetStateAction<Edge[]>>, (changes: any) => void];
}

export default function PipelineCanvas({
  onNodeSelect,
  nodesState,
  edgesState,
}: PipelineCanvasProps) {
  const [nodes, setNodes, onNodesChange] = nodesState;
  const [edges, setEdges, onEdgesChange] = edgesState;
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [rfInstance, setRfInstance] = useState<ReactFlowInstance | null>(null);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges],
  );

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      const raw = event.dataTransfer.getData("application/reactflow");
      if (!raw || !rfInstance) return;

      const nodeInfo = JSON.parse(raw);
      const position = rfInstance.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const newNode: Node = {
        id: `${nodeInfo.type}_${Date.now()}`,
        type: "pipeline",
        position,
        data: {
          label: nodeInfo.type
            .split("_")
            .map((w: string) => w.charAt(0).toUpperCase() + w.slice(1))
            .join(" "),
          category: nodeInfo.category,
          description: nodeInfo.description,
          nodeType: nodeInfo.type,
          inputs: nodeInfo.inputs,
          outputs: nodeInfo.outputs,
          params: {},
        },
      };

      setNodes((nds) => [...nds, newNode]);
    },
    [rfInstance, setNodes],
  );

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => onNodeSelect(node),
    [onNodeSelect],
  );

  const onPaneClick = useCallback(() => onNodeSelect(null), [onNodeSelect]);

  return (
    <div ref={reactFlowWrapper} className="flex-1 h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onInit={setRfInstance}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        fitView
        className="bg-gray-50"
      >
        <Controls />
        <MiniMap
          nodeStrokeWidth={3}
          className="!bg-white !border-gray-200"
        />
        <Background color="#e5e7eb" gap={16} />
      </ReactFlow>
    </div>
  );
}
