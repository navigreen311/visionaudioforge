"use client";

import React, { useEffect, useRef } from "react";

interface BBox {
  label: string;
  confidence: number;
  bbox: [number, number, number, number]; // [x, y, w, h]
}

interface DetectionOverlayProps {
  imageSrc: string;
  boxes: BBox[];
  className?: string;
}

const COLORS = [
  "#ef4444", "#f97316", "#eab308", "#22c55e", "#06b6d4",
  "#3b82f6", "#8b5cf6", "#ec4899", "#14b8a6", "#f43f5e",
];

export default function DetectionOverlay({
  imageSrc,
  boxes,
  className = "",
}: DetectionOverlayProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const img = imgRef.current;
    if (!canvas || !img) return;

    const draw = () => {
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      ctx.drawImage(img, 0, 0);

      boxes.forEach((box, i) => {
        const color = COLORS[i % COLORS.length];
        const [x, y, w, h] = box.bbox;

        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, w, h);

        const label = `${box.label} ${(box.confidence * 100).toFixed(0)}%`;
        ctx.font = "14px sans-serif";
        const textW = ctx.measureText(label).width;
        ctx.fillStyle = color;
        ctx.fillRect(x, y - 20, textW + 8, 20);
        ctx.fillStyle = "#ffffff";
        ctx.fillText(label, x + 4, y - 5);
      });
    };

    if (img.complete) {
      draw();
    } else {
      img.onload = draw;
    }
  }, [imageSrc, boxes]);

  return (
    <div className={`relative ${className}`}>
      <img
        ref={imgRef}
        src={imageSrc}
        alt="Detection source"
        className="hidden"
        crossOrigin="anonymous"
      />
      <canvas
        ref={canvasRef}
        className="max-w-full rounded border border-gray-200"
      />
    </div>
  );
}
