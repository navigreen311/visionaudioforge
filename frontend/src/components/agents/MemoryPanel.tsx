"use client";

interface Memory {
  id: string;
  content: string;
  importance_score: number;
  freshness_score: number;
  created_at: string;
}

interface MemoryPanelProps {
  memories: Memory[];
  onDelete: (memoryId: string) => void;
  onDecay: () => void;
  loading?: boolean;
}

function importanceBadge(score: number) {
  if (score >= 0.8) return { label: "High", color: "bg-red-100 text-red-700" };
  if (score >= 0.5) return { label: "Med", color: "bg-yellow-100 text-yellow-700" };
  return { label: "Low", color: "bg-gray-100 text-gray-600" };
}

export default function MemoryPanel({
  memories,
  onDelete,
  onDecay,
  loading,
}: MemoryPanelProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-900 text-sm">
          Memories ({memories.length})
        </h3>
        <button
          onClick={onDecay}
          disabled={loading}
          className="text-xs text-brand-600 hover:text-brand-700 disabled:opacity-50"
        >
          Decay All
        </button>
      </div>

      {memories.length === 0 && (
        <p className="text-gray-400 text-xs text-center py-4">No memories stored yet.</p>
      )}

      <div className="space-y-2 max-h-96 overflow-y-auto">
        {memories.map((mem) => {
          const badge = importanceBadge(mem.importance_score);
          return (
            <div
              key={mem.id}
              className="border border-gray-100 rounded-lg p-3 text-xs group hover:border-gray-300 transition-colors"
            >
              <div className="flex items-start justify-between gap-2">
                <p className="text-gray-700 line-clamp-3 flex-1">{mem.content}</p>
                <button
                  onClick={() => onDelete(mem.id)}
                  className="text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
                  title="Delete memory"
                >
                  &times;
                </button>
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${badge.color}`}>
                  {badge.label}
                </span>
                <span className="text-gray-400">
                  Fresh: {(mem.freshness_score * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
