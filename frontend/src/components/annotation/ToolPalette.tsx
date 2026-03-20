"use client";

export type AnnotationTool = "select" | "bbox" | "polygon" | "keypoint" | "label";

interface ToolPaletteProps {
  activeTool: AnnotationTool;
  onToolChange: (tool: AnnotationTool) => void;
}

const tools: { id: AnnotationTool; label: string; icon: string; description: string }[] = [
  { id: "select", label: "Select", icon: "S", description: "Select and move annotations" },
  { id: "bbox", label: "Bbox", icon: "B", description: "Draw bounding box" },
  { id: "polygon", label: "Polygon", icon: "P", description: "Draw polygon" },
  { id: "keypoint", label: "Keypoint", icon: "K", description: "Place keypoint" },
  { id: "label", label: "Label", icon: "L", description: "Apply label" },
];

export default function ToolPalette({ activeTool, onToolChange }: ToolPaletteProps) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
        Tools
      </span>
      <div className="flex flex-col gap-1">
        {tools.map((tool) => (
          <button
            key={tool.id}
            onClick={() => onToolChange(tool.id)}
            title={tool.description}
            className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              activeTool === tool.id
                ? "bg-brand-600 text-white shadow-sm"
                : "bg-white text-gray-700 hover:bg-gray-100 border border-gray-200"
            }`}
          >
            <span className="w-5 h-5 flex items-center justify-center rounded text-xs font-bold bg-black/10">
              {tool.icon}
            </span>
            <span>{tool.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
