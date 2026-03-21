"use client";

// ---------------------------------------------------------------------------
// FeaturedSection — Full-width dark gradient hero showcasing 3 featured plugins
// ---------------------------------------------------------------------------

interface FeaturedPlugin {
  name: string;
  description: string;
  category: string;
  icon: string;
}

const FEATURED_PLUGINS: FeaturedPlugin[] = [
  {
    name: "YOLO Detector",
    description:
      "Real-time object detection powered by YOLOv8. Detect, classify, and track objects across video streams.",
    category: "vision",
    icon: "\uD83D\uDC41",
  },
  {
    name: "Whisper Transcriber",
    description:
      "High-accuracy speech-to-text transcription with OpenAI Whisper. Supports 50+ languages out of the box.",
    category: "audio",
    icon: "\uD83C\uDFA7",
  },
  {
    name: "Slack Notifier",
    description:
      "Instant Slack alerts for pipeline events, anomalies, and custom triggers. Never miss a critical moment.",
    category: "integration",
    icon: "\uD83D\uDD17",
  },
];

interface FeaturedSectionProps {
  onInstall?: (pluginName: string) => void;
}

export default function FeaturedSection({ onInstall }: FeaturedSectionProps) {
  return (
    <div className="w-full rounded-2xl bg-gradient-to-r from-gray-900 via-gray-800 to-gray-900 p-6 h-[180px] flex flex-col justify-between">
      {/* Section header */}
      <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
        Featured Plugins
      </h2>

      {/* Cards row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 flex-1 mt-3">
        {FEATURED_PLUGINS.map((plugin) => (
          <div
            key={plugin.name}
            className="flex items-start gap-3 bg-white/5 rounded-xl px-4 py-3 border border-white/10"
          >
            {/* Icon */}
            <span className="text-2xl shrink-0 mt-0.5">{plugin.icon}</span>

            {/* Text content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-white truncate">
                  {plugin.name}
                </h3>
                <span className="shrink-0 px-1.5 py-0.5 rounded text-[9px] font-bold uppercase bg-amber-500/20 text-amber-400 border border-amber-500/30">
                  ★ Featured
                </span>
              </div>
              <p className="text-[11px] text-gray-400 mt-0.5 line-clamp-2 leading-relaxed">
                {plugin.description}
              </p>
            </div>

            {/* Install button */}
            <button
              onClick={() => onInstall?.(plugin.name)}
              className="shrink-0 self-center px-3 py-1 text-xs font-medium rounded-lg bg-brand-600 text-white hover:bg-brand-700 transition-colors"
            >
              Install
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
