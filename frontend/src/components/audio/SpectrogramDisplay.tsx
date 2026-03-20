"use client";

import React, { useState } from "react";
import Card from "@/components/ui/Card";

interface SpectrogramDisplayProps {
  title: string;
  imageBase64: string;
  /** Optional MFCC coefficient table data */
  coefficients?: number[][];
}

export default function SpectrogramDisplay({
  title,
  imageBase64,
  coefficients,
}: SpectrogramDisplayProps) {
  const [zoomed, setZoomed] = useState(false);

  return (
    <Card title={title}>
      <div className="space-y-3">
        <div
          className={`relative cursor-zoom-in overflow-hidden rounded-lg border border-gray-200 transition-all ${
            zoomed ? "max-h-none" : "max-h-[400px]"
          }`}
          onClick={() => setZoomed(!zoomed)}
        >
          <img
            src={`data:image/png;base64,${imageBase64}`}
            alt={title}
            className={`w-full object-contain transition-transform ${
              zoomed ? "scale-100" : ""
            }`}
          />
          <div className="absolute bottom-2 right-2 rounded bg-black/60 px-2 py-0.5 text-xs text-white">
            {zoomed ? "Click to shrink" : "Click to zoom"}
          </div>
        </div>

        {coefficients && coefficients.length > 0 && (
          <div className="overflow-x-auto">
            <p className="text-sm font-medium text-gray-700 mb-2">
              MFCC Coefficients (first 10 frames)
            </p>
            <table className="min-w-full text-xs border-collapse">
              <thead>
                <tr className="bg-gray-50">
                  <th className="border border-gray-200 px-2 py-1 text-left font-medium text-gray-600">
                    Coeff
                  </th>
                  {coefficients[0]
                    .slice(0, 10)
                    .map((_, i) => (
                      <th
                        key={i}
                        className="border border-gray-200 px-2 py-1 text-right font-medium text-gray-600"
                      >
                        F{i + 1}
                      </th>
                    ))}
                </tr>
              </thead>
              <tbody>
                {coefficients.map((row, ri) => (
                  <tr key={ri} className={ri % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                    <td className="border border-gray-200 px-2 py-1 font-medium text-gray-700">
                      C{ri}
                    </td>
                    {row.slice(0, 10).map((val, ci) => (
                      <td
                        key={ci}
                        className="border border-gray-200 px-2 py-1 text-right text-gray-600 tabular-nums"
                      >
                        {val.toFixed(2)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Card>
  );
}
