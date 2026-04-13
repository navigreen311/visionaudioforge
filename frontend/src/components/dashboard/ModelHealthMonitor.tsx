"use client";

interface ModelHealth {
  name: string;
  accuracy: number;
  baseline: number;
  status: "good" | "warning";
}

const MODELS: ModelHealth[] = [
  { name: "VisionModel v1.2", accuracy: 81, baseline: 89, status: "warning" },
  { name: "AudioModel v2.0", accuracy: 94, baseline: 93, status: "good" },
  { name: "DetectModel v3.1", accuracy: 88, baseline: 90, status: "good" },
];

function StatusIcon({ status }: { status: "good" | "warning" }) {
  if (status === "warning") {
    return (
      <svg
        className="w-5 h-5 text-amber-500"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 9v2m0 4h.01M10.29 3.86l-8.6 14.86A1 1 0 002.56 20h18.88a1 1 0 00.87-1.28l-8.6-14.86a1 1 0 00-1.42 0z"
        />
      </svg>
    );
  }

  return (
    <svg
      className="w-5 h-5 text-green-500"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M5 13l4 4L19 7"
      />
    </svg>
  );
}

export default function ModelHealthMonitor() {
  return (
    <div className="bg-white rounded-lg border shadow-sm p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">
        Model Health Monitor
      </h2>

      <div className="space-y-4">
        {MODELS.map((model) => {
          const delta = model.accuracy - model.baseline;
          const isWarning = model.baseline - model.accuracy > 5;
          const barColor = isWarning ? "bg-amber-400" : "bg-green-500";

          return (
            <div key={model.name} className="space-y-1">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <StatusIcon status={model.status} />
                  <span className="text-sm font-medium text-gray-700">
                    {model.name}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-gray-900">
                    {model.accuracy}%
                  </span>
                  <span
                    className={`text-xs font-medium ${
                      delta >= 0 ? "text-green-600" : "text-red-500"
                    }`}
                  >
                    {delta >= 0 ? "+" : ""}
                    {delta}%
                  </span>
                </div>
              </div>

              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`${barColor} h-2 rounded-full transition-all`}
                  style={{ width: `${model.accuracy}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
