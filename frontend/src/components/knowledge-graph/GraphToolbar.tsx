'use client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type LayoutMode = 'force' | 'hierarchical' | 'radial';

export type ToolbarAction =
  | 'add-entity'
  | 'add-relationship'
  | 'find-path'
  | 'extract-from-asset'
  | 'export';

interface GraphToolbarProps {
  currentLayout: LayoutMode;
  onLayoutChange: (layout: LayoutMode) => void;
  onAction: (action: ToolbarAction) => void;
}

// ---------------------------------------------------------------------------
// Layout button config
// ---------------------------------------------------------------------------

const LAYOUTS: { mode: LayoutMode; label: string; icon: string }[] = [
  { mode: 'force', label: 'Force', icon: '⊛' },
  { mode: 'hierarchical', label: 'Hierarchical', icon: '⊟' },
  { mode: 'radial', label: 'Radial', icon: '◎' },
];

// ---------------------------------------------------------------------------
// Action button config
// ---------------------------------------------------------------------------

const ACTIONS: { action: ToolbarAction; label: string }[] = [
  { action: 'add-entity', label: '+ Add Entity' },
  { action: 'add-relationship', label: '+ Add Relationship' },
  { action: 'find-path', label: 'Find Path' },
  { action: 'extract-from-asset', label: 'Extract from Asset' },
  { action: 'export', label: 'Export' },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function GraphToolbar({
  currentLayout,
  onLayoutChange,
  onAction,
}: GraphToolbarProps) {
  return (
    <div className="flex items-center gap-4 px-4 py-2 bg-gray-900 border-b border-gray-700">
      {/* Layout switcher */}
      <div className="flex items-center gap-1">
        <span className="text-xs text-gray-500 mr-1">Layout:</span>
        {LAYOUTS.map(({ mode, label, icon }) => (
          <button
            key={mode}
            type="button"
            onClick={() => onLayoutChange(mode)}
            className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
              currentLayout === mode
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200'
            }`}
            title={label}
          >
            <span className="mr-1">{icon}</span>
            {label}
          </button>
        ))}
      </div>

      {/* Divider */}
      <div className="w-px h-6 bg-gray-700" />

      {/* Action buttons */}
      <div className="flex items-center gap-2">
        {ACTIONS.map(({ action, label }) => (
          <button
            key={action}
            type="button"
            onClick={() => onAction(action)}
            className="px-3 py-1 rounded text-xs font-medium bg-gray-800 text-gray-300 hover:bg-gray-700 hover:text-gray-100 transition-colors whitespace-nowrap"
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}
