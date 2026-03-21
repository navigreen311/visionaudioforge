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
    <div className="inline-flex rounded-full overflow-hidden border border-gray-300 bg-gray-50">
      {MODES.map((mode, index) => {
        const config = MODE_CONFIG[mode];
        const isActive = value === mode;

        return (
          <button
            key={mode}
            onClick={() => onChange(mode)}
            title={config.description}
            className={[
              "px-4 py-1.5 text-xs font-medium transition-colors whitespace-nowrap",
              isActive
                ? "bg-brand-600 text-white shadow-sm"
                : "bg-transparent text-gray-600 hover:bg-gray-100",
              index > 0 ? "border-l border-gray-300" : "",
            ].join(" ")}
          >
            <span className="block leading-tight">{config.label}</span>
            <span
              className={[
                "block text-[10px] font-normal leading-tight",
                isActive ? "text-white/80" : "text-gray-400",
              ].join(" ")}
            >
              {config.resolution}
            </span>
          </button>
        );
      })}
    </div>
  );
}
