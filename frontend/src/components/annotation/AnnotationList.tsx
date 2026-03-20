"use client";

export interface AnnotationItem {
  id: string;
  annotation_type: string;
  data: Record<string, unknown>;
  is_verified: boolean;
}

interface AnnotationListProps {
  annotations: AnnotationItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}

const typeColors: Record<string, string> = {
  bbox: "bg-blue-100 text-blue-700",
  polygon: "bg-green-100 text-green-700",
  keypoint: "bg-purple-100 text-purple-700",
  segment: "bg-orange-100 text-orange-700",
  label: "bg-yellow-100 text-yellow-700",
  text: "bg-pink-100 text-pink-700",
};

function annotationSummary(ann: AnnotationItem): string {
  const d = ann.data;
  const label = (d.label as string) || "";
  switch (ann.annotation_type) {
    case "bbox":
      return `${label} (${Math.round(d.width as number)}x${Math.round(d.height as number)})`;
    case "polygon":
      return `${label} (${(d.points as unknown[])?.length || 0} pts)`;
    case "keypoint":
      return `${label} (${(d.points as unknown[])?.length || 0} kps)`;
    case "segment":
      return `${label} (${d.start_s}s-${d.end_s}s)`;
    case "label":
      return label;
    case "text":
      return (d.text as string) || label;
    default:
      return label || ann.annotation_type;
  }
}

export default function AnnotationList({
  annotations,
  selectedId,
  onSelect,
  onDelete,
}: AnnotationListProps) {
  if (annotations.length === 0) {
    return (
      <div className="text-sm text-gray-400 italic py-4 text-center">
        No annotations yet. Use a tool to annotate the asset.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1 max-h-[60vh] overflow-y-auto">
      {annotations.map((ann) => (
        <div
          key={ann.id}
          onClick={() => onSelect(ann.id)}
          className={`flex items-center justify-between rounded-lg px-3 py-2 text-sm cursor-pointer transition-colors ${
            selectedId === ann.id
              ? "bg-brand-50 border border-brand-300"
              : "bg-white border border-gray-200 hover:bg-gray-50"
          }`}
        >
          <div className="flex items-center gap-2 min-w-0">
            <span
              className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                typeColors[ann.annotation_type] || "bg-gray-100 text-gray-600"
              }`}
            >
              {ann.annotation_type}
            </span>
            <span className="truncate text-gray-700">{annotationSummary(ann)}</span>
            {ann.is_verified && (
              <span className="text-green-500 text-xs" title="Verified">
                V
              </span>
            )}
          </div>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete(ann.id);
            }}
            className="text-red-400 hover:text-red-600 flex-shrink-0 ml-2"
            title="Delete"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      ))}
    </div>
  );
}
