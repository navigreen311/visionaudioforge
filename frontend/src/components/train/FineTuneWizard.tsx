'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type TaskBadge = 'Vision' | 'Audio' | 'Multimodal';

interface BackboneModel {
  id: string;
  name: string;
  params: string;
  task: TaskBadge;
  useCase: string;
}

interface Dataset {
  id: string;
  name: string;
  modality: string;
  sampleCount: number;
  version: string;
}

interface LoRAConfig {
  enabled: boolean;
  rank: 4 | 8 | 16 | 32;
  alpha: number;
}

interface HyperParams {
  epochs: number;
  learningRate: number;
  batchSize: 8 | 16 | 32 | 64;
  optimizer: 'Adam' | 'AdamW' | 'SGD';
  lora: LoRAConfig;
  quantize: { enabled: boolean; mode: 'INT8' | 'FP16' };
}

interface FineTuneConfig {
  backbone: BackboneModel;
  dataset: Dataset;
  hyperParams: HyperParams;
}

interface FineTuneWizardProps {
  isOpen: boolean;
  onClose: () => void;
  onStart: (config: FineTuneConfig) => void;
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const BACKBONE_MODELS: BackboneModel[] = [
  { id: 'resnet18',        name: 'ResNet-18',        params: '11.7M',  task: 'Vision',     useCase: 'Lightweight image classification' },
  { id: 'resnet50',        name: 'ResNet-50',        params: '25.6M',  task: 'Vision',     useCase: 'General image classification & detection' },
  { id: 'vit-b-16',        name: 'ViT-B/16',         params: '86M',    task: 'Vision',     useCase: 'Vision transformer for high-accuracy tasks' },
  { id: 'efficientnet-b0', name: 'EfficientNet-B0',  params: '5.3M',   task: 'Vision',     useCase: 'Efficient mobile / edge inference' },
  { id: 'clip-vit-b-32',   name: 'CLIP ViT-B/32',    params: '151M',   task: 'Multimodal', useCase: 'Cross-modal image-text retrieval' },
  { id: 'whisper-small',   name: 'Whisper-Small',    params: '244M',   task: 'Audio',      useCase: 'Multilingual speech recognition' },
  { id: 'wav2vec2',        name: 'Wav2Vec2',         params: '95M',    task: 'Audio',      useCase: 'Self-supervised speech representation' },
  { id: 'clap',            name: 'CLAP',             params: '155M',   task: 'Multimodal', useCase: 'Audio-text contrastive learning' },
];

const LR_PRESETS = [1e-3, 1e-4, 1e-5] as const;
const BATCH_SIZES = [8, 16, 32, 64] as const;
const OPTIMIZERS = ['Adam', 'AdamW', 'SGD'] as const;
const LORA_RANKS = [4, 8, 16, 32] as const;

const TASK_COLORS: Record<TaskBadge, string> = {
  Vision:     'bg-blue-100 text-blue-700',
  Audio:      'bg-amber-100 text-amber-700',
  Multimodal: 'bg-purple-100 text-purple-700',
};

const STEP_LABELS = ['Choose Backbone', 'Select Dataset', 'Hyperparameters', 'Review & Start'];

/* ------------------------------------------------------------------ */
/*  Default hyper-params                                               */
/* ------------------------------------------------------------------ */

const DEFAULT_HYPER: HyperParams = {
  epochs: 10,
  learningRate: 1e-4,
  batchSize: 16,
  optimizer: 'AdamW',
  lora: { enabled: false, rank: 8, alpha: 16 },
  quantize: { enabled: false, mode: 'FP16' },
};

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

function StepIndicator({ current }: { current: number }) {
  return (
    <div className="flex items-center justify-center gap-2 mb-6">
      {STEP_LABELS.map((label, idx) => {
        const stepNum = idx + 1;
        const isActive = idx === current;
        const isDone = idx < current;
        return (
          <React.Fragment key={label}>
            {idx > 0 && (
              <div
                className={`h-px w-8 ${isDone ? 'bg-brand-500' : 'bg-gray-200'}`}
              />
            )}
            <div className="flex items-center gap-1.5">
              <span
                className={`flex items-center justify-center h-6 w-6 rounded-full text-xs font-semibold
                  ${isActive ? 'bg-brand-500 text-white' : isDone ? 'bg-brand-100 text-brand-700' : 'bg-gray-100 text-gray-400'}`}
              >
                {isDone ? '✓' : stepNum}
              </span>
              <span
                className={`text-xs hidden sm:inline ${isActive ? 'font-semibold text-gray-800' : 'text-gray-400'}`}
              >
                {label}
              </span>
            </div>
          </React.Fragment>
        );
      })}
    </div>
  );
}

/* ---------- Step 1: Choose Backbone ---------- */

function StepBackbone({
  selected,
  onSelect,
}: {
  selected: BackboneModel | null;
  onSelect: (m: BackboneModel) => void;
}) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Choose a backbone model</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {BACKBONE_MODELS.map((m) => {
          const isSelected = selected?.id === m.id;
          return (
            <button
              key={m.id}
              type="button"
              onClick={() => onSelect(m)}
              className={`text-left rounded-lg border p-3 transition-all
                ${isSelected
                  ? 'border-brand-500 ring-2 ring-brand-200 bg-brand-50'
                  : 'border-gray-200 hover:border-gray-300 bg-white'}`}
            >
              <div className="flex items-start justify-between mb-1.5">
                <span className="text-sm font-medium text-gray-800">{m.name}</span>
                <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${TASK_COLORS[m.task]}`}>
                  {m.task}
                </span>
              </div>
              <p className="text-xs text-gray-500 mb-2">{m.useCase}</p>
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-gray-400">{m.params} params</span>
                <span
                  className={`text-[11px] font-medium ${isSelected ? 'text-brand-600' : 'text-gray-400'}`}
                >
                  {isSelected ? 'Selected' : 'Select'}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

/* ---------- Step 2: Select Dataset ---------- */

function StepDataset({
  selected,
  onSelect,
}: {
  selected: Dataset | null;
  onSelect: (d: Dataset) => void;
}) {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetch('/api/datasets')
      .then(async (res) => {
        if (!res.ok) throw new Error(`Failed to fetch datasets (${res.status})`);
        return res.json() as Promise<Dataset[]>;
      })
      .then((data) => {
        if (!cancelled) setDatasets(data);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12 text-sm text-gray-400">
        Loading datasets...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-12 text-sm text-red-500">
        {error}
      </div>
    );
  }

  if (datasets.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <div className="text-3xl mb-2">📂</div>
        <p className="text-sm font-medium text-gray-600 mb-1">No datasets found</p>
        <p className="text-xs text-gray-400">Upload a dataset first</p>
      </div>
    );
  }

  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Select a dataset</h3>
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs text-gray-500">
              <th className="px-3 py-2 font-medium">Name</th>
              <th className="px-3 py-2 font-medium">Modality</th>
              <th className="px-3 py-2 font-medium">Samples</th>
              <th className="px-3 py-2 font-medium">Version</th>
            </tr>
          </thead>
          <tbody>
            {datasets.map((d) => {
              const isSelected = selected?.id === d.id;
              return (
                <tr
                  key={d.id}
                  onClick={() => onSelect(d)}
                  className={`cursor-pointer border-t border-gray-100 transition-colors
                    ${isSelected ? 'bg-brand-50' : 'hover:bg-gray-50'}`}
                >
                  <td className="px-3 py-2 font-medium text-gray-800">{d.name}</td>
                  <td className="px-3 py-2 text-gray-500">{d.modality}</td>
                  <td className="px-3 py-2 text-gray-500">{d.sampleCount.toLocaleString()}</td>
                  <td className="px-3 py-2 text-gray-400">{d.version}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ---------- Step 3: Hyperparameters ---------- */

function StepHyperParams({
  params,
  datasetSize,
  onChange,
}: {
  params: HyperParams;
  datasetSize: number;
  onChange: (p: HyperParams) => void;
}) {
  const update = useCallback(
    <K extends keyof HyperParams>(key: K, value: HyperParams[K]) => {
      onChange({ ...params, [key]: value });
    },
    [params, onChange],
  );

  const costEstimate = useMemo(() => {
    if (datasetSize === 0) return null;
    const steps = params.epochs * (datasetSize / params.batchSize);
    const hours = steps * 0.001;
    const cost = hours * 0.5;
    return { hours: hours.toFixed(2), cost: cost.toFixed(2) };
  }, [params.epochs, params.batchSize, datasetSize]);

  return (
    <div className="space-y-5">
      <h3 className="text-sm font-semibold text-gray-700">Configure hyperparameters</h3>

      {/* Epochs */}
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Epochs</label>
        <input
          type="number"
          min={1}
          max={500}
          value={params.epochs}
          onChange={(e) => update('epochs', Math.max(1, parseInt(e.target.value, 10) || 1))}
          className="w-24 border border-gray-200 rounded px-2 py-1.5 text-sm focus:ring-1 focus:ring-brand-500 focus:border-brand-500"
        />
      </div>

      {/* Learning Rate */}
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Learning Rate</label>
        <div className="flex items-center gap-2">
          <input
            type="number"
            step="0.0001"
            min={0}
            value={params.learningRate}
            onChange={(e) => update('learningRate', parseFloat(e.target.value) || 1e-4)}
            className="w-32 border border-gray-200 rounded px-2 py-1.5 text-sm focus:ring-1 focus:ring-brand-500 focus:border-brand-500"
          />
          <div className="flex gap-1">
            {LR_PRESETS.map((lr) => (
              <button
                key={lr}
                type="button"
                onClick={() => update('learningRate', lr)}
                className={`text-xs px-2 py-1 rounded border transition-colors
                  ${params.learningRate === lr
                    ? 'border-brand-500 bg-brand-50 text-brand-700'
                    : 'border-gray-200 text-gray-500 hover:border-gray-300'}`}
              >
                {lr.toExponential()}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Batch Size */}
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Batch Size</label>
        <select
          value={params.batchSize}
          onChange={(e) => update('batchSize', parseInt(e.target.value, 10) as 8 | 16 | 32 | 64)}
          className="w-24 border border-gray-200 rounded px-2 py-1.5 text-sm focus:ring-1 focus:ring-brand-500 focus:border-brand-500"
        >
          {BATCH_SIZES.map((bs) => (
            <option key={bs} value={bs}>{bs}</option>
          ))}
        </select>
      </div>

      {/* Optimizer */}
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Optimizer</label>
        <div className="flex gap-2">
          {OPTIMIZERS.map((opt) => (
            <button
              key={opt}
              type="button"
              onClick={() => update('optimizer', opt)}
              className={`text-xs px-3 py-1.5 rounded border transition-colors
                ${params.optimizer === opt
                  ? 'border-brand-500 bg-brand-50 text-brand-700 font-medium'
                  : 'border-gray-200 text-gray-500 hover:border-gray-300'}`}
            >
              {opt}
            </button>
          ))}
        </div>
      </div>

      {/* LoRA Toggle */}
      <div className="border border-gray-200 rounded-lg p-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-gray-600">LoRA (Low-Rank Adaptation)</span>
          <button
            type="button"
            onClick={() =>
              update('lora', { ...params.lora, enabled: !params.lora.enabled })
            }
            className={`relative w-9 h-5 rounded-full transition-colors
              ${params.lora.enabled ? 'bg-brand-500' : 'bg-gray-300'}`}
          >
            <span
              className={`absolute top-0.5 left-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform
                ${params.lora.enabled ? 'translate-x-4' : 'translate-x-0'}`}
            />
          </button>
        </div>
        {params.lora.enabled && (
          <div className="flex gap-4 mt-2">
            <div>
              <label className="block text-[11px] text-gray-500 mb-1">Rank</label>
              <select
                value={params.lora.rank}
                onChange={(e) =>
                  update('lora', {
                    ...params.lora,
                    rank: parseInt(e.target.value, 10) as 4 | 8 | 16 | 32,
                  })
                }
                className="w-20 border border-gray-200 rounded px-2 py-1 text-xs focus:ring-1 focus:ring-brand-500"
              >
                {LORA_RANKS.map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-[11px] text-gray-500 mb-1">Alpha</label>
              <input
                type="number"
                min={1}
                value={params.lora.alpha}
                onChange={(e) =>
                  update('lora', {
                    ...params.lora,
                    alpha: Math.max(1, parseInt(e.target.value, 10) || 1),
                  })
                }
                className="w-20 border border-gray-200 rounded px-2 py-1 text-xs focus:ring-1 focus:ring-brand-500"
              />
            </div>
          </div>
        )}
      </div>

      {/* Quantize Toggle */}
      <div className="border border-gray-200 rounded-lg p-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-gray-600">Quantization</span>
          <button
            type="button"
            onClick={() =>
              update('quantize', { ...params.quantize, enabled: !params.quantize.enabled })
            }
            className={`relative w-9 h-5 rounded-full transition-colors
              ${params.quantize.enabled ? 'bg-brand-500' : 'bg-gray-300'}`}
          >
            <span
              className={`absolute top-0.5 left-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform
                ${params.quantize.enabled ? 'translate-x-4' : 'translate-x-0'}`}
            />
          </button>
        </div>
        {params.quantize.enabled && (
          <div className="flex gap-2 mt-2">
            {(['INT8', 'FP16'] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => update('quantize', { ...params.quantize, mode })}
                className={`text-xs px-3 py-1 rounded border transition-colors
                  ${params.quantize.mode === mode
                    ? 'border-brand-500 bg-brand-50 text-brand-700 font-medium'
                    : 'border-gray-200 text-gray-500 hover:border-gray-300'}`}
              >
                {mode}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Training Cost Estimate */}
      {costEstimate && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
          <h4 className="text-xs font-medium text-gray-600 mb-1.5">Training Cost Estimate</h4>
          <div className="flex items-baseline gap-4">
            <div>
              <span className="text-lg font-semibold text-gray-800">${costEstimate.cost}</span>
              <span className="text-xs text-gray-400 ml-1">est. cost</span>
            </div>
            <div>
              <span className="text-sm font-medium text-gray-600">{costEstimate.hours} hrs</span>
              <span className="text-xs text-gray-400 ml-1">est. time</span>
            </div>
          </div>
          <p className="text-[10px] text-gray-400 mt-1.5">
            Formula: {params.epochs} epochs x {datasetSize.toLocaleString()} samples / {params.batchSize} batch x 0.001 hrs x $0.50/hr
          </p>
        </div>
      )}
    </div>
  );
}

/* ---------- Step 4: Review ---------- */

function StepReview({
  backbone,
  dataset,
  hyperParams,
}: {
  backbone: BackboneModel;
  dataset: Dataset;
  hyperParams: HyperParams;
}) {
  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-gray-700">Review your configuration</h3>

      {/* Backbone */}
      <div className="border border-gray-200 rounded-lg p-3">
        <h4 className="text-[11px] uppercase tracking-wide text-gray-400 mb-1.5">Backbone</h4>
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-800">{backbone.name}</span>
          <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${TASK_COLORS[backbone.task]}`}>
            {backbone.task}
          </span>
          <span className="text-xs text-gray-400">{backbone.params} params</span>
        </div>
      </div>

      {/* Dataset */}
      <div className="border border-gray-200 rounded-lg p-3">
        <h4 className="text-[11px] uppercase tracking-wide text-gray-400 mb-1.5">Dataset</h4>
        <div className="flex items-center gap-3 text-sm">
          <span className="font-medium text-gray-800">{dataset.name}</span>
          <span className="text-gray-400">{dataset.modality}</span>
          <span className="text-gray-400">{dataset.sampleCount.toLocaleString()} samples</span>
          <span className="text-gray-400">v{dataset.version}</span>
        </div>
      </div>

      {/* Hyperparameters */}
      <div className="border border-gray-200 rounded-lg p-3">
        <h4 className="text-[11px] uppercase tracking-wide text-gray-400 mb-2">Hyperparameters</h4>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-y-2 gap-x-4 text-sm">
          <div>
            <span className="text-xs text-gray-400">Epochs</span>
            <p className="font-medium text-gray-800">{hyperParams.epochs}</p>
          </div>
          <div>
            <span className="text-xs text-gray-400">Learning Rate</span>
            <p className="font-medium text-gray-800">{hyperParams.learningRate.toExponential()}</p>
          </div>
          <div>
            <span className="text-xs text-gray-400">Batch Size</span>
            <p className="font-medium text-gray-800">{hyperParams.batchSize}</p>
          </div>
          <div>
            <span className="text-xs text-gray-400">Optimizer</span>
            <p className="font-medium text-gray-800">{hyperParams.optimizer}</p>
          </div>
          {hyperParams.lora.enabled && (
            <div>
              <span className="text-xs text-gray-400">LoRA</span>
              <p className="font-medium text-gray-800">
                Rank {hyperParams.lora.rank}, Alpha {hyperParams.lora.alpha}
              </p>
            </div>
          )}
          {hyperParams.quantize.enabled && (
            <div>
              <span className="text-xs text-gray-400">Quantization</span>
              <p className="font-medium text-gray-800">{hyperParams.quantize.mode}</p>
            </div>
          )}
        </div>
      </div>

      {/* Cost */}
      {(() => {
        const steps = hyperParams.epochs * (dataset.sampleCount / hyperParams.batchSize);
        const hours = steps * 0.001;
        const cost = hours * 0.5;
        return (
          <div className="bg-brand-50 border border-brand-200 rounded-lg p-3">
            <h4 className="text-[11px] uppercase tracking-wide text-brand-600 mb-1">Estimated Cost</h4>
            <span className="text-lg font-semibold text-brand-700">${cost.toFixed(2)}</span>
            <span className="text-xs text-brand-500 ml-2">{hours.toFixed(2)} hrs</span>
          </div>
        );
      })()}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Wizard Component                                              */
/* ------------------------------------------------------------------ */

export default function FineTuneWizard({ isOpen, onClose, onStart }: FineTuneWizardProps) {
  const [step, setStep] = useState(0);
  const [backbone, setBackbone] = useState<BackboneModel | null>(null);
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [hyperParams, setHyperParams] = useState<HyperParams>(DEFAULT_HYPER);

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setStep(0);
      setBackbone(null);
      setDataset(null);
      setHyperParams(DEFAULT_HYPER);
    }
  }, [isOpen]);

  // Close on Escape key
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isOpen, onClose]);

  const canNext = useMemo(() => {
    switch (step) {
      case 0: return backbone !== null;
      case 1: return dataset !== null;
      case 2: return true;
      case 3: return true;
      default: return false;
    }
  }, [step, backbone, dataset]);

  const handleNext = useCallback(() => {
    if (step < 3) setStep((s) => s + 1);
  }, [step]);

  const handleBack = useCallback(() => {
    if (step > 0) setStep((s) => s - 1);
  }, [step]);

  const handleStart = useCallback(() => {
    if (!backbone || !dataset) return;
    onStart({ backbone, dataset, hyperParams });
  }, [backbone, dataset, hyperParams, onStart]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-label="Fine-tune wizard"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-3xl max-h-[90vh] bg-white rounded-xl shadow-2xl flex flex-col mx-4 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <h2 className="text-base font-semibold text-gray-800">Fine-Tune Model</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Step Indicator */}
        <div className="px-5 pt-4">
          <StepIndicator current={step} />
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 pb-4">
          {step === 0 && (
            <StepBackbone selected={backbone} onSelect={setBackbone} />
          )}
          {step === 1 && (
            <StepDataset selected={dataset} onSelect={setDataset} />
          )}
          {step === 2 && (
            <StepHyperParams
              params={hyperParams}
              datasetSize={dataset?.sampleCount ?? 0}
              onChange={setHyperParams}
            />
          )}
          {step === 3 && backbone && dataset && (
            <StepReview
              backbone={backbone}
              dataset={dataset}
              hyperParams={hyperParams}
            />
          )}
        </div>

        {/* Footer Navigation */}
        <div className="flex items-center justify-between px-5 py-3 border-t border-gray-100 bg-gray-50">
          <button
            type="button"
            onClick={handleBack}
            disabled={step === 0}
            className="text-sm text-gray-500 hover:text-gray-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            Back
          </button>

          <span className="text-xs text-gray-400">
            Step {step + 1} of {STEP_LABELS.length}
          </span>

          {step < 3 ? (
            <button
              type="button"
              onClick={handleNext}
              disabled={!canNext}
              className="px-4 py-1.5 text-sm font-medium text-white bg-brand-500 rounded-lg
                hover:bg-brand-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Next
            </button>
          ) : (
            <button
              type="button"
              onClick={handleStart}
              className="px-4 py-1.5 text-sm font-medium text-white bg-green-600 rounded-lg
                hover:bg-green-700 transition-colors"
            >
              Start Fine-tuning
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
