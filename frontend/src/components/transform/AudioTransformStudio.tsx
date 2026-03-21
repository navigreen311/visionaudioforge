'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import api from '@/lib/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TransformOperation {
  name: string;
  params?: Record<string, unknown>;
}

interface ChainResponse {
  audio: string;
  sample_rate: number;
  applied?: string[];
  operations_applied?: string[];
  processing_time_ms: number;
  original_duration_s?: number;
  result_duration_s?: number;
}

interface CleanupState {
  noiseReduction: boolean;
  noiseStrength: number;
  dereverb: boolean;
  roomSize: number;
  silenceRemoval: boolean;
  silenceThresholdDb: number;
}

interface PitchTempoState {
  pitchShift: number;
  formantShift: number;
  timeStretch: number;
  preservePitch: boolean;
}

interface VoiceSpeechState {
  sourceSeparation: boolean;
  separationTarget: string;
  voiceConversion: boolean;
  voiceTarget: string;
  ttsMode: boolean;
  ttsText: string;
  ttsVoice: string;
  ttsSpeed: number;
}

interface MasteringState {
  loudnessNorm: boolean;
  lufs: number;
  eqPreset: string;
  compression: boolean;
  compressionRatio: string;
}

// ---------------------------------------------------------------------------
// Collapsible Section
// ---------------------------------------------------------------------------

function Section({
  title,
  open,
  onToggle,
  children,
}: {
  title: string;
  open: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-semibold text-gray-900 hover:bg-gray-50 transition-colors"
      >
        {title}
        <svg
          className={`h-4 w-4 text-gray-500 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && <div className="border-t border-gray-200 px-4 py-4 space-y-4">{children}</div>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Small UI helpers
// ---------------------------------------------------------------------------

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer select-none">
      <div
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') onChange(!checked);
        }}
        tabIndex={0}
        className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors ${
          checked ? 'bg-brand-600' : 'bg-gray-300'
        }`}
      >
        <span
          className={`inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform ${
            checked ? 'translate-x-4' : 'translate-x-0.5'
          }`}
        />
      </div>
      {label}
    </label>
  );
}

function Slider({
  label,
  value,
  min,
  max,
  step,
  unit,
  onChange,
  disabled,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit?: string;
  onChange: (v: number) => void;
  disabled?: boolean;
}) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm text-gray-700">
        <span>{label}</span>
        <span className="font-mono text-xs text-gray-500">
          {value}
          {unit ?? ''}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full accent-brand-600"
      />
    </div>
  );
}

function SelectField({
  label,
  value,
  options,
  onChange,
  disabled,
}: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
  disabled?: boolean;
}) {
  return (
    <label className="block text-sm text-gray-700">
      {label}
      <select
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm shadow-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

// ---------------------------------------------------------------------------
// Waveform canvas helper
// ---------------------------------------------------------------------------

function drawWaveform(
  canvas: HTMLCanvasElement,
  audioBuffer: AudioBuffer,
  color: string,
) {
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  ctx.scale(dpr, dpr);

  ctx.clearRect(0, 0, w, h);

  const data = audioBuffer.getChannelData(0);
  const samplesPerPixel = Math.max(1, Math.floor(data.length / w));

  ctx.beginPath();
  ctx.strokeStyle = color;
  ctx.lineWidth = 1;

  for (let x = 0; x < w; x++) {
    const start = x * samplesPerPixel;
    let min = 1;
    let max = -1;
    for (let j = 0; j < samplesPerPixel; j++) {
      const s = data[start + j] ?? 0;
      if (s < min) min = s;
      if (s > max) max = s;
    }
    const yLow = ((1 + min) / 2) * h;
    const yHigh = ((1 + max) / 2) * h;
    ctx.moveTo(x, yLow);
    ctx.lineTo(x, yHigh);
  }
  ctx.stroke();
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function AudioTransformStudio() {
  // -- File state --
  const [file, setFile] = useState<File | null>(null);
  const [originalUrl, setOriginalUrl] = useState<string | null>(null);
  const [transformedUrl, setTransformedUrl] = useState<string | null>(null);

  // -- AudioContext for waveform rendering --
  const audioCtxRef = useRef<AudioContext | null>(null);
  const originalBufferRef = useRef<AudioBuffer | null>(null);
  const transformedBufferRef = useRef<AudioBuffer | null>(null);
  const originalCanvasRef = useRef<HTMLCanvasElement>(null);
  const transformedCanvasRef = useRef<HTMLCanvasElement>(null);

  // -- A/B toggle --
  const [abActive, setAbActive] = useState(false);
  const [abSide, setAbSide] = useState<'A' | 'B'>('A');
  const abIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const originalPlayerRef = useRef<HTMLAudioElement>(null);
  const transformedPlayerRef = useRef<HTMLAudioElement>(null);

  // -- Processing state --
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ChainResponse | null>(null);

  // -- Section open state --
  const [openSections, setOpenSections] = useState({
    cleanup: true,
    pitchTempo: false,
    voiceSpeech: false,
    mastering: false,
  });

  // -- Control states --
  const [cleanup, setCleanup] = useState<CleanupState>({
    noiseReduction: false,
    noiseStrength: 0.5,
    dereverb: false,
    roomSize: 0.5,
    silenceRemoval: false,
    silenceThresholdDb: -40,
  });

  const [pitchTempo, setPitchTempo] = useState<PitchTempoState>({
    pitchShift: 0,
    formantShift: 0,
    timeStretch: 1.0,
    preservePitch: true,
  });

  const [voiceSpeech, setVoiceSpeech] = useState<VoiceSpeechState>({
    sourceSeparation: false,
    separationTarget: 'vocals',
    voiceConversion: false,
    voiceTarget: 'male_deep',
    ttsMode: false,
    ttsText: '',
    ttsVoice: 'default',
    ttsSpeed: 1.0,
  });

  const [mastering, setMastering] = useState<MasteringState>({
    loudnessNorm: false,
    lufs: -14,
    eqPreset: 'flat',
    compression: false,
    compressionRatio: '4:1',
  });

  // -- Drag state --
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ---------------------------------------------------------------------------
  // Cleanup AudioContext on unmount
  // ---------------------------------------------------------------------------
  useEffect(() => {
    return () => {
      if (audioCtxRef.current) {
        audioCtxRef.current.close().catch(() => {});
        audioCtxRef.current = null;
      }
      if (originalUrl) URL.revokeObjectURL(originalUrl);
      if (transformedUrl) URL.revokeObjectURL(transformedUrl);
      if (abIntervalRef.current) clearInterval(abIntervalRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---------------------------------------------------------------------------
  // Decode audio to buffer and draw waveform
  // ---------------------------------------------------------------------------
  const getAudioCtx = useCallback(() => {
    if (!audioCtxRef.current) {
      audioCtxRef.current = new AudioContext();
    }
    return audioCtxRef.current;
  }, []);

  const decodeAndDraw = useCallback(
    async (
      arrayBuffer: ArrayBuffer,
      canvas: HTMLCanvasElement | null,
      bufferRef: React.MutableRefObject<AudioBuffer | null>,
      color: string,
    ) => {
      const ctx = getAudioCtx();
      const buffer = await ctx.decodeAudioData(arrayBuffer.slice(0));
      bufferRef.current = buffer;
      if (canvas) drawWaveform(canvas, buffer, color);
    },
    [getAudioCtx],
  );

  // ---------------------------------------------------------------------------
  // Handle file selection
  // ---------------------------------------------------------------------------
  const handleFile = useCallback(
    async (f: File) => {
      setFile(f);
      setError(null);
      setResult(null);
      setTransformedUrl(null);
      transformedBufferRef.current = null;

      // Revoke old URL
      if (originalUrl) URL.revokeObjectURL(originalUrl);
      const url = URL.createObjectURL(f);
      setOriginalUrl(url);

      // Decode for waveform
      try {
        const ab = await f.arrayBuffer();
        await decodeAndDraw(ab, originalCanvasRef.current, originalBufferRef, '#3b82f6');
      } catch {
        // Non-critical: waveform may not render for all formats
      }
    },
    [originalUrl, decodeAndDraw],
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const f = e.dataTransfer.files[0];
      if (f && f.type.startsWith('audio/')) handleFile(f);
    },
    [handleFile],
  );

  const onFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const f = e.target.files?.[0];
      if (f) handleFile(f);
    },
    [handleFile],
  );

  // ---------------------------------------------------------------------------
  // Build operations array from controls
  // ---------------------------------------------------------------------------
  const buildOperations = useCallback((): TransformOperation[] => {
    const ops: TransformOperation[] = [];

    // Cleanup
    if (cleanup.noiseReduction) {
      ops.push({ name: 'denoise', params: { strength: cleanup.noiseStrength } });
    }
    if (cleanup.dereverb) {
      ops.push({ name: 'dereverb', params: { room_size: cleanup.roomSize } });
    }
    if (cleanup.silenceRemoval) {
      ops.push({ name: 'silence_remove', params: { threshold_db: cleanup.silenceThresholdDb } });
    }

    // Pitch & Tempo
    if (pitchTempo.pitchShift !== 0) {
      ops.push({ name: 'pitch_shift', params: { semitones: pitchTempo.pitchShift } });
    }
    if (pitchTempo.formantShift !== 0) {
      ops.push({ name: 'formant_shift', params: { semitones: pitchTempo.formantShift } });
    }
    if (pitchTempo.timeStretch !== 1.0) {
      ops.push({
        name: 'time_stretch',
        params: { rate: pitchTempo.timeStretch, preserve_pitch: pitchTempo.preservePitch },
      });
    }

    // Voice & Speech
    if (voiceSpeech.sourceSeparation) {
      ops.push({ name: 'source_separation', params: { target: voiceSpeech.separationTarget } });
    }
    if (voiceSpeech.voiceConversion) {
      ops.push({ name: 'voice_convert', params: { target_voice: voiceSpeech.voiceTarget } });
    }

    // Mastering
    if (mastering.loudnessNorm) {
      ops.push({ name: 'loudness', params: { target_lufs: mastering.lufs } });
    }
    if (mastering.eqPreset !== 'flat') {
      ops.push({ name: 'eq', params: { preset: mastering.eqPreset } });
    }
    if (mastering.compression) {
      const ratio = parseFloat(mastering.compressionRatio.replace(':1', ''));
      ops.push({ name: 'compress', params: { ratio } });
    }

    return ops;
  }, [cleanup, pitchTempo, voiceSpeech, mastering]);

  // ---------------------------------------------------------------------------
  // Transform handler
  // ---------------------------------------------------------------------------
  const handleTransform = useCallback(async () => {
    if (!file) return;

    // Handle TTS mode separately
    if (voiceSpeech.ttsMode && voiceSpeech.ttsText.trim()) {
      setProcessing(true);
      setError(null);
      try {
        const formData = new FormData();
        formData.append('text', voiceSpeech.ttsText);
        formData.append('voice', voiceSpeech.ttsVoice);
        formData.append('speed', String(voiceSpeech.ttsSpeed));
        const { data } = await api.post('/api/transform/audio/tts', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        if (data.audio) {
          const binary = atob(data.audio);
          const bytes = new Uint8Array(binary.length);
          for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
          const blob = new Blob([bytes], { type: 'audio/wav' });
          if (transformedUrl) URL.revokeObjectURL(transformedUrl);
          const url = URL.createObjectURL(blob);
          setTransformedUrl(url);

          const ab = bytes.buffer.slice(0);
          await decodeAndDraw(ab, transformedCanvasRef.current, transformedBufferRef, '#10b981');
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'TTS failed';
        setError(msg);
      } finally {
        setProcessing(false);
      }
      return;
    }

    const ops = buildOperations();
    if (ops.length === 0) {
      setError('Enable at least one transform operation.');
      return;
    }

    setProcessing(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('operations', JSON.stringify(ops));

      const { data } = await api.post<ChainResponse>('/api/transform/audio', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setResult(data);

      // Convert base64 audio to blob URL
      if (data.audio) {
        const binary = atob(data.audio);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
        const blob = new Blob([bytes], { type: 'audio/wav' });

        if (transformedUrl) URL.revokeObjectURL(transformedUrl);
        const url = URL.createObjectURL(blob);
        setTransformedUrl(url);

        // Decode for waveform
        const ab = bytes.buffer.slice(0);
        await decodeAndDraw(ab, transformedCanvasRef.current, transformedBufferRef, '#10b981');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Transform failed';
      setError(msg);
    } finally {
      setProcessing(false);
    }
  }, [file, voiceSpeech, buildOperations, transformedUrl, decodeAndDraw]);

  // ---------------------------------------------------------------------------
  // A/B Listen toggle (3s alternation)
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (abIntervalRef.current) {
      clearInterval(abIntervalRef.current);
      abIntervalRef.current = null;
    }

    if (!abActive || !originalUrl || !transformedUrl) {
      return;
    }

    const toggle = () => {
      setAbSide((prev) => {
        const next = prev === 'A' ? 'B' : 'A';
        if (next === 'A') {
          transformedPlayerRef.current?.pause();
          originalPlayerRef.current?.play().catch(() => {});
        } else {
          originalPlayerRef.current?.pause();
          transformedPlayerRef.current?.play().catch(() => {});
        }
        return next;
      });
    };

    // Start playing original side
    originalPlayerRef.current?.play().catch(() => {});
    setAbSide('A');

    abIntervalRef.current = setInterval(toggle, 3000);

    return () => {
      if (abIntervalRef.current) {
        clearInterval(abIntervalRef.current);
        abIntervalRef.current = null;
      }
    };
  }, [abActive, originalUrl, transformedUrl]);

  // ---------------------------------------------------------------------------
  // Section toggle helper
  // ---------------------------------------------------------------------------
  const toggleSection = (key: keyof typeof openSections) => {
    setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="space-y-6">
      {/* ----------------------------------------------------------------- */}
      {/* Audio Dropzone */}
      {/* ----------------------------------------------------------------- */}
      <div
        className={`relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors cursor-pointer ${
          dragOver
            ? 'border-brand-500 bg-brand-50'
            : 'border-gray-300 bg-gray-50 hover:border-gray-400'
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <svg
          className="mb-3 h-10 w-10 text-gray-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2z"
          />
        </svg>
        <p className="text-sm text-gray-600">
          <span className="font-medium text-brand-600">Click to upload</span> or drag and drop an
          audio file
        </p>
        <p className="mt-1 text-xs text-gray-500">Accepts audio/*</p>
        {file && (
          <p className="mt-2 text-xs text-gray-700 font-medium">
            {file.name} ({(file.size / 1024).toFixed(1)} KB)
          </p>
        )}
        <input
          ref={fileInputRef}
          type="file"
          accept="audio/*"
          onChange={onFileInput}
          className="hidden"
        />
      </div>

      {/* Simple player for the original file */}
      {originalUrl && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            Original Audio
          </p>
          <audio ref={originalPlayerRef} src={originalUrl} controls className="w-full" />
        </div>
      )}

      {/* ----------------------------------------------------------------- */}
      {/* Transform Controls */}
      {/* ----------------------------------------------------------------- */}
      <div className="space-y-3">
        {/* A. Cleanup */}
        <Section
          title="A. Cleanup"
          open={openSections.cleanup}
          onToggle={() => toggleSection('cleanup')}
        >
          <Toggle
            label="Noise Reduction"
            checked={cleanup.noiseReduction}
            onChange={(v) => setCleanup((s) => ({ ...s, noiseReduction: v }))}
          />
          {cleanup.noiseReduction && (
            <Slider
              label="Strength"
              value={cleanup.noiseStrength}
              min={0}
              max={1}
              step={0.05}
              onChange={(v) => setCleanup((s) => ({ ...s, noiseStrength: v }))}
            />
          )}

          <Toggle
            label="De-reverb"
            checked={cleanup.dereverb}
            onChange={(v) => setCleanup((s) => ({ ...s, dereverb: v }))}
          />
          {cleanup.dereverb && (
            <Slider
              label="Room Size"
              value={cleanup.roomSize}
              min={0}
              max={1}
              step={0.05}
              onChange={(v) => setCleanup((s) => ({ ...s, roomSize: v }))}
            />
          )}

          <Toggle
            label="Silence Removal"
            checked={cleanup.silenceRemoval}
            onChange={(v) => setCleanup((s) => ({ ...s, silenceRemoval: v }))}
          />
          {cleanup.silenceRemoval && (
            <Slider
              label="Threshold"
              value={cleanup.silenceThresholdDb}
              min={-60}
              max={-10}
              step={1}
              unit=" dB"
              onChange={(v) => setCleanup((s) => ({ ...s, silenceThresholdDb: v }))}
            />
          )}
        </Section>

        {/* B. Pitch & Tempo */}
        <Section
          title="B. Pitch & Tempo"
          open={openSections.pitchTempo}
          onToggle={() => toggleSection('pitchTempo')}
        >
          <Slider
            label="Pitch Shift"
            value={pitchTempo.pitchShift}
            min={-12}
            max={12}
            step={0.5}
            unit=" st"
            onChange={(v) => setPitchTempo((s) => ({ ...s, pitchShift: v }))}
          />
          <Slider
            label="Formant Shift"
            value={pitchTempo.formantShift}
            min={-6}
            max={6}
            step={0.5}
            unit=" st"
            onChange={(v) => setPitchTempo((s) => ({ ...s, formantShift: v }))}
          />
          <Slider
            label="Time Stretch"
            value={pitchTempo.timeStretch}
            min={0.5}
            max={2.0}
            step={0.05}
            unit="x"
            onChange={(v) => setPitchTempo((s) => ({ ...s, timeStretch: v }))}
          />
          <Toggle
            label="Preserve Pitch"
            checked={pitchTempo.preservePitch}
            onChange={(v) => setPitchTempo((s) => ({ ...s, preservePitch: v }))}
          />
        </Section>

        {/* C. Voice & Speech */}
        <Section
          title="C. Voice & Speech"
          open={openSections.voiceSpeech}
          onToggle={() => toggleSection('voiceSpeech')}
        >
          <Toggle
            label="Source Separation"
            checked={voiceSpeech.sourceSeparation}
            onChange={(v) => setVoiceSpeech((s) => ({ ...s, sourceSeparation: v }))}
          />
          {voiceSpeech.sourceSeparation && (
            <SelectField
              label="Target"
              value={voiceSpeech.separationTarget}
              options={[
                { value: 'vocals', label: 'Vocals' },
                { value: 'drums', label: 'Drums' },
                { value: 'bass', label: 'Bass' },
                { value: 'other', label: 'Other' },
              ]}
              onChange={(v) => setVoiceSpeech((s) => ({ ...s, separationTarget: v }))}
            />
          )}

          <Toggle
            label="Voice Conversion"
            checked={voiceSpeech.voiceConversion}
            onChange={(v) => setVoiceSpeech((s) => ({ ...s, voiceConversion: v }))}
          />
          {voiceSpeech.voiceConversion && (
            <SelectField
              label="Target Voice"
              value={voiceSpeech.voiceTarget}
              options={[
                { value: 'male_deep', label: 'Male Deep' },
                { value: 'male_tenor', label: 'Male Tenor' },
                { value: 'female_alto', label: 'Female Alto' },
                { value: 'female_soprano', label: 'Female Soprano' },
                { value: 'child', label: 'Child' },
              ]}
              onChange={(v) => setVoiceSpeech((s) => ({ ...s, voiceTarget: v }))}
            />
          )}

          <Toggle
            label="TTS Mode"
            checked={voiceSpeech.ttsMode}
            onChange={(v) => setVoiceSpeech((s) => ({ ...s, ttsMode: v }))}
          />
          {voiceSpeech.ttsMode && (
            <div className="space-y-3 pl-1">
              <label className="block text-sm text-gray-700">
                Text
                <textarea
                  value={voiceSpeech.ttsText}
                  onChange={(e) =>
                    setVoiceSpeech((s) => ({ ...s, ttsText: e.target.value }))
                  }
                  rows={3}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
                  placeholder="Enter text to synthesize..."
                />
              </label>
              <SelectField
                label="Voice Preset"
                value={voiceSpeech.ttsVoice}
                options={[
                  { value: 'default', label: 'Default' },
                  { value: 'male_1', label: 'Male 1' },
                  { value: 'female_1', label: 'Female 1' },
                  { value: 'narrator', label: 'Narrator' },
                ]}
                onChange={(v) => setVoiceSpeech((s) => ({ ...s, ttsVoice: v }))}
              />
              <Slider
                label="Speed"
                value={voiceSpeech.ttsSpeed}
                min={0.5}
                max={2.0}
                step={0.1}
                unit="x"
                onChange={(v) => setVoiceSpeech((s) => ({ ...s, ttsSpeed: v }))}
              />
            </div>
          )}
        </Section>

        {/* D. Mastering */}
        <Section
          title="D. Mastering"
          open={openSections.mastering}
          onToggle={() => toggleSection('mastering')}
        >
          <Toggle
            label="Loudness Normalization"
            checked={mastering.loudnessNorm}
            onChange={(v) => setMastering((s) => ({ ...s, loudnessNorm: v }))}
          />
          {mastering.loudnessNorm && (
            <Slider
              label="Target LUFS"
              value={mastering.lufs}
              min={-23}
              max={-6}
              step={0.5}
              unit=" LUFS"
              onChange={(v) => setMastering((s) => ({ ...s, lufs: v }))}
            />
          )}

          <SelectField
            label="EQ Preset"
            value={mastering.eqPreset}
            options={[
              { value: 'flat', label: 'Flat (none)' },
              { value: 'bass_boost', label: 'Bass Boost' },
              { value: 'treble_boost', label: 'Treble Boost' },
              { value: 'vocal_presence', label: 'Vocal Presence' },
              { value: 'loudness', label: 'Loudness' },
            ]}
            onChange={(v) => setMastering((s) => ({ ...s, eqPreset: v }))}
          />

          <Toggle
            label="Compression"
            checked={mastering.compression}
            onChange={(v) => setMastering((s) => ({ ...s, compression: v }))}
          />
          {mastering.compression && (
            <SelectField
              label="Ratio"
              value={mastering.compressionRatio}
              options={[
                { value: '2:1', label: '2:1 (Gentle)' },
                { value: '4:1', label: '4:1 (Moderate)' },
                { value: '8:1', label: '8:1 (Heavy)' },
                { value: '12:1', label: '12:1 (Limiting)' },
                { value: '20:1', label: '20:1 (Brick Wall)' },
              ]}
              onChange={(v) => setMastering((s) => ({ ...s, compressionRatio: v }))}
            />
          )}
        </Section>
      </div>

      {/* ----------------------------------------------------------------- */}
      {/* Transform Button */}
      {/* ----------------------------------------------------------------- */}
      <button
        type="button"
        disabled={!file || processing}
        onClick={handleTransform}
        className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-transparent bg-brand-600 px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {processing && (
          <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
        )}
        {processing ? 'Transforming...' : 'Transform'}
      </button>

      {/* Error display */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* ----------------------------------------------------------------- */}
      {/* A/B Comparison */}
      {/* ----------------------------------------------------------------- */}
      {transformedUrl && (
        <div className="space-y-4 rounded-lg border border-gray-200 bg-white p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-900">A/B Comparison</h3>
            <button
              type="button"
              onClick={() => setAbActive((p) => !p)}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                abActive
                  ? 'bg-brand-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {abActive ? `A/B Listen (${abSide})` : 'A/B Listen'}
            </button>
          </div>

          {/* Side-by-side players */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <p className="text-xs font-medium text-blue-600 uppercase tracking-wide">
                A - Original
              </p>
              <audio ref={originalPlayerRef} src={originalUrl ?? undefined} controls className="w-full" />
              <canvas
                ref={originalCanvasRef}
                className="h-20 w-full rounded border border-gray-200 bg-gray-50"
              />
            </div>
            <div className="space-y-2">
              <p className="text-xs font-medium text-emerald-600 uppercase tracking-wide">
                B - Transformed
              </p>
              <audio ref={transformedPlayerRef} src={transformedUrl} controls className="w-full" />
              <canvas
                ref={transformedCanvasRef}
                className="h-20 w-full rounded border border-gray-200 bg-gray-50"
              />
            </div>
          </div>

          {/* Result metadata */}
          {result && (
            <div className="flex flex-wrap gap-3 text-xs text-gray-500">
              {result.processing_time_ms != null && (
                <span>Processing: {result.processing_time_ms.toFixed(0)} ms</span>
              )}
              {result.original_duration_s != null && (
                <span>Original: {result.original_duration_s.toFixed(2)}s</span>
              )}
              {result.result_duration_s != null && (
                <span>Result: {result.result_duration_s.toFixed(2)}s</span>
              )}
              {(result.applied ?? result.operations_applied) && (
                <span>
                  Applied: {(result.applied ?? result.operations_applied ?? []).join(', ')}
                </span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
