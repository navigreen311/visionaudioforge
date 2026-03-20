"use client";

import { useState, useCallback, useRef } from "react";

export type SearchModality = "text" | "image" | "audio";

interface SearchBarProps {
  onSearch: (query: string, modality: SearchModality, file?: File) => void;
  isLoading?: boolean;
}

export default function SearchBar({ onSearch, isLoading = false }: SearchBarProps) {
  const [modality, setModality] = useState<SearchModality>("text");
  const [textQuery, setTextQuery] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = () => {
    if (modality === "text" && textQuery.trim()) {
      onSearch(textQuery.trim(), modality);
    } else if ((modality === "image" || modality === "audio") && selectedFile) {
      onSearch("", modality, selectedFile);
    }
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) setSelectedFile(file);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false);
  }, []);

  const modalityButtons: { value: SearchModality; label: string }[] = [
    { value: "text", label: "Text" },
    { value: "image", label: "Image" },
    { value: "audio", label: "Audio" },
  ];

  return (
    <div className="w-full space-y-4">
      {/* Modality Toggle */}
      <div className="flex gap-2">
        {modalityButtons.map((btn) => (
          <button
            key={btn.value}
            onClick={() => {
              setModality(btn.value);
              setSelectedFile(null);
            }}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              modality === btn.value
                ? "bg-brand-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {btn.label}
          </button>
        ))}
      </div>

      {/* Text Input */}
      {modality === "text" && (
        <div className="flex gap-2">
          <input
            type="text"
            value={textQuery}
            onChange={(e) => setTextQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            placeholder="Describe what you're looking for..."
            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
          />
          <button
            onClick={handleSubmit}
            disabled={!textQuery.trim() || isLoading}
            className="px-6 py-3 bg-brand-600 text-white rounded-lg font-medium hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? "Searching..." : "Search"}
          </button>
        </div>
      )}

      {/* Image / Audio Upload */}
      {(modality === "image" || modality === "audio") && (
        <div className="space-y-3">
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
              isDragOver
                ? "border-brand-500 bg-brand-50"
                : selectedFile
                ? "border-green-400 bg-green-50"
                : "border-gray-300 hover:border-gray-400"
            }`}
          >
            {selectedFile ? (
              <p className="text-green-700 font-medium">{selectedFile.name}</p>
            ) : (
              <div>
                <p className="text-gray-500">
                  Drag and drop {modality === "image" ? "an image" : "an audio file"} here
                </p>
                <p className="text-gray-400 text-sm mt-1">or click to browse</p>
              </div>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept={modality === "image" ? "image/*" : "audio/*"}
              onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
              className="hidden"
            />
          </div>
          <button
            onClick={handleSubmit}
            disabled={!selectedFile || isLoading}
            className="w-full px-6 py-3 bg-brand-600 text-white rounded-lg font-medium hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? "Searching..." : "Search"}
          </button>
        </div>
      )}
    </div>
  );
}
