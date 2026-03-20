"use client";

interface LabelSelectorProps {
  labels: string[];
  selected: string;
  onChange: (label: string) => void;
}

export default function LabelSelector({ labels, selected, onChange }: LabelSelectorProps) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-medium text-gray-500 uppercase tracking-wider">
        Label
      </label>
      <select
        value={selected}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
      >
        {labels.map((label) => (
          <option key={label} value={label}>
            {label}
          </option>
        ))}
      </select>
    </div>
  );
}
