"use client";

const SKILL_PACKS = [
  { id: "general", label: "General", icon: "G" },
  { id: "investigator", label: "Investigator", icon: "I" },
  { id: "qa_analyst", label: "QA Analyst", icon: "Q" },
  { id: "compliance", label: "Compliance", icon: "C" },
  { id: "media_editor", label: "Media Editor", icon: "M" },
  { id: "operations", label: "Operations", icon: "O" },
  { id: "executive", label: "Executive", icon: "E" },
] as const;

interface SkillPackSwitcherProps {
  current: string;
  onChange: (pack: string) => void;
}

export default function SkillPackSwitcher({
  current,
  onChange,
}: SkillPackSwitcherProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <h3 className="font-semibold text-gray-900 text-sm mb-3">Skill Pack</h3>
      <div className="flex flex-wrap gap-2">
        {SKILL_PACKS.map((pack) => (
          <button
            key={pack.id}
            onClick={() => onChange(pack.id)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              current === pack.id
                ? "bg-brand-600 text-white"
                : "bg-gray-50 text-gray-600 hover:bg-gray-100"
            }`}
          >
            {pack.label}
          </button>
        ))}
      </div>
    </div>
  );
}
