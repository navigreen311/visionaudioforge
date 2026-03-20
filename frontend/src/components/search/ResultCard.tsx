"use client";

export interface SearchResult {
  asset_id: string;
  score: number;
  rank: number;
  asset_type: string;
  filename: string;
  path: string;
}

interface ResultCardProps {
  result: SearchResult;
  onClick: (result: SearchResult) => void;
}

export default function ResultCard({ result, onClick }: ResultCardProps) {
  const scorePercent = Math.round(result.score * 100);

  const typeColors: Record<string, string> = {
    image: "bg-blue-100 text-blue-700",
    audio: "bg-purple-100 text-purple-700",
    video: "bg-red-100 text-red-700",
    unknown: "bg-gray-100 text-gray-600",
  };
  const typeBadgeClass = typeColors[result.asset_type] || typeColors.unknown;

  return (
    <div
      onClick={() => onClick(result)}
      className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm hover:shadow-md transition-shadow cursor-pointer group"
    >
      {/* Thumbnail / Icon */}
      <div className="aspect-square bg-gray-50 flex items-center justify-center relative">
        {result.asset_type === "image" && result.path ? (
          <div className="w-full h-full bg-gray-200 flex items-center justify-center">
            <svg className="w-12 h-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
        ) : result.asset_type === "audio" ? (
          <svg className="w-12 h-12 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
          </svg>
        ) : (
          <svg className="w-12 h-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
        )}

        {/* Score badge */}
        <div className="absolute top-2 right-2 bg-black/70 text-white text-xs font-medium px-2 py-1 rounded-full">
          {scorePercent}%
        </div>
      </div>

      {/* Info */}
      <div className="p-3">
        <p className="text-sm font-medium text-gray-900 truncate group-hover:text-brand-600 transition-colors">
          {result.filename || `Asset ${result.asset_id.slice(0, 8)}...`}
        </p>
        <div className="flex items-center gap-2 mt-2">
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${typeBadgeClass}`}>
            {result.asset_type}
          </span>
          <span className="text-xs text-gray-400">#{result.rank}</span>
        </div>
      </div>
    </div>
  );
}
