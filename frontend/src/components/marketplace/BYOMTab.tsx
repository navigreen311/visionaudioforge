'use client';

import { useState, useEffect, useCallback, useRef } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ModelType =
  | 'Classification'
  | 'Detection'
  | 'Segmentation'
  | 'Audio'
  | 'Embedding'
  | 'Custom';

type ColorSpace = 'RGB' | 'BGR' | 'Grayscale' | 'HSV' | 'LAB';

type OutputType = 'probabilities' | 'bounding_boxes' | 'masks' | 'embeddings' | 'raw';

interface ValidationResult {
  valid: boolean;
  input_shape: string;
  output_shape: string;
  framework_detected: string;
  param_count: number;
}

interface AdapterConfig {
  resize_w: number;
  resize_h: number;
  normalize: boolean;
  mean: string;
  std: string;
  color_space: ColorSpace;
  output_type: OutputType;
  classes: string;
  confidence_threshold: number;
}

interface PipelineNodeConfig {
  node_name: string;
  category: string;
  icon_index: number;
}

interface BYOMModel {
  model_id: string;
  model_name: string;
  model_type: ModelType;
  file_name: string;
  status: 'validated' | 'registered' | 'error';
  node_name: string | null;
  created_at: string;
  input_shape: string;
  output_shape: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MODEL_TYPES: ModelType[] = [
  'Classification',
  'Detection',
  'Segmentation',
  'Audio',
  'Embedding',
  'Custom',
];

const COLOR_SPACES: ColorSpace[] = ['RGB', 'BGR', 'Grayscale', 'HSV', 'LAB'];

const OUTPUT_TYPES: OutputType[] = [
  'probabilities',
  'bounding_boxes',
  'masks',
  'embeddings',
  'raw',
];

const ACCEPTED_EXTENSIONS = '.onnx,.pt,.pth,.tflite';

const NODE_CATEGORIES = [
  'Vision',
  'Audio',
  'Transform',
  'Analytics',
  'Detection',
  'Embedding',
  'Custom',
];

// 8 preset icon SVG paths (simple geometric shapes for pipeline nodes)
const PRESET_ICONS: { label: string; path: string }[] = [
  {
    label: 'Eye',
    path: 'M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17a5 5 0 110-10 5 5 0 010 10zm0-8a3 3 0 100 6 3 3 0 000-6z',
  },
  {
    label: 'Brain',
    path: 'M12 2a9 9 0 00-9 9c0 3.87 2.13 7.24 5.28 8.57a1 1 0 001.44-.9V15.5a2.5 2.5 0 015 0v3.17a1 1 0 001.44.9C19.87 18.24 22 14.87 22 11a9 9 0 00-9-9h-1z',
  },
  {
    label: 'Waveform',
    path: 'M3 12h2l2-6 3 12 3-8 2 4h2l2-3h3',
  },
  {
    label: 'Grid',
    path: 'M3 3h7v7H3V3zm11 0h7v7h-7V3zM3 14h7v7H3v-7zm11 0h7v7h-7v-7z',
  },
  {
    label: 'Layers',
    path: 'M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5',
  },
  {
    label: 'Cube',
    path: 'M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z',
  },
  {
    label: 'Sparkle',
    path: 'M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8L12 2z',
  },
  {
    label: 'Bolt',
    path: 'M13 2L3 14h9l-1 8 10-12h-9l1-8z',
  },
];

const STATUS_COLORS: Record<string, string> = {
  validated: 'bg-green-100 text-green-700',
  registered: 'bg-blue-100 text-blue-700',
  error: 'bg-red-100 text-red-700',
};

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

const API_BASE = '/api/marketplace/byom';

async function apiValidate(formData: FormData): Promise<ValidationResult> {
  const res = await fetch(`${API_BASE}/validate`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error(`Validation failed: ${res.statusText}`);
  return res.json() as Promise<ValidationResult>;
}

async function apiRegister(payload: Record<string, unknown>): Promise<BYOMModel> {
  const res = await fetch(`${API_BASE}/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Registration failed: ${res.statusText}`);
  return res.json() as Promise<BYOMModel>;
}

async function apiListModels(): Promise<BYOMModel[]> {
  const res = await fetch(`${API_BASE}/models`);
  if (!res.ok) throw new Error(`Fetch models failed: ${res.statusText}`);
  return res.json() as Promise<BYOMModel[]>;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function BYOMTab() {
  // -- Section 1: Upload --
  const [modelName, setModelName] = useState('');
  const [modelType, setModelType] = useState<ModelType>('Classification');
  const [modelFile, setModelFile] = useState<File | null>(null);
  const [validating, setValidating] = useState(false);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [validationError, setValidationError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // -- Section 2: Adapter Config --
  const [adapter, setAdapter] = useState<AdapterConfig>({
    resize_w: 224,
    resize_h: 224,
    normalize: true,
    mean: '0.485, 0.456, 0.406',
    std: '0.229, 0.224, 0.225',
    color_space: 'RGB',
    output_type: 'probabilities',
    classes: '',
    confidence_threshold: 0.5,
  });

  // -- Section 3: Pipeline Node Config --
  const [nodeConfig, setNodeConfig] = useState<PipelineNodeConfig>({
    node_name: '',
    category: NODE_CATEGORIES[0],
    icon_index: 0,
  });
  const [registering, setRegistering] = useState(false);
  const [registerError, setRegisterError] = useState('');

  // -- My BYOM Models --
  const [models, setModels] = useState<BYOMModel[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);

  // -----------------------------------------------------------------------
  // Load models on mount
  // -----------------------------------------------------------------------
  const loadModels = useCallback(async () => {
    setModelsLoading(true);
    try {
      const data = await apiListModels();
      setModels(data);
    } catch {
      // silently fall back to empty
    } finally {
      setModelsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadModels();
  }, [loadModels]);

  // -----------------------------------------------------------------------
  // Handlers
  // -----------------------------------------------------------------------
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null;
    setModelFile(file);
    setValidation(null);
    setValidationError('');
  };

  const handleValidate = async () => {
    if (!modelFile || !modelName) return;
    setValidating(true);
    setValidation(null);
    setValidationError('');
    try {
      const fd = new FormData();
      fd.append('file', modelFile);
      fd.append('model_name', modelName);
      fd.append('model_type', modelType);
      const result = await apiValidate(fd);
      setValidation(result);
    } catch (err) {
      setValidationError(err instanceof Error ? err.message : 'Unknown validation error');
    } finally {
      setValidating(false);
    }
  };

  const handleRegister = async () => {
    if (!validation?.valid || !modelName) return;
    setRegistering(true);
    setRegisterError('');
    try {
      const payload = {
        model_name: modelName,
        model_type: modelType,
        file_name: modelFile?.name ?? '',
        input_shape: validation.input_shape,
        output_shape: validation.output_shape,
        adapter: {
          resize_w: adapter.resize_w,
          resize_h: adapter.resize_h,
          normalize: adapter.normalize,
          mean: adapter.mean.split(',').map((v) => parseFloat(v.trim())),
          std: adapter.std.split(',').map((v) => parseFloat(v.trim())),
          color_space: adapter.color_space,
          output_type: adapter.output_type,
          classes: adapter.classes,
          confidence_threshold: adapter.confidence_threshold,
        },
        node: {
          node_name: nodeConfig.node_name || modelName,
          category: nodeConfig.category,
          icon: PRESET_ICONS[nodeConfig.icon_index].label,
        },
      };
      await apiRegister(payload);
      await loadModels();
      // Reset form
      setModelName('');
      setModelFile(null);
      setValidation(null);
      setValidationError('');
      setNodeConfig({ node_name: '', category: NODE_CATEGORIES[0], icon_index: 0 });
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (err) {
      setRegisterError(err instanceof Error ? err.message : 'Registration failed');
    } finally {
      setRegistering(false);
    }
  };

  const updateAdapter = <K extends keyof AdapterConfig>(key: K, value: AdapterConfig[K]) => {
    setAdapter((prev) => ({ ...prev, [key]: value }));
  };

  // -----------------------------------------------------------------------
  // Render helpers
  // -----------------------------------------------------------------------
  const inputCls =
    'w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 focus:outline-none';
  const labelCls = 'block text-xs font-medium text-gray-600 mb-1';
  const sectionCls = 'border border-gray-200 rounded-xl bg-white p-6 shadow-sm space-y-4';

  return (
    <div className="space-y-6">
      {/* ================================================================= */}
      {/* Section 1 — Upload & Validate                                     */}
      {/* ================================================================= */}
      <div className={sectionCls}>
        <h2 className="text-lg font-semibold text-gray-900">Upload Model</h2>
        <p className="text-sm text-gray-500">
          Upload a custom model file and validate its structure before creating a pipeline node.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Model Name */}
          <div>
            <label className={labelCls}>Model Name</label>
            <input
              type="text"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              placeholder="my-custom-model"
              className={inputCls}
            />
          </div>

          {/* Model Type */}
          <div>
            <label className={labelCls}>Model Type</label>
            <select
              value={modelType}
              onChange={(e) => setModelType(e.target.value as ModelType)}
              className={inputCls}
            >
              {MODEL_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>

          {/* File Upload */}
          <div>
            <label className={labelCls}>Model File (.onnx, .pt, .pth, .tflite)</label>
            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_EXTENSIONS}
              onChange={handleFileChange}
              className="w-full text-sm text-gray-600 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-brand-50 file:text-brand-700 hover:file:bg-brand-100"
            />
          </div>
        </div>

        {/* Validate Button */}
        <button
          onClick={() => void handleValidate()}
          disabled={!modelFile || !modelName || validating}
          className="px-6 py-2 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          {validating ? 'Validating...' : 'Validate Model'}
        </button>

        {/* Validation Result */}
        {validation && (
          <div
            className={`rounded-lg px-4 py-3 text-sm font-mono ${
              validation.valid
                ? 'bg-green-50 text-green-800 border border-green-200'
                : 'bg-red-50 text-red-800 border border-red-200'
            }`}
          >
            {validation.valid
              ? `\u2713 Valid \u00B7 Input: ${validation.input_shape} \u00B7 Output: ${validation.output_shape}`
              : `\u2717 Invalid model`}
          </div>
        )}

        {validationError && (
          <div className="rounded-lg px-4 py-3 text-sm bg-red-50 text-red-700 border border-red-200">
            {validationError}
          </div>
        )}
      </div>

      {/* ================================================================= */}
      {/* Section 2 — Configure Adapter                                     */}
      {/* ================================================================= */}
      <div className={sectionCls}>
        <h2 className="text-lg font-semibold text-gray-900">Configure Adapter</h2>
        <p className="text-sm text-gray-500">
          Define preprocessing, output format, and confidence settings for your model.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Resize W x H */}
          <div>
            <label className={labelCls}>Resize Width</label>
            <input
              type="number"
              min={1}
              value={adapter.resize_w}
              onChange={(e) => updateAdapter('resize_w', parseInt(e.target.value, 10) || 1)}
              className={inputCls}
            />
          </div>
          <div>
            <label className={labelCls}>Resize Height</label>
            <input
              type="number"
              min={1}
              value={adapter.resize_h}
              onChange={(e) => updateAdapter('resize_h', parseInt(e.target.value, 10) || 1)}
              className={inputCls}
            />
          </div>

          {/* Normalize Toggle + Mean / Std */}
          <div>
            <label className={labelCls}>Normalize</label>
            <div className="flex items-center gap-3 mt-1">
              <button
                onClick={() => updateAdapter('normalize', !adapter.normalize)}
                className={`relative w-10 h-5 rounded-full transition-colors ${
                  adapter.normalize ? 'bg-brand-600' : 'bg-gray-300'
                }`}
              >
                <span
                  className={`absolute top-0.5 left-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform ${
                    adapter.normalize ? 'translate-x-5' : ''
                  }`}
                />
              </button>
              <span className="text-xs text-gray-500">
                {adapter.normalize ? 'On' : 'Off'}
              </span>
            </div>
          </div>

          {/* Color Space */}
          <div>
            <label className={labelCls}>Color Space</label>
            <select
              value={adapter.color_space}
              onChange={(e) => updateAdapter('color_space', e.target.value as ColorSpace)}
              className={inputCls}
            >
              {COLOR_SPACES.map((cs) => (
                <option key={cs} value={cs}>
                  {cs}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Mean / Std — shown when normalize is on */}
        {adapter.normalize && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>Mean (comma-separated)</label>
              <input
                type="text"
                value={adapter.mean}
                onChange={(e) => updateAdapter('mean', e.target.value)}
                placeholder="0.485, 0.456, 0.406"
                className={inputCls}
              />
            </div>
            <div>
              <label className={labelCls}>Std (comma-separated)</label>
              <input
                type="text"
                value={adapter.std}
                onChange={(e) => updateAdapter('std', e.target.value)}
                placeholder="0.229, 0.224, 0.225"
                className={inputCls}
              />
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Output Type */}
          <div>
            <label className={labelCls}>Output Type</label>
            <select
              value={adapter.output_type}
              onChange={(e) => updateAdapter('output_type', e.target.value as OutputType)}
              className={inputCls}
            >
              {OUTPUT_TYPES.map((ot) => (
                <option key={ot} value={ot}>
                  {ot.replace('_', ' ')}
                </option>
              ))}
            </select>
          </div>

          {/* Classes — file upload or paste */}
          <div className="md:col-span-2">
            <label className={labelCls}>Classes (paste list or upload .txt file)</label>
            <div className="flex gap-2">
              <textarea
                value={adapter.classes}
                onChange={(e) => updateAdapter('classes', e.target.value)}
                placeholder="person&#10;car&#10;bicycle&#10;..."
                rows={3}
                className={`${inputCls} flex-1`}
              />
              <label className="flex items-center justify-center px-3 border border-gray-300 rounded-lg text-xs text-gray-500 cursor-pointer hover:bg-gray-50">
                Upload .txt
                <input
                  type="file"
                  accept=".txt"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (!file) return;
                    const reader = new FileReader();
                    reader.onload = (ev) => {
                      const text = ev.target?.result;
                      if (typeof text === 'string') updateAdapter('classes', text);
                    };
                    reader.readAsText(file);
                  }}
                />
              </label>
            </div>
          </div>
        </div>

        {/* Confidence Threshold Slider */}
        <div className="max-w-md">
          <label className={labelCls}>
            Confidence Threshold: {adapter.confidence_threshold.toFixed(2)}
          </label>
          <input
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={adapter.confidence_threshold}
            onChange={(e) => updateAdapter('confidence_threshold', parseFloat(e.target.value))}
            className="w-full accent-brand-600"
          />
          <div className="flex justify-between text-[10px] text-gray-400">
            <span>0.00</span>
            <span>0.50</span>
            <span>1.00</span>
          </div>
        </div>
      </div>

      {/* ================================================================= */}
      {/* Section 3 — Pipeline Node Config                                  */}
      {/* ================================================================= */}
      <div className={sectionCls}>
        <h2 className="text-lg font-semibold text-gray-900">Pipeline Node Config</h2>
        <p className="text-sm text-gray-500">
          Configure how this model appears as a node in the visual pipeline editor.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Node Name */}
          <div>
            <label className={labelCls}>Node Name</label>
            <input
              type="text"
              value={nodeConfig.node_name}
              onChange={(e) =>
                setNodeConfig((prev) => ({ ...prev, node_name: e.target.value }))
              }
              placeholder={modelName || 'my-model-node'}
              className={inputCls}
            />
          </div>

          {/* Category */}
          <div>
            <label className={labelCls}>Category</label>
            <select
              value={nodeConfig.category}
              onChange={(e) =>
                setNodeConfig((prev) => ({ ...prev, category: e.target.value }))
              }
              className={inputCls}
            >
              {NODE_CATEGORIES.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>

          {/* Icon Selector */}
          <div>
            <label className={labelCls}>Icon</label>
            <div className="grid grid-cols-4 gap-2">
              {PRESET_ICONS.map((icon, idx) => (
                <button
                  key={icon.label}
                  onClick={() =>
                    setNodeConfig((prev) => ({ ...prev, icon_index: idx }))
                  }
                  title={icon.label}
                  className={`p-2 rounded-lg border transition-colors ${
                    nodeConfig.icon_index === idx
                      ? 'border-brand-600 bg-brand-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <svg
                    className="h-5 w-5 text-gray-700 mx-auto"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={1.5}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d={icon.path} />
                  </svg>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Register Button */}
        <button
          onClick={() => void handleRegister()}
          disabled={!validation?.valid || registering}
          className="px-6 py-2 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          {registering ? 'Creating...' : 'Create Pipeline Node'}
        </button>

        {registerError && (
          <div className="rounded-lg px-4 py-3 text-sm bg-red-50 text-red-700 border border-red-200">
            {registerError}
          </div>
        )}
      </div>

      {/* ================================================================= */}
      {/* My BYOM Models                                                    */}
      {/* ================================================================= */}
      <div className="space-y-3">
        <h2 className="text-lg font-semibold text-gray-900">My BYOM Models</h2>

        {modelsLoading && (
          <p className="text-sm text-gray-400">Loading models...</p>
        )}

        {!modelsLoading && models.length === 0 && (
          <p className="text-sm text-gray-400">
            No BYOM models registered yet. Upload and validate a model above to get started.
          </p>
        )}

        {models.map((m) => (
          <div
            key={m.model_id}
            className="flex items-center gap-4 border border-gray-200 rounded-xl bg-white p-4 shadow-sm"
          >
            {/* Icon */}
            <span className="flex items-center justify-center h-10 w-10 rounded-lg bg-brand-50">
              <svg
                className="h-5 w-5 text-brand-600"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth={1.5}
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d={PRESET_ICONS[1].path} />
              </svg>
            </span>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-semibold text-gray-900">{m.model_name}</h3>
              <p className="text-xs text-gray-500">
                {m.model_type} | {m.file_name} | Input: {m.input_shape} | Output: {m.output_shape}
              </p>
            </div>

            {/* Node name badge */}
            {m.node_name && (
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-indigo-100 text-indigo-700">
                {m.node_name}
              </span>
            )}

            {/* Status */}
            <span
              className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${
                STATUS_COLORS[m.status] || 'bg-gray-100 text-gray-600'
              }`}
            >
              {m.status}
            </span>

            {/* Created */}
            <span className="text-[10px] text-gray-400 font-mono whitespace-nowrap">
              {new Date(m.created_at).toLocaleDateString()}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
