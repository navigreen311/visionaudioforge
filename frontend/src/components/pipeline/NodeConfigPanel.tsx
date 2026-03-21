'use client';

import { useCallback, useEffect, useState } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PipelineNodeData {
  label: string;
  category: string;
  description?: string;
  nodeType: string;
  inputs?: Record<string, Record<string, unknown>>;
  outputs?: Record<string, Record<string, unknown>>;
  params: Record<string, unknown>;
}

interface PipelineNode {
  id: string;
  type?: string;
  data: PipelineNodeData;
  position: { x: number; y: number };
}

interface NodeConfigPanelProps {
  selectedNode: PipelineNode | null;
  onConfigChange: (nodeId: string, config: Record<string, unknown>) => void;
  onRemove: (nodeId: string) => void;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const CATEGORY_BADGE_COLORS: Record<string, string> = {
  Input: 'bg-green-100 text-green-700',
  Vision: 'bg-blue-100 text-blue-700',
  Audio: 'bg-purple-100 text-purple-700',
  Search: 'bg-yellow-100 text-yellow-700',
  Action: 'bg-red-100 text-red-700',
  Transform: 'bg-orange-100 text-orange-700',
  Control: 'bg-gray-100 text-gray-700',
};

const COCO_CLASSES = [
  'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train',
  'truck', 'boat', 'traffic light', 'fire hydrant', 'stop sign',
  'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow',
  'elephant', 'bear', 'zebra', 'giraffe', 'backpack', 'umbrella', 'handbag',
  'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball', 'kite',
  'baseball bat', 'baseball glove', 'skateboard', 'surfboard',
  'tennis racket', 'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon',
  'bowl', 'banana', 'apple', 'sandwich', 'orange', 'broccoli', 'carrot',
  'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch', 'potted plant',
  'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote',
  'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
  'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear',
  'hair drier', 'toothbrush',
];

const RESOLUTIONS = ['320x240', '640x480', '1280x720', '1920x1080'];
const FRAME_RATES = ['5', '10', '15', '24', '30', '60'];
const COOLDOWN_OPTIONS = ['5s', '15s', '30s', '1m', '5m', '15m', '30m', '1h'];

// ---------------------------------------------------------------------------
// Shared form helpers
// ---------------------------------------------------------------------------

function FieldLabel({ label, required }: { label: string; required?: boolean }) {
  return (
    <label className="block text-xs font-medium text-gray-600 mb-1">
      {label}
      {required && <span className="text-red-400 ml-0.5">*</span>}
    </label>
  );
}

const inputClass =
  'w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:ring-1 focus:ring-brand-500 focus:border-brand-500 outline-none';

const selectClass = inputClass;

// ---------------------------------------------------------------------------
// Camera Feed config
// ---------------------------------------------------------------------------

function CameraFeedConfig({
  params,
  onChange,
}: {
  params: Record<string, unknown>;
  onChange: (key: string, value: unknown) => void;
}) {
  const source = (params.source as string) ?? 'webcam';

  return (
    <div className="space-y-3">
      <div>
        <FieldLabel label="Source" required />
        <select
          className={selectClass}
          value={source}
          onChange={(e) => onChange('source', e.target.value)}
        >
          <option value="webcam">Webcam</option>
          <option value="screen">Screen Capture</option>
          <option value="rtsp">RTSP Stream</option>
        </select>
      </div>

      {source === 'rtsp' && (
        <div>
          <FieldLabel label="RTSP URL" required />
          <input
            type="text"
            className={inputClass}
            placeholder="rtsp://host:port/stream"
            value={(params.rtsp_url as string) ?? ''}
            onChange={(e) => onChange('rtsp_url', e.target.value)}
          />
        </div>
      )}

      <div>
        <FieldLabel label="Frame Rate" />
        <select
          className={selectClass}
          value={String(params.frame_rate ?? '30')}
          onChange={(e) => onChange('frame_rate', Number(e.target.value))}
        >
          {FRAME_RATES.map((fr) => (
            <option key={fr} value={fr}>
              {fr} fps
            </option>
          ))}
        </select>
      </div>

      <div>
        <FieldLabel label="Resolution" />
        <select
          className={selectClass}
          value={(params.resolution as string) ?? '1280x720'}
          onChange={(e) => onChange('resolution', e.target.value)}
        >
          {RESOLUTIONS.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Object Detect config
// ---------------------------------------------------------------------------

interface ModelOption {
  id: string;
  name: string;
}

function ObjectDetectConfig({
  params,
  onChange,
}: {
  params: Record<string, unknown>;
  onChange: (key: string, value: unknown) => void;
}) {
  const [models, setModels] = useState<ModelOption[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoadingModels(true);
    fetch('/api/registry/models')
      .then((r) => r.json())
      .then((data: ModelOption[]) => {
        if (!cancelled) setModels(Array.isArray(data) ? data : []);
      })
      .catch(() => {
        if (!cancelled) setModels([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingModels(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const confidence = (params.confidence as number) ?? 50;
  const selectedClasses = (params.classes as string[]) ?? [];

  const toggleClass = (cls: string) => {
    const next = selectedClasses.includes(cls)
      ? selectedClasses.filter((c) => c !== cls)
      : [...selectedClasses, cls];
    onChange('classes', next);
  };

  return (
    <div className="space-y-3">
      <div>
        <FieldLabel label="Model" required />
        <select
          className={selectClass}
          value={(params.model as string) ?? ''}
          onChange={(e) => onChange('model', e.target.value)}
          disabled={loadingModels}
        >
          <option value="">
            {loadingModels ? 'Loading models...' : 'Select a model'}
          </option>
          {models.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name}
            </option>
          ))}
        </select>
      </div>

      <div>
        <FieldLabel label={`Confidence: ${confidence}%`} />
        <input
          type="range"
          min={0}
          max={100}
          value={confidence}
          onChange={(e) => onChange('confidence', Number(e.target.value))}
          className="w-full accent-brand-500"
        />
        <div className="flex justify-between text-xs text-gray-400 mt-0.5">
          <span>0%</span>
          <span>100%</span>
        </div>
      </div>

      <div>
        <FieldLabel label="Classes (COCO)" />
        <div className="max-h-40 overflow-y-auto border border-gray-200 rounded p-2 space-y-1">
          {COCO_CLASSES.map((cls) => (
            <label
              key={cls}
              className="flex items-center gap-2 text-xs text-gray-700 cursor-pointer hover:bg-gray-50 rounded px-1 py-0.5"
            >
              <input
                type="checkbox"
                checked={selectedClasses.includes(cls)}
                onChange={() => toggleClass(cls)}
                className="rounded border-gray-300 text-brand-500 focus:ring-brand-500"
              />
              {cls}
            </label>
          ))}
        </div>
        {selectedClasses.length > 0 && (
          <p className="text-xs text-gray-400 mt-1">
            {selectedClasses.length} class{selectedClasses.length !== 1 ? 'es' : ''} selected
          </p>
        )}
      </div>

      <div>
        <FieldLabel label="Max Detections" />
        <input
          type="number"
          min={1}
          max={1000}
          className={inputClass}
          value={(params.max_detections as number) ?? 100}
          onChange={(e) => onChange('max_detections', Number(e.target.value))}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Filter config
// ---------------------------------------------------------------------------

const FILTER_FIELDS = ['confidence', 'area', 'label', 'score', 'count'];
const FILTER_OPERATORS = ['>', '<', '>=', '<=', '==', '!='];
const FILTER_ON_FAIL = ['skip', 'stop', 'branch'];

function FilterConfig({
  params,
  onChange,
}: {
  params: Record<string, unknown>;
  onChange: (key: string, value: unknown) => void;
}) {
  return (
    <div className="space-y-3">
      <div>
        <FieldLabel label="Condition Field" required />
        <select
          className={selectClass}
          value={(params.condition_field as string) ?? ''}
          onChange={(e) => onChange('condition_field', e.target.value)}
        >
          <option value="">Select field...</option>
          {FILTER_FIELDS.map((f) => (
            <option key={f} value={f}>
              {f}
            </option>
          ))}
        </select>
      </div>

      <div>
        <FieldLabel label="Operator" required />
        <select
          className={selectClass}
          value={(params.operator as string) ?? '>'}
          onChange={(e) => onChange('operator', e.target.value)}
        >
          {FILTER_OPERATORS.map((op) => (
            <option key={op} value={op}>
              {op}
            </option>
          ))}
        </select>
      </div>

      <div>
        <FieldLabel label="Value" required />
        <input
          type="text"
          className={inputClass}
          value={(params.value as string) ?? ''}
          onChange={(e) => onChange('value', e.target.value)}
          placeholder="e.g. 0.5"
        />
      </div>

      <div>
        <FieldLabel label="On Fail" />
        <select
          className={selectClass}
          value={(params.on_fail as string) ?? 'skip'}
          onChange={(e) => onChange('on_fail', e.target.value)}
        >
          {FILTER_ON_FAIL.map((opt) => (
            <option key={opt} value={opt}>
              {opt.charAt(0).toUpperCase() + opt.slice(1)}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Send Alert config
// ---------------------------------------------------------------------------

const SEVERITIES = ['info', 'warning', 'critical'] as const;

const SEVERITY_COLORS: Record<string, string> = {
  info: 'bg-blue-100 text-blue-700 border-blue-300',
  warning: 'bg-yellow-100 text-yellow-700 border-yellow-300',
  critical: 'bg-red-100 text-red-700 border-red-300',
};

function SendAlertConfig({
  params,
  onChange,
}: {
  params: Record<string, unknown>;
  onChange: (key: string, value: unknown) => void;
}) {
  const severity = (params.severity as string) ?? 'info';

  return (
    <div className="space-y-3">
      <div>
        <FieldLabel label="Severity" required />
        <div className="flex gap-2">
          {SEVERITIES.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => onChange('severity', s)}
              className={`flex-1 px-2 py-1.5 text-xs font-medium rounded border transition-colors ${
                severity === s
                  ? SEVERITY_COLORS[s]
                  : 'bg-gray-50 text-gray-500 border-gray-200 hover:bg-gray-100'
              }`}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div>
        <FieldLabel label="Message Template" required />
        <textarea
          className={`${inputClass} resize-none`}
          rows={3}
          value={(params.message as string) ?? ''}
          onChange={(e) => onChange('message', e.target.value)}
          placeholder="Detection found: {{label}} ({{confidence}}%)"
        />
        <p className="text-xs text-gray-400 mt-1">
          Variables: {'{{label}}'}, {'{{confidence}}'}, {'{{count}}'}, {'{{timestamp}}'}
        </p>
      </div>

      <div>
        <FieldLabel label="Cooldown" />
        <select
          className={selectClass}
          value={(params.cooldown as string) ?? '30s'}
          onChange={(e) => onChange('cooldown', e.target.value)}
        >
          {COOLDOWN_OPTIONS.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Save to Assets config
// ---------------------------------------------------------------------------

function SaveToAssetsConfig({
  params,
  onChange,
}: {
  params: Record<string, unknown>;
  onChange: (key: string, value: unknown) => void;
}) {
  const overwrite = (params.overwrite as boolean) ?? false;
  const tags = (params.tags as string[]) ?? [];
  const [tagInput, setTagInput] = useState('');

  const addTag = () => {
    const trimmed = tagInput.trim();
    if (trimmed && !tags.includes(trimmed)) {
      onChange('tags', [...tags, trimmed]);
    }
    setTagInput('');
  };

  const removeTag = (tag: string) => {
    onChange('tags', tags.filter((t) => t !== tag));
  };

  const handleTagKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addTag();
    }
  };

  return (
    <div className="space-y-3">
      <div>
        <FieldLabel label="Name Template" required />
        <input
          type="text"
          className={inputClass}
          value={(params.name_template as string) ?? ''}
          onChange={(e) => onChange('name_template', e.target.value)}
          placeholder="detection_{{timestamp}}"
        />
        <p className="text-xs text-gray-400 mt-1">
          Variables: {'{{timestamp}}'}, {'{{label}}'}, {'{{index}}'}
        </p>
      </div>

      <div>
        <FieldLabel label="Tags" />
        <div className="flex gap-1">
          <input
            type="text"
            className={`${inputClass} flex-1`}
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyDown={handleTagKeyDown}
            placeholder="Add tag and press Enter"
          />
          <button
            type="button"
            onClick={addTag}
            className="px-2 py-1.5 text-sm bg-brand-50 text-brand-600 rounded hover:bg-brand-100 transition-colors"
          >
            +
          </button>
        </div>
        {tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {tags.map((tag) => (
              <span
                key={tag}
                className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-gray-100 text-gray-700 rounded"
              >
                {tag}
                <button
                  type="button"
                  onClick={() => removeTag(tag)}
                  className="text-gray-400 hover:text-red-500"
                >
                  x
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      <div>
        <label className="flex items-center gap-2 cursor-pointer">
          <div
            role="switch"
            aria-checked={overwrite}
            tabIndex={0}
            onClick={() => onChange('overwrite', !overwrite)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onChange('overwrite', !overwrite);
              }
            }}
            className={`relative w-9 h-5 rounded-full transition-colors ${
              overwrite ? 'bg-brand-500' : 'bg-gray-300'
            }`}
          >
            <span
              className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${
                overwrite ? 'translate-x-4' : 'translate-x-0'
              }`}
            />
          </div>
          <span className="text-xs font-medium text-gray-600">
            Overwrite existing
          </span>
        </label>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Generic JSON config (fallback for unknown node types)
// ---------------------------------------------------------------------------

function GenericJsonConfig({
  params,
  onParamsChange,
}: {
  params: Record<string, unknown>;
  onParamsChange: (newParams: Record<string, unknown>) => void;
}) {
  const [jsonText, setJsonText] = useState(() =>
    JSON.stringify(params, null, 2),
  );
  const [parseError, setParseError] = useState<string | null>(null);

  // Sync external changes into the textarea
  useEffect(() => {
    setJsonText(JSON.stringify(params, null, 2));
    setParseError(null);
  }, [params]);

  const handleBlur = () => {
    try {
      const parsed = JSON.parse(jsonText) as Record<string, unknown>;
      setParseError(null);
      onParamsChange(parsed);
    } catch (err) {
      setParseError(
        err instanceof Error ? err.message : 'Invalid JSON',
      );
    }
  };

  return (
    <div className="space-y-2">
      <FieldLabel label="Configuration (JSON)" />
      <textarea
        className={`${inputClass} font-mono text-xs resize-y ${
          parseError ? 'border-red-300 focus:ring-red-400' : ''
        }`}
        rows={10}
        value={jsonText}
        onChange={(e) => setJsonText(e.target.value)}
        onBlur={handleBlur}
        spellCheck={false}
      />
      {parseError && (
        <p className="text-xs text-red-500">{parseError}</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main panel
// ---------------------------------------------------------------------------

/** Map node types to their specialised config panels. */
const NODE_TYPE_ALIASES: Record<string, string> = {
  // Allow flexible matching
  camera_feed: 'camera_feed',
  input_video: 'camera_feed',
  detect_objects: 'detect_objects',
  object_detect: 'detect_objects',
  filter: 'filter',
  alert: 'alert',
  send_alert: 'alert',
  save_asset: 'save_asset',
  save_to_assets: 'save_asset',
};

export default function NodeConfigPanel({
  selectedNode,
  onConfigChange,
  onRemove,
}: NodeConfigPanelProps) {
  // Derive a stable change handler
  const handleChange = useCallback(
    (key: string, value: unknown) => {
      if (!selectedNode) return;
      const updated = { ...selectedNode.data.params, [key]: value };
      onConfigChange(selectedNode.id, updated);
    },
    [selectedNode, onConfigChange],
  );

  const handleFullParamsChange = useCallback(
    (newParams: Record<string, unknown>) => {
      if (!selectedNode) return;
      onConfigChange(selectedNode.id, newParams);
    },
    [selectedNode, onConfigChange],
  );

  // ----- Empty state -----
  if (!selectedNode) {
    return (
      <aside className="w-80 bg-white border-l border-gray-200 p-4 flex items-center justify-center text-sm text-gray-400">
        Select a node to configure
      </aside>
    );
  }

  const { data } = selectedNode;
  const params = data.params ?? {};
  const nodeType = data.nodeType ?? '';
  const resolvedType = NODE_TYPE_ALIASES[nodeType] ?? nodeType;
  const badgeColor =
    CATEGORY_BADGE_COLORS[data.category] ?? 'bg-gray-100 text-gray-600';

  // ----- Render the node-specific config -----
  const renderConfig = () => {
    switch (resolvedType) {
      case 'camera_feed':
        return <CameraFeedConfig params={params} onChange={handleChange} />;
      case 'detect_objects':
        return <ObjectDetectConfig params={params} onChange={handleChange} />;
      case 'filter':
        return <FilterConfig params={params} onChange={handleChange} />;
      case 'alert':
        return <SendAlertConfig params={params} onChange={handleChange} />;
      case 'save_asset':
        return <SaveToAssetsConfig params={params} onChange={handleChange} />;
      default:
        return (
          <GenericJsonConfig
            params={params}
            onParamsChange={handleFullParamsChange}
          />
        );
    }
  };

  return (
    <aside className="w-80 bg-white border-l border-gray-200 overflow-y-auto flex-shrink-0 flex flex-col">
      {/* Header */}
      <div className="p-3 border-b border-gray-100">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2 min-w-0">
            <h3 className="text-sm font-semibold text-gray-800 truncate">
              {data.label || nodeType}
            </h3>
            <span
              className={`inline-flex px-1.5 py-0.5 text-[10px] font-semibold rounded ${badgeColor}`}
            >
              {data.category}
            </span>
          </div>
          <button
            type="button"
            onClick={() => onRemove(selectedNode.id)}
            className="ml-2 flex-shrink-0 px-2 py-1 text-xs font-medium text-red-600 bg-red-50 hover:bg-red-100 rounded transition-colors"
            title="Remove node"
          >
            Remove node
          </button>
        </div>
        {data.description && (
          <p className="text-xs text-gray-400">{data.description}</p>
        )}
      </div>

      {/* Config body */}
      <div className="p-3 flex-1 overflow-y-auto">{renderConfig()}</div>
    </aside>
  );
}
