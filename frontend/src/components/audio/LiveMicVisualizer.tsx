"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";

export default function LiveMicVisualizer() {
  const [active, setActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState({ rms: 0, peak: 0, duration: 0 });

  const streamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const rafRef = useRef<number>(0);
  const startTimeRef = useRef<number>(0);

  const freqCanvasRef = useRef<HTMLCanvasElement>(null);
  const waveCanvasRef = useRef<HTMLCanvasElement>(null);

  const draw = useCallback(() => {
    const analyser = analyserRef.current;
    const freqCanvas = freqCanvasRef.current;
    const waveCanvas = waveCanvasRef.current;
    if (!analyser || !freqCanvas || !waveCanvas) return;

    const freqCtx = freqCanvas.getContext("2d");
    const waveCtx = waveCanvas.getContext("2d");
    if (!freqCtx || !waveCtx) return;

    const bufferLength = analyser.frequencyBinCount;
    const freqData = new Uint8Array(bufferLength);
    const timeData = new Uint8Array(bufferLength);

    function loop() {
      rafRef.current = requestAnimationFrame(loop);
      analyser!.getByteFrequencyData(freqData);
      analyser!.getByteTimeDomainData(timeData);

      // --- Frequency bars ---
      freqCtx!.fillStyle = "#111827";
      freqCtx!.fillRect(0, 0, freqCanvas!.width, freqCanvas!.height);

      const barWidth = (freqCanvas!.width / bufferLength) * 2.5;
      let x = 0;
      for (let i = 0; i < bufferLength; i++) {
        const barHeight = (freqData[i] / 255) * freqCanvas!.height;
        const hue = (i / bufferLength) * 270;
        freqCtx!.fillStyle = `hsl(${hue}, 85%, 55%)`;
        freqCtx!.fillRect(
          x,
          freqCanvas!.height - barHeight,
          barWidth,
          barHeight,
        );
        x += barWidth + 1;
      }

      // --- Waveform ---
      waveCtx!.fillStyle = "#111827";
      waveCtx!.fillRect(0, 0, waveCanvas!.width, waveCanvas!.height);
      waveCtx!.lineWidth = 2;
      waveCtx!.strokeStyle = "#22d3ee";
      waveCtx!.beginPath();

      const sliceWidth = waveCanvas!.width / bufferLength;
      let wx = 0;
      for (let i = 0; i < bufferLength; i++) {
        const v = timeData[i] / 128.0;
        const y = (v * waveCanvas!.height) / 2;
        if (i === 0) waveCtx!.moveTo(wx, y);
        else waveCtx!.lineTo(wx, y);
        wx += sliceWidth;
      }
      waveCtx!.lineTo(waveCanvas!.width, waveCanvas!.height / 2);
      waveCtx!.stroke();

      // --- Stats ---
      let sumSquares = 0;
      let peak = 0;
      for (let i = 0; i < bufferLength; i++) {
        const normalized = (timeData[i] - 128) / 128;
        sumSquares += normalized * normalized;
        const abs = Math.abs(normalized);
        if (abs > peak) peak = abs;
      }
      const rms = Math.sqrt(sumSquares / bufferLength);
      const elapsed = (performance.now() - startTimeRef.current) / 1000;
      setStats({ rms, peak, duration: elapsed });
    }

    loop();
  }, []);

  const startMic = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const audioCtx = new AudioContext();
      audioCtxRef.current = audioCtx;

      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 2048;
      source.connect(analyser);
      analyserRef.current = analyser;

      startTimeRef.current = performance.now();
      setActive(true);
      draw();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not access microphone. Please allow microphone access.",
      );
    }
  }, [draw]);

  const stopMic = useCallback(() => {
    cancelAnimationFrame(rafRef.current);
    streamRef.current?.getTracks().forEach((t) => t.stop());
    audioCtxRef.current?.close();
    streamRef.current = null;
    audioCtxRef.current = null;
    analyserRef.current = null;
    setActive(false);
  }, []);

  useEffect(() => {
    return () => {
      cancelAnimationFrame(rafRef.current);
      streamRef.current?.getTracks().forEach((t) => t.stop());
      audioCtxRef.current?.close();
    };
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        {!active ? (
          <Button onClick={startMic}>Start Microphone</Button>
        ) : (
          <Button variant="danger" onClick={stopMic}>
            Stop
          </Button>
        )}
        {active && (
          <span className="flex items-center gap-2 text-sm text-green-600">
            <span className="relative flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-green-500" />
            </span>
            Recording
          </span>
        )}
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card title="Frequency Spectrum">
          <canvas
            ref={freqCanvasRef}
            width={600}
            height={200}
            className="w-full h-[200px] rounded-lg bg-gray-900"
          />
        </Card>

        <Card title="Waveform">
          <canvas
            ref={waveCanvasRef}
            width={600}
            height={200}
            className="w-full h-[200px] rounded-lg bg-gray-900"
          />
        </Card>
      </div>

      <Card title="Audio Stats">
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center">
            <p className="text-xs text-gray-500 uppercase tracking-wide">
              Volume (RMS)
            </p>
            <p className="text-2xl font-bold text-gray-900 tabular-nums">
              {(stats.rms * 100).toFixed(1)}
              <span className="text-sm font-normal text-gray-500">%</span>
            </p>
            <div className="mt-1 h-2 w-full rounded-full bg-gray-200 overflow-hidden">
              <div
                className="h-full rounded-full bg-brand-500 transition-all duration-75"
                style={{ width: `${Math.min(stats.rms * 100, 100)}%` }}
              />
            </div>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-500 uppercase tracking-wide">
              Peak Level
            </p>
            <p className="text-2xl font-bold text-gray-900 tabular-nums">
              {(stats.peak * 100).toFixed(1)}
              <span className="text-sm font-normal text-gray-500">%</span>
            </p>
            <div className="mt-1 h-2 w-full rounded-full bg-gray-200 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-75 ${
                  stats.peak > 0.9 ? "bg-red-500" : stats.peak > 0.6 ? "bg-yellow-500" : "bg-green-500"
                }`}
                style={{ width: `${Math.min(stats.peak * 100, 100)}%` }}
              />
            </div>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-500 uppercase tracking-wide">
              Duration
            </p>
            <p className="text-2xl font-bold text-gray-900 tabular-nums">
              {stats.duration.toFixed(1)}
              <span className="text-sm font-normal text-gray-500">s</span>
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}
