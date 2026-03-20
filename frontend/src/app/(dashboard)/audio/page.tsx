"use client";

import React, { useState } from "react";
import Tabs from "@/components/ui/Tabs";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import AudioUploadPlayer from "@/components/audio/AudioUploadPlayer";
import SpectrogramDisplay from "@/components/audio/SpectrogramDisplay";
import AugmentationBuilder from "@/components/audio/AugmentationBuilder";
import LiveMicVisualizer from "@/components/audio/LiveMicVisualizer";
import {
  analyzeAudio,
  augmentAudio,
  type AudioAnalysisResult,
  type AugmentationConfig,
  type AugmentationResult,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// Spectral Analysis Tab
// ---------------------------------------------------------------------------

function SpectralAnalysisTab() {
  const [file, setFile] = useState<File | null>(null);
  const [operations, setOperations] = useState<Set<string>>(
    new Set(["stft", "mel", "mfcc", "waveform"]),
  );
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AudioAnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const toggleOp = (op: string) => {
    setOperations((prev) => {
      const next = new Set(prev);
      if (next.has(op)) next.delete(op);
      else next.add(op);
      return next;
    });
  };

  const handleAnalyze = async () => {
    if (!file || operations.size === 0) return;
    setLoading(true);
    setError(null);
    try {
      const data = await analyzeAudio(file, Array.from(operations));
      setResult(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Analysis failed. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  };

  const OPS = [
    { id: "stft", label: "STFT" },
    { id: "mel", label: "MEL Spectrogram" },
    { id: "mfcc", label: "MFCC" },
    { id: "waveform", label: "Waveform" },
  ];

  return (
    <div className="space-y-6">
      <Card title="Upload Audio">
        <AudioUploadPlayer file={file} onFileSelected={setFile} />
      </Card>

      <Card title="Analysis Options">
        <div className="flex flex-wrap items-center gap-4">
          {OPS.map((op) => (
            <label key={op.id} className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={operations.has(op.id)}
                onChange={() => toggleOp(op.id)}
                className="h-4 w-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500"
              />
              <span className="text-sm text-gray-700">{op.label}</span>
            </label>
          ))}
          <div className="flex-1" />
          <Button
            onClick={handleAnalyze}
            disabled={!file || operations.size === 0}
            loading={loading}
          >
            Analyze
          </Button>
        </div>
      </Card>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-4">
          {result.waveform && (
            <Card title="Waveform Stats">
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                {[
                  {
                    label: "Duration",
                    value: `${result.waveform.duration.toFixed(2)}s`,
                  },
                  {
                    label: "Sample Rate",
                    value: `${result.waveform.sample_rate} Hz`,
                  },
                  {
                    label: "RMS",
                    value: result.waveform.rms.toFixed(4),
                  },
                  {
                    label: "Peak",
                    value: result.waveform.peak.toFixed(4),
                  },
                  {
                    label: "Samples",
                    value: result.waveform.samples.toLocaleString(),
                  },
                ].map((s) => (
                  <div key={s.label} className="text-center">
                    <p className="text-xs text-gray-500 uppercase tracking-wide">
                      {s.label}
                    </p>
                    <p className="text-lg font-semibold text-gray-900 tabular-nums">
                      {s.value}
                    </p>
                  </div>
                ))}
              </div>
            </Card>
          )}

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            {result.stft?.image && (
              <SpectrogramDisplay title="STFT Spectrogram" imageBase64={result.stft.image} />
            )}
            {result.mel?.image && (
              <SpectrogramDisplay title="MEL Spectrogram" imageBase64={result.mel.image} />
            )}
            {result.mfcc?.image && (
              <SpectrogramDisplay
                title="MFCC Heatmap"
                imageBase64={result.mfcc.image}
                coefficients={result.mfcc.coefficients}
              />
            )}
            {result.waveform?.image && (
              <SpectrogramDisplay title="Waveform" imageBase64={result.waveform.image} />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Augmentation Tab
// ---------------------------------------------------------------------------

function AugmentationTab() {
  const [file, setFile] = useState<File | null>(null);
  const [config, setConfig] = useState<AugmentationConfig>({});
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AugmentationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAugment = async () => {
    if (!file) return;
    if (!config.preset && (!config.steps || config.steps.length === 0)) return;
    setLoading(true);
    setError(null);
    try {
      const data = await augmentAudio(file, config);
      setResult(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Augmentation failed. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  };

  const hasConfig = !!(config.preset || (config.steps && config.steps.length > 0));

  return (
    <div className="space-y-6">
      <Card title="Upload Audio">
        <AudioUploadPlayer file={file} onFileSelected={setFile} />
      </Card>

      <Card title="Augmentation Pipeline">
        <AugmentationBuilder onConfigChange={setConfig} />
        <div className="mt-4 flex justify-end">
          <Button
            onClick={handleAugment}
            disabled={!file || !hasConfig}
            loading={loading}
          >
            Augment
          </Button>
        </div>
      </Card>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-4">
          <Card title="Augmented Audio">
            <audio
              src={`data:${result.mime_type};base64,${result.audio_base64}`}
              controls
              className="w-full mb-4"
            />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium text-gray-700 mb-2">
                  Applied Augmentations
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {result.applied.map((aug, i) => (
                    <Badge key={i} variant="info">
                      {aug}
                    </Badge>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-700 mb-2">
                  Duration Comparison
                </p>
                <div className="grid grid-cols-2 gap-3 text-center">
                  <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                    <p className="text-xs text-gray-500">Original</p>
                    <p className="text-lg font-semibold text-gray-900 tabular-nums">
                      {result.original_duration.toFixed(2)}s
                    </p>
                  </div>
                  <div className="rounded-lg border border-brand-200 bg-brand-50 p-3">
                    <p className="text-xs text-brand-600">Augmented</p>
                    <p className="text-lg font-semibold text-brand-700 tabular-nums">
                      {result.augmented_duration.toFixed(2)}s
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Live Mic Tab
// ---------------------------------------------------------------------------

function LiveMicTab() {
  return <LiveMicVisualizer />;
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function AudioPage() {
  const [activeTab, setActiveTab] = useState("spectral");

  const tabs = [
    {
      id: "spectral",
      label: "Spectral Analysis",
      content: <SpectralAnalysisTab />,
    },
    {
      id: "augmentation",
      label: "Augmentation",
      content: <AugmentationTab />,
    },
    {
      id: "live-mic",
      label: "Live Mic",
      content: <LiveMicTab />,
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Audio Analysis</h1>
        <p className="mt-1 text-sm text-gray-500">
          Spectral analysis, augmentation pipelines, and real-time microphone
          visualization powered by Librosa.
        </p>
      </div>
      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />
    </div>
  );
}
