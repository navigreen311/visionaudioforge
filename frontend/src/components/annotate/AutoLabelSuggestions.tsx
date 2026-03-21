'use client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AutoLabelSuggestion {
  id: string;
  label: string;
  confidence: number;
  bbox: { x: number; y: number; width: number; height: number };
}

interface AutoLabelSuggestionsProps {
  suggestions: AutoLabelSuggestion[];
  onAccept: (id: string) => void;
  onReject: (id: string) => void;
  onAcceptAll: () => void;
  onRejectAll: () => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function confidenceColor(conf: number): string {
  if (conf >= 0.8) return 'bg-green-100 text-green-700';
  if (conf >= 0.5) return 'bg-yellow-100 text-yellow-700';
  return 'bg-red-100 text-red-700';
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function AutoLabelSuggestions({
  suggestions,
  onAccept,
  onReject,
  onAcceptAll,
  onRejectAll,
}: AutoLabelSuggestionsProps) {
  if (suggestions.length === 0) {
    return (
      <p className="py-4 text-center text-sm italic text-gray-400">
        No suggestions. Click &quot;Auto-Label&quot; to generate.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Toolbar */}
      <div className="flex items-center gap-2">
        <button
          onClick={onAcceptAll}
          className="flex-1 rounded-lg bg-green-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-700"
        >
          Accept All
        </button>
        <button
          onClick={onRejectAll}
          className="flex-1 rounded-lg bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700"
        >
          Reject All
        </button>
      </div>

      {/* Suggestion list */}
      <ul className="flex flex-col gap-2 max-h-[50vh] overflow-y-auto">
        {suggestions.map((s) => (
          <li
            key={s.id}
            className="flex items-center gap-3 rounded-lg border-2 border-dashed border-gray-300 px-3 py-2"
          >
            {/* Label name */}
            <span className="flex-1 truncate text-sm font-medium text-gray-800">
              {s.label}
            </span>

            {/* Confidence badge */}
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-semibold ${confidenceColor(
                s.confidence,
              )}`}
            >
              {Math.round(s.confidence * 100)}%
            </span>

            {/* Accept */}
            <button
              onClick={() => onAccept(s.id)}
              className="rounded p-1 text-green-500 hover:bg-green-50 hover:text-green-700"
              title="Accept suggestion"
              aria-label={`Accept ${s.label}`}
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </button>

            {/* Reject */}
            <button
              onClick={() => onReject(s.id)}
              className="rounded p-1 text-red-400 hover:bg-red-50 hover:text-red-600"
              title="Reject suggestion"
              aria-label={`Reject ${s.label}`}
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
