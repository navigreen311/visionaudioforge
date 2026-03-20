"use client";

import { useEffect, useRef } from "react";

interface AudioMeterProps {
  stream: MediaStream | null;
}

export default function AudioMeter({ stream }: AudioMeterProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef<number>(0);

  useEffect(() => {
    if (!stream || !canvasRef.current) return;

    const ctx = canvasRef.current.getContext("2d");
    if (!ctx) return;

    const audioCtx = new AudioContext();
    const source = audioCtx.createMediaStreamSource(stream);
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 256;
    source.connect(analyser);

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    const canvas = canvasRef.current;

    function draw() {
      rafRef.current = requestAnimationFrame(draw);
      analyser.getByteFrequencyData(dataArray);

      ctx!.fillStyle = "#f3f4f6";
      ctx!.fillRect(0, 0, canvas.width, canvas.height);

      const barWidth = (canvas.width / bufferLength) * 2.5;
      let x = 0;

      for (let i = 0; i < bufferLength; i++) {
        const barHeight = (dataArray[i] / 255) * canvas.height;
        const hue = (dataArray[i] / 255) * 120; // green → red
        ctx!.fillStyle = `hsl(${120 - hue}, 80%, 50%)`;
        ctx!.fillRect(x, canvas.height - barHeight, barWidth, barHeight);
        x += barWidth + 1;
      }
    }

    draw();

    return () => {
      cancelAnimationFrame(rafRef.current);
      audioCtx.close();
    };
  }, [stream]);

  return (
    <div className="w-full">
      <canvas
        ref={canvasRef}
        width={600}
        height={120}
        className="w-full h-[120px] rounded-lg border border-gray-200"
      />
      <p className="mt-2 text-sm text-gray-500 text-center">
        {stream ? "Monitoring audio levels..." : "No audio stream active"}
      </p>
    </div>
  );
}
