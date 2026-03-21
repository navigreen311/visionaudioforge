'use client';

interface AnnotationProgressProps {
  annotated: number;
  total: number;
}

export default function AnnotationProgress({
  annotated,
  total,
}: AnnotationProgressProps) {
  const pct = total > 0 ? Math.round((annotated / total) * 100) : 0;

  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-gray-600 whitespace-nowrap">
        {annotated} of {total} assets annotated
      </span>
      <div className="flex-1 h-1.5 rounded-full bg-gray-200 overflow-hidden min-w-[80px]">
        <div
          className="h-full rounded-full bg-blue-500 transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-gray-400 tabular-nums">{pct}%</span>
    </div>
  );
}
