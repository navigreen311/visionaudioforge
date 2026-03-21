"use client";

export type AnalysisMode = "speed" | "balanced" | "quality";

interface AnalysisModeConfig {
  label: string;
  description: string;
  frameSkip: number;
  resolution: string;
}

const MODE_CONFIG: Record<AnalysisMode, AnalysisModeConfig> = {
  speed: {
    label: "Speed",
    description: "Every 8th frame, 320x240",
    frameSkip: 8,
    resolution: "320x240",
  },
  balanced: {
    label: "Balanced",
    description: "Every 4th frame, 640x480",
    frameSkip: 4,
    resolution: "640x480",
  },
  quality: {
    label: "Quality",
    description: "Every frame, full res",
    frameSkip: 1,
    resolution: "full",
  },
};

const MODES: AnalysisMode[] = ["speed", "balanced", "quality"];

interface AnalysisModeSelectorProps {
  value: AnalysisMode;
  onChange: (mode: AnalysisMode) => void;
}

export default function AnalysisModeSelector({
  value,
  onChange,
}: AnalysisModeSelectorProps) {
  return (
    <div className="inline-flex rounded-lg overflow-hidden border border-gray-300">
      {MODES.map((mode, index) => {
        const config = MODE_CONFIG[mode];
        const isActive = value === mode;

        return (
          <button
            key={mode}
            onClick={() => onChange(mode)}
            title={config.description}
            className={[
              "px-4 py-2 text-sm font-medium transition-colors",
              isActive
                ? "bg-[#185FA5] text-white"
                : "bg-white text-gray-700 hover:bg-gray-100",
              index > 0 ? "border-l border-gray-300" : "",
            ].join(" ")}
          >
            {config.label}
          </button>
        );
      })}
    </div>
  );
}
