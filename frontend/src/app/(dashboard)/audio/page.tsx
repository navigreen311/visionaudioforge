"use client";

import React, { useState, useCallback } from "react";
import Tabs from "@/components/ui/Tabs";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import AudioUploadPlayer from "@/components/audio/AudioUploadPlayer";
import SpectrogramDisplay from "@/components/audio/SpectrogramDisplay";
import AugmentationBuilder from "@/components/audio/AugmentationBuilder";
import LiveMicVisualizer from "@/components/audio/LiveMicVisualizer";
import AudioPlayer from "@/components/audio/AudioPlayer";
import LiveMicSpectrogram from "@/components/audio/LiveMicSpectrogram";
import SpectrogramViewer, {
  type SpectrogramParams,
} from "@/components/audio/SpectrogramViewer";
import MFCCHeatmap, {
  type MFCCReanalyzeParams,
} from "@/components/audio/MFCCHeatmap";
import AugmentationStudio, {
  type AugmentConfig,
} from "@/components/audio/AugmentationStudio";
import TranscriptionPanel from "@/components/audio/TranscriptionPanel";
import AudioExportPanel from "@/components/audio/AudioExportPanel";
import AudioHistory, {
  type AudioHistoryEntry,
} from "@/components/audio/AudioHistory";
import {
  analyzeAudio,
  augmentAudio,
  analyzeCall,
  type AudioAnalysisResult,
  type AugmentationConfig,
  type AugmentationStep,
  type AugmentationResult,
  type CallAnalysisResult,
  type SpeakerSentiment,
  type TalkRatioEntry,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// Spectral Analysis Tab
// ---------------------------------------------------------------------------

function SpectralAnalysisTab({
  onFileUploaded,
}: {
  onFileUploaded: (file: File) => void;
}) {
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

  const handleFileSelected = (f: File | null) => {
    setFile(f);
    if (f) onFileUploaded(f);
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

  const handleSpectrogramReanalyze = async (params: SpectrogramParams) => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const data = await analyzeAudio(file, Array.from(operations));
      setResult(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Re-analysis failed. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  };

  const handleMFCCReanalyze = async (params: MFCCReanalyzeParams) => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const data = await analyzeAudio(file, ["mfcc"]);
      setResult((prev) => (prev ? { ...prev, mfcc: data.mfcc } : data));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "MFCC re-analysis failed.",
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
        <AudioUploadPlayer file={file} onFileSelected={handleFileSelected} />
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
              <div className="space-y-4">
                <SpectrogramDisplay title="STFT Spectrogram" imageBase64={result.stft.image} />
                <SpectrogramViewer
                  spectrogramB64={result.stft.image}
                  type="stft"
                  onReanalyze={handleSpectrogramReanalyze}
                />
              </div>
            )}
            {result.mel?.image && (
              <div className="space-y-4">
                <SpectrogramDisplay title="MEL Spectrogram" imageBase64={result.mel.image} />
                <SpectrogramViewer
                  spectrogramB64={result.mel.image}
                  type="mel"
                  onReanalyze={handleSpectrogramReanalyze}
                />
              </div>
            )}
            {result.mfcc?.image && (
              <div className="space-y-4">
                <SpectrogramDisplay
                  title="MFCC Heatmap"
                  imageBase64={result.mfcc.image}
                  coefficients={result.mfcc.coefficients}
                />
                <MFCCHeatmap
                  mfccData={{
                    image_b64: result.mfcc.image,
                    coefficients: (result.mfcc.coefficients ?? []).map(
                      (c: { index: number; mean: number; std: number; values: number[] } | number[], i: number) =>
                        Array.isArray(c)
                          ? { index: i, mean: 0, std: 0, values: c }
                          : c
                    ),
                  }}
                  onReanalyze={handleMFCCReanalyze}
                />
              </div>
            )}
            {result.waveform?.image && (
              <SpectrogramDisplay title="Waveform" imageBase64={result.waveform.image} />
            )}
          </div>

          {/* Export Panel - shown when results exist */}
          <AudioExportPanel
            analysisResults={result as unknown as Record<string, unknown>}
            spectrogramB64={result.stft?.image ?? result.mel?.image ?? null}
            audioFile={file}
          />
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Augmentation Tab
// ---------------------------------------------------------------------------

function AugmentationTab({
  onFileUploaded,
}: {
  onFileUploaded: (file: File) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [config, setConfig] = useState<AugmentationConfig>({});
  const handleConfigChange = (newConfig: { preset?: string; steps?: AugmentationStep[] }) => {
    setConfig(newConfig);
  };
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AugmentationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileSelected = (f: File | null) => {
    setFile(f);
    if (f) onFileUploaded(f);
  };

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

  const handleStudioAugment = useCallback((augConfig: AugmentConfig) => {
    // These names are the augmentation API's vocabulary, not a guess at it.
    // They used to be a guess: the server dispatched on "noise" | "stretch" |
    // "pitch" | "shift" and had no waveform masker at all, so every step this
    // panel produced raised ValueError and came back as a 500 with no body.
    //
    // backend/app/services/audio/augmentation.py now accepts each of them and
    // canonicalises the parameters (amplitude -> SNR, shift_pct -> ms), and
    // backend/tests/test_console_api_contract.py reads this function to check
    // that it still does. Adding a step here with a name the server does not
    // know fails that test by name.
    const steps: AugmentationStep[] = [];
    if (augConfig.whiteNoise.enabled) {
      steps.push({ type: "white_noise", params: { snr_db: augConfig.whiteNoise.snrDb } });
    }
    if (augConfig.pinkNoise.enabled) {
      steps.push({ type: "pink_noise", params: { amplitude: augConfig.pinkNoise.amplitude } });
    }
    if (augConfig.timeStretch.enabled) {
      steps.push({ type: "time_stretch", params: { rate: augConfig.timeStretch.rate } });
    }
    if (augConfig.pitchShift.enabled) {
      steps.push({ type: "pitch_shift", params: { semitones: augConfig.pitchShift.semitones } });
    }
    if (augConfig.timeShift.enabled) {
      steps.push({ type: "time_shift", params: { shift_pct: augConfig.timeShift.shiftPct } });
    }
    if (augConfig.frequencyMask.enabled) {
      steps.push({ type: "frequency_mask", params: { mask_size_pct: augConfig.frequencyMask.maskSizePct } });
    }
    if (steps.length > 0 && file) {
      setConfig({ steps });
      // Trigger augmentation with the studio config
      setLoading(true);
      setError(null);
      augmentAudio(file, { steps })
        .then((data) => setResult(data))
        .catch((err) =>
          setError(err instanceof Error ? err.message : "Augmentation failed."),
        )
        .finally(() => setLoading(false));
    }
  }, [file]);

  const hasConfig = !!(config.preset || (config.steps && config.steps.length > 0));

  return (
    <div className="space-y-6">
      <Card title="Upload Audio">
        <AudioUploadPlayer file={file} onFileSelected={handleFileSelected} />
      </Card>

      <Card title="Augmentation Pipeline">
        <AugmentationBuilder onConfigChange={handleConfigChange} />
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

      {/* Advanced Augmentation Studio */}
      <AugmentationStudio
        originalFile={file}
        onAugment={handleStudioAugment}
        augmentedAudioB64={result?.audio_base64 ?? null}
        originalSpectrogramB64={null}
        augmentedSpectrogramB64={null}
      />

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
                  {result.applied.map((aug: string, i: number) => (
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
// Live Mic Tab (original)
// ---------------------------------------------------------------------------

function LiveMicTab() {
  return (
    <div className="space-y-6">
      <LiveMicVisualizer />
      <Card title="Live Spectrogram">
        <LiveMicSpectrogram />
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Transcription Tab
// ---------------------------------------------------------------------------

function TranscriptionTab({
  sharedFile,
}: {
  sharedFile: File | null;
}) {
  return (
    <div className="space-y-6">
      <TranscriptionPanel audioFile={sharedFile} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Call Intelligence Tab
// ---------------------------------------------------------------------------

function CallIntelligenceTab() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CallAnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const data = await analyzeCall(file);
      setResult(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Call analysis failed. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  };

  // Compute pie chart segments for talk ratio
  const talkRatioEntries = result?.talk_ratio
    ? Object.entries(result.talk_ratio)
    : [];
  const pieColors = [
    "#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6",
    "#ec4899", "#06b6d4", "#84cc16",
  ];

  return (
    <div className="space-y-6">
      <Card title="Upload Call Recording">
        <AudioUploadPlayer file={file} onFileSelected={setFile} />
        <div className="mt-4 flex justify-end">
          <Button onClick={handleAnalyze} disabled={!file} loading={loading}>
            Analyze Call
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
          {/* Duration & Speaker Count */}
          <Card title="Call Overview">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <p className="text-xs text-gray-500 uppercase tracking-wide">Duration</p>
                <p className="text-lg font-semibold text-gray-900 tabular-nums">
                  {result.duration_s.toFixed(1)}s
                </p>
              </div>
              <div className="text-center">
                <p className="text-xs text-gray-500 uppercase tracking-wide">Speakers</p>
                <p className="text-lg font-semibold text-gray-900 tabular-nums">
                  {Object.keys(result.talk_ratio).length}
                </p>
              </div>
              <div className="text-center">
                <p className="text-xs text-gray-500 uppercase tracking-wide">Action Items</p>
                <p className="text-lg font-semibold text-gray-900 tabular-nums">
                  {result.action_items.length}
                </p>
              </div>
              <div className="text-center">
                <p className="text-xs text-gray-500 uppercase tracking-wide">Summary</p>
                <p className="text-sm text-gray-700 mt-1">{result.summary || "N/A"}</p>
              </div>
            </div>
          </Card>

          {/* Speaker Transcript */}
          <Card title="Speaker-Separated Transcript">
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {result.speakers.length > 0 ? (
                result.speakers.map((seg: { speaker: string; start_s: number; end_s: number }, i: number) => (
                  <div key={i} className="flex gap-3 items-start">
                    <Badge
                      variant="info"
                    >
                      {seg.speaker}
                    </Badge>
                    <div className="flex-1">
                      <span className="text-xs text-gray-400 tabular-nums">
                        {seg.start_s.toFixed(1)}s - {seg.end_s.toFixed(1)}s
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-500">No speaker segments detected.</p>
              )}
              {result.transcript && (
                <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                  <p className="text-xs text-gray-500 uppercase mb-1">Full Transcript</p>
                  <p className="text-sm text-gray-700">{result.transcript}</p>
                </div>
              )}
            </div>
          </Card>

          {/* Action Items */}
          {result.action_items.length > 0 && (
            <Card title="Action Items">
              <ul className="list-disc list-inside space-y-1">
                {result.action_items.map((item: string, i: number) => (
                  <li key={i} className="text-sm text-gray-700">
                    {item}
                  </li>
                ))}
              </ul>
            </Card>
          )}

          {/* Sentiment per Speaker */}
          {Object.keys(result.sentiment).length > 0 && (
            <Card title="Sentiment per Speaker">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(result.sentiment).map(([speaker, sent]: [string, SpeakerSentiment]) => (
                  <div key={speaker} className="rounded-lg border border-gray-200 p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-gray-900">{speaker}</span>
                      <Badge
                        variant={
                          sent.overall === "positive"
                            ? "success"
                            : sent.overall === "negative"
                              ? "error"
                              : "neutral"
                        }
                      >
                        {sent.overall}
                      </Badge>
                    </div>
                    <div className="flex gap-4 text-xs text-gray-500">
                      <span>
                        Positive: {(sent.scores.positive * 100).toFixed(1)}%
                      </span>
                      <span>
                        Negative: {(sent.scores.negative * 100).toFixed(1)}%
                      </span>
                      <span>
                        Neutral: {(sent.scores.neutral * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Talk Ratio Pie Chart (CSS-based) */}
          {talkRatioEntries.length > 0 && (
            <Card title="Talk Ratio">
              <div className="flex items-center gap-8">
                {/* Simple CSS pie chart approximation using a stacked bar */}
                <div className="flex-1">
                  <div className="flex h-8 rounded-full overflow-hidden">
                    {talkRatioEntries.map(([speaker, data]: [string, TalkRatioEntry], i: number) => (
                      <div
                        key={speaker}
                        style={{
                          width: `${data.percentage}%`,
                          backgroundColor: pieColors[i % pieColors.length],
                        }}
                        title={`${speaker}: ${data.percentage.toFixed(1)}%`}
                        className="transition-all"
                      />
                    ))}
                  </div>
                  <div className="flex flex-wrap gap-4 mt-3">
                    {talkRatioEntries.map(([speaker, data]: [string, TalkRatioEntry], i: number) => (
                      <div key={speaker} className="flex items-center gap-2">
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{
                            backgroundColor: pieColors[i % pieColors.length],
                          }}
                        />
                        <span className="text-sm text-gray-700">
                          {speaker}: {data.percentage.toFixed(1)}% ({data.time_s.toFixed(1)}s)
                          {data.interruptions > 0 && (
                            <span className="text-xs text-red-500 ml-1">
                              ({data.interruptions} interruption{data.interruptions > 1 ? "s" : ""})
                            </span>
                          )}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function AudioPage() {
  const [activeTab, setActiveTab] = useState("spectral");
  const [sharedFile, setSharedFile] = useState<File | null>(null);

  const handleFileUploaded = useCallback((file: File) => {
    setSharedFile(file);
  }, []);

  const handleHistoryRestore = useCallback((entry: AudioHistoryEntry) => {
    // When restoring from history, switch to the relevant tab
    if (entry.operationType === "augmentation") {
      setActiveTab("augmentation");
    } else if (entry.operationType === "transcription") {
      setActiveTab("transcription");
    } else {
      setActiveTab("spectral");
    }
  }, []);

  const tabs = [
    {
      id: "spectral",
      label: "Spectral Analysis",
      content: <SpectralAnalysisTab onFileUploaded={handleFileUploaded} />,
    },
    {
      id: "augmentation",
      label: "Augmentation",
      content: <AugmentationTab onFileUploaded={handleFileUploaded} />,
    },
    {
      id: "live-mic",
      label: "Live Mic",
      content: <LiveMicTab />,
    },
    {
      id: "transcription",
      label: "Transcription",
      content: <TranscriptionTab sharedFile={sharedFile} />,
    },
    {
      id: "call-intelligence",
      label: "Call Intelligence",
      content: <CallIntelligenceTab />,
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

      {/* Persistent Audio Player - shown when a file has been uploaded */}
      {sharedFile && (
        <AudioPlayer file={sharedFile} />
      )}

      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      {/* Audio History - always visible at the bottom */}
      <AudioHistory onRestore={handleHistoryRestore} />
    </div>
  );
}
