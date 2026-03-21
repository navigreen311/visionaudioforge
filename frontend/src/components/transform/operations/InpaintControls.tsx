"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Section, Slider, TextInput } from "./shared";

interface Props {
  onParamsChange: (params: Record<string, unknown>) => void;
}

export default function InpaintControls({ onParamsChange }: Props) {
  const [maskFile, setMaskFile] = useState<File | null>(null);
  const [prompt, setPrompt] = useState("");
  const [inpaintRadius, setInpaintRadius] = useState(15);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const emit = useCallback(() => {
    onParamsChange({
      maskFile: maskFile?.name ?? null,
      prompt,
      inpaintRadius,
    });
  }, [maskFile, prompt, inpaintRadius, onParamsChange]);

  useEffect(() => {
    emit();
  }, [emit]);

  const handleFiles = useCallback((files: FileList | null) => {
    if (files && files.length > 0) {
      setMaskFile(files[0]);
    }
  }, []);

  return (
    <Section>
      {/* Mask upload zone */}
      <div className="space-y-1">
        <span className="block text-sm font-medium text-gray-700">Mask Image</span>
        <div
          className={`relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 transition-colors cursor-pointer ${
            dragOver
              ? "border-brand-500 bg-brand-50"
              : "border-gray-300 bg-gray-50 hover:border-gray-400"
          }`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            handleFiles(e.dataTransfer.files);
          }}
          onClick={() => inputRef.current?.click()}
        >
          <svg
            className="mb-2 h-8 w-8 text-gray-400"
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
          <p className="text-sm text-gray-600">
            {maskFile ? (
              <span className="font-medium text-brand-600">{maskFile.name}</span>
            ) : (
              <>
                <span className="font-medium text-brand-600">Upload mask</span> or drag
                and drop
              </>
            )}
          </p>
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            onChange={(e) => handleFiles(e.target.files)}
            className="hidden"
          />
        </div>
      </div>

      <TextInput
        label="Prompt"
        value={prompt}
        placeholder="Describe what to fill in..."
        onChange={setPrompt}
      />
      <Slider
        label="Inpaint Radius"
        value={inpaintRadius}
        min={0}
        max={50}
        onChange={setInpaintRadius}
      />
    </Section>
  );
}
