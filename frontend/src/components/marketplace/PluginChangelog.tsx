'use client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ChangelogEntry {
  version: string;
  date: string;
  changes: string[];
  type: 'major' | 'minor' | 'patch';
}

interface PluginChangelogProps {
  entries: ChangelogEntry[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const TYPE_BADGE: Record<string, string> = {
  major: 'bg-red-100 text-red-700',
  minor: 'bg-blue-100 text-blue-700',
  patch: 'bg-gray-100 text-gray-600',
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function PluginChangelog({ entries }: PluginChangelogProps) {
  return (
    <div className="space-y-4">
      {entries.map((entry, idx) => (
        <div
          key={entry.version}
          className="relative border border-gray-200 rounded-xl bg-white p-4 space-y-2"
        >
          {/* Timeline connector */}
          {idx < entries.length - 1 && (
            <div className="absolute left-7 top-14 bottom-0 w-px bg-gray-200 -mb-4" />
          )}

          {/* Version header */}
          <div className="flex items-center gap-3">
            <div className="h-6 w-6 rounded-full bg-brand-100 flex items-center justify-center z-10">
              <div className="h-2.5 w-2.5 rounded-full bg-brand-600" />
            </div>
            <h3 className="text-sm font-semibold text-gray-900">v{entry.version}</h3>
            <span
              className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${
                TYPE_BADGE[entry.type] || TYPE_BADGE.patch
              }`}
            >
              {entry.type}
            </span>
            <span className="text-xs text-gray-400 ml-auto">{entry.date}</span>
          </div>

          {/* Change list */}
          <ul className="ml-9 space-y-1">
            {entry.changes.map((change, cIdx) => (
              <li key={cIdx} className="text-sm text-gray-700 flex items-start gap-2">
                <span className="text-gray-400 mt-1 shrink-0">&#8226;</span>
                <span>{change}</span>
              </li>
            ))}
          </ul>
        </div>
      ))}

      {entries.length === 0 && (
        <p className="text-center text-sm text-gray-400 py-6">
          No changelog entries available.
        </p>
      )}
    </div>
  );
}
