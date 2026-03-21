"use client";

import React, { useState, useCallback } from "react";
import Button from "@/components/ui/Button";
import ClassDistributionChart from "./ClassDistributionChart";

interface DatasetDetail {
  id: string;
  name: string;
  modality: string;
  sample_count: number;
  version: number;
  split: { train: number; val: number; test: number };
  class_counts: Record<string, number>;
}

interface DatasetDetailPanelProps {
  dataset: DatasetDetail;
  isOpen: boolean;
  onClose: () => void;
  onResplit: (id: string, train: number, val: number, test: number) => void;
}

export default function DatasetDetailPanel({
  dataset,
  isOpen,
  onClose,
  onResplit,
}: DatasetDetailPanelProps) {
  const [trainPct, setTrainPct] = useState(70);
  const [valPct, setValPct] = useState(15);
  const [testPct, setTestPct] = useState(15);
  const [showResplit, setShowResplit] = useState(false);

  const handleTrainChange = useCallback((v: number) => {
    const clamped = Math.min(v, 100);
    setTrainPct(clamped);
    const remaining = 100 - clamped;
    setValPct(Math.round(remaining / 2));
    setTestPct(remaining - Math.round(remaining / 2));
  }, []);

  const handleValChange = useCallback(
    (v: number) => {
      const maxVal = 100 - trainPct;
      const clamped = Math.min(v, maxVal);
      setValPct(clamped);
      setTestPct(maxVal - clamped);
    },
    [trainPct]
  );

  // Check imbalance
  const counts = Object.values(dataset.class_counts);
  const minCount = counts.length > 0 ? Math.min(...counts) : 0;
  const maxCount = counts.length > 0 ? Math.max(...counts) : 0;
  const isImbalanced = minCount > 0 && maxCount / minCount > 5;

  const total = dataset.split.train + dataset.split.val + dataset.split.test;
  const trainW = total > 0 ? (dataset.split.train / total) * 100 : 0;
  const valW = total > 0 ? (dataset.split.val / total) * 100 : 0;
  const testW = total > 0 ? (dataset.split.test / total) * 100 : 0;

  // Placeholder thumbnails
  const placeholderThumbs = Array.from({ length: 8 }, (_, i) => i);

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/30 transition-opacity"
          onClick={onClose}
        />
      )}

      {/* Slide-over */}
      <div
        className={`fixed inset-y-0 right-0 z-50 w-full max-w-md transform bg-white shadow-xl transition-transform duration-300 ease-in-out ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              {dataset.name}
            </h2>
            <p className="text-sm text-gray-500">
              v{dataset.version} &middot; {dataset.sample_count.toLocaleString()} samples
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
          >
            <svg
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto px-6 py-5 space-y-6" style={{ maxHeight: "calc(100vh - 72px)" }}>
          {/* Class Distribution */}
          <section>
            <h3 className="text-sm font-medium text-gray-900 mb-3">
              Class Distribution
            </h3>
            {Object.keys(dataset.class_counts).length > 0 ? (
              <ClassDistributionChart classCounts={dataset.class_counts} />
            ) : (
              <p className="text-sm text-gray-500">No class data available.</p>
            )}
            {isImbalanced && (
              <div className="mt-3 flex items-start gap-2 rounded-lg bg-amber-50 border border-amber-200 p-3">
                <svg
                  className="h-5 w-5 text-amber-500 shrink-0 mt-0.5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"
                  />
                </svg>
                <div>
                  <p className="text-sm font-medium text-amber-800">
                    Class Imbalance Detected
                  </p>
                  <p className="text-xs text-amber-700 mt-0.5">
                    Largest class is {">"}5x the smallest ({maxCount.toLocaleString()} vs{" "}
                    {minCount.toLocaleString()}). Consider oversampling minority classes or
                    using weighted loss.
                  </p>
                </div>
              </div>
            )}
          </section>

          {/* Split Breakdown */}
          <section>
            <h3 className="text-sm font-medium text-gray-900 mb-3">
              Split Breakdown
            </h3>
            <div className="flex h-4 w-full overflow-hidden rounded-full bg-gray-100">
              <div
                className="bg-blue-500 transition-all"
                style={{ width: `${trainW}%` }}
                title={`Train: ${dataset.split.train}`}
              />
              <div
                className="bg-amber-400 transition-all"
                style={{ width: `${valW}%` }}
                title={`Val: ${dataset.split.val}`}
              />
              <div
                className="bg-green-500 transition-all"
                style={{ width: `${testW}%` }}
                title={`Test: ${dataset.split.test}`}
              />
            </div>
            <div className="mt-2 flex gap-4 text-xs text-gray-600">
              <span className="flex items-center gap-1">
                <span className="inline-block h-2.5 w-2.5 rounded-full bg-blue-500" />
                Train: {dataset.split.train.toLocaleString()}
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block h-2.5 w-2.5 rounded-full bg-amber-400" />
                Val: {dataset.split.val.toLocaleString()}
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block h-2.5 w-2.5 rounded-full bg-green-500" />
                Test: {dataset.split.test.toLocaleString()}
              </span>
            </div>
          </section>

          {/* Re-split */}
          <section>
            {!showResplit ? (
              <Button variant="secondary" size="sm" onClick={() => setShowResplit(true)}>
                Re-split Dataset
              </Button>
            ) : (
              <div className="space-y-3 rounded-lg border border-gray-200 p-4">
                <h4 className="text-sm font-medium text-gray-900">
                  Adjust Split Ratios
                </h4>
                <div>
                  <label className="flex items-center justify-between text-xs text-gray-600">
                    <span>Train: {trainPct}%</span>
                  </label>
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={trainPct}
                    onChange={(e) => handleTrainChange(Number(e.target.value))}
                    className="w-full accent-blue-500"
                  />
                </div>
                <div>
                  <label className="flex items-center justify-between text-xs text-gray-600">
                    <span>Val: {valPct}%</span>
                  </label>
                  <input
                    type="range"
                    min={0}
                    max={100 - trainPct}
                    value={valPct}
                    onChange={(e) => handleValChange(Number(e.target.value))}
                    className="w-full accent-amber-400"
                  />
                </div>
                <div className="text-xs text-gray-600">
                  Test: {testPct}%
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    onClick={() => {
                      onResplit(dataset.id, trainPct / 100, valPct / 100, testPct / 100);
                      setShowResplit(false);
                    }}
                  >
                    Apply
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowResplit(false)}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            )}
          </section>

          {/* Sample Preview Grid */}
          <section>
            <h3 className="text-sm font-medium text-gray-900 mb-3">
              Sample Preview
            </h3>
            <div className="grid grid-cols-4 gap-2">
              {placeholderThumbs.map((i) => (
                <div
                  key={i}
                  className="flex aspect-square items-center justify-center rounded-lg border border-gray-200 bg-gray-50"
                >
                  <svg
                    className="h-8 w-8 text-gray-300"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                    />
                  </svg>
                </div>
              ))}
            </div>
            <p className="mt-2 text-xs text-gray-400 text-center">
              Thumbnails load when backend storage is connected.
            </p>
          </section>
        </div>
      </div>
    </>
  );
}
