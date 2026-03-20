"use client";

import { useEffect, useState } from "react";

interface NodeTypeInfo {
  type: string;
  category: string;
  description: string;
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown>;
}

const CATEGORY_ICONS: Record<string, string> = {
  Input: "📥",
  Vision: "👁",
  Audio: "🎵",
  Search: "🔍",
  Action: "⚡",
  Transform: "🔄",
};

export default function NodePalette() {
  const [nodeTypes, setNodeTypes] = useState<NodeTypeInfo[]>([]);
  const [openCategories, setOpenCategories] = useState<Set<string>>(new Set());

  useEffect(() => {
    fetch("/api/pipeline/nodes")
      .then((r) => r.json())
      .then((data) => {
        setNodeTypes(data);
        // Open all categories by default
        const cats = new Set(data.map((n: NodeTypeInfo) => n.category));
        setOpenCategories(cats as Set<string>);
      })
      .catch(() => {
        // Fallback with empty list
      });
  }, []);

  const grouped = nodeTypes.reduce<Record<string, NodeTypeInfo[]>>(
    (acc, node) => {
      (acc[node.category] = acc[node.category] || []).push(node);
      return acc;
    },
    {},
  );

  const toggleCategory = (cat: string) => {
    setOpenCategories((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  };

  const onDragStart = (
    event: React.DragEvent<HTMLDivElement>,
    nodeType: NodeTypeInfo,
  ) => {
    event.dataTransfer.setData(
      "application/reactflow",
      JSON.stringify(nodeType),
    );
    event.dataTransfer.effectAllowed = "move";
  };

  return (
    <aside className="w-60 bg-white border-r border-gray-200 overflow-y-auto flex-shrink-0">
      <div className="p-3 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider">
          Nodes
        </h3>
      </div>
      <div className="p-2 space-y-1">
        {Object.entries(grouped).map(([category, nodes]) => (
          <div key={category}>
            <button
              onClick={() => toggleCategory(category)}
              className="w-full flex items-center justify-between px-2 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-50 rounded"
            >
              <span>
                {CATEGORY_ICONS[category] || "📦"} {category}
              </span>
              <span className="text-xs text-gray-400">
                {openCategories.has(category) ? "▾" : "▸"}
              </span>
            </button>
            {openCategories.has(category) && (
              <div className="ml-2 space-y-0.5">
                {nodes.map((node) => (
                  <div
                    key={node.type}
                    draggable
                    onDragStart={(e) => onDragStart(e, node)}
                    className="flex items-center gap-2 px-2 py-1.5 text-sm text-gray-700 bg-gray-50 hover:bg-brand-50 hover:text-brand-700 rounded cursor-grab active:cursor-grabbing transition-colors"
                    title={node.description}
                  >
                    <span className="w-2 h-2 rounded-full bg-brand-400 flex-shrink-0" />
                    {node.type
                      .split("_")
                      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
                      .join(" ")}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </aside>
  );
}
