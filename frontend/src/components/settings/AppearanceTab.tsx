'use client';

import { useCallback, useEffect, useState } from 'react';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import api from '@/lib/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ThemeMode = 'light' | 'dark' | 'system';
type SidebarWidth = 'compact' | 'normal' | 'wide';
type DashboardView = 'grid' | 'list';
type CardsPerRow = 2 | 3 | 4 | 0; // 0 = Auto
type DateFormat = 'MM/DD/YYYY' | 'DD/MM/YYYY' | 'YYYY-MM-DD';
type TimeFormat = '12h' | '24h';

interface AppearancePreferences {
  theme: ThemeMode;
  sidebarWidth: SidebarWidth;
  sidebarAutoCollapse: boolean;
  dashboardView: DashboardView;
  cardsPerRow: CardsPerRow;
  language: string;
  timezone: string;
  dateFormat: DateFormat;
  timeFormat: TimeFormat;
}

const STORAGE_KEY = 'vaf_theme';
const PREFS_STORAGE_KEY = 'vaf_appearance_prefs';

const DEFAULT_PREFS: AppearancePreferences = {
  theme: 'system',
  sidebarWidth: 'normal',
  sidebarAutoCollapse: true,
  dashboardView: 'grid',
  cardsPerRow: 0,
  language: 'en',
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  dateFormat: 'MM/DD/YYYY',
  timeFormat: '12h',
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function loadPrefs(): AppearancePreferences {
  try {
    const raw = localStorage.getItem(PREFS_STORAGE_KEY);
    if (raw) {
      return { ...DEFAULT_PREFS, ...JSON.parse(raw) } as AppearancePreferences;
    }
  } catch {
    // ignore corrupt data
  }
  return { ...DEFAULT_PREFS };
}

function savePrefsLocal(prefs: AppearancePreferences): void {
  try {
    localStorage.setItem(PREFS_STORAGE_KEY, JSON.stringify(prefs));
  } catch {
    // storage full or blocked
  }
}

function applyTheme(mode: ThemeMode): void {
  const root = document.documentElement;
  if (mode === 'system') {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    root.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
  } else {
    root.setAttribute('data-theme', mode);
  }
  try {
    localStorage.setItem(STORAGE_KEY, mode);
  } catch {
    // ignore
  }
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const LANGUAGES = [
  { value: 'en', label: 'English' },
  { value: 'es', label: 'Espa\u00f1ol' },
  { value: 'fr', label: 'Fran\u00e7ais' },
  { value: 'de', label: 'Deutsch' },
  { value: 'ja', label: '\u65e5\u672c\u8a9e' },
  { value: 'zh', label: '\u4e2d\u6587' },
  { value: 'pt', label: 'Portugu\u00eas' },
  { value: 'ko', label: '\ud55c\uad6d\uc5b4' },
];

const TIMEZONES = [
  'UTC',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'Europe/London',
  'Europe/Paris',
  'Europe/Berlin',
  'Asia/Tokyo',
  'Asia/Shanghai',
  'Asia/Kolkata',
  'Australia/Sydney',
  'Pacific/Auckland',
];

// ---------------------------------------------------------------------------
// Theme Preview Thumbnails
// ---------------------------------------------------------------------------

function ThemePreview({ mode, selected }: { mode: ThemeMode; selected: boolean }) {
  const bgColor =
    mode === 'light'
      ? 'bg-white'
      : mode === 'dark'
        ? 'bg-gray-800'
        : 'bg-gradient-to-r from-white to-gray-800';

  const sidebarColor =
    mode === 'light'
      ? 'bg-gray-100'
      : mode === 'dark'
        ? 'bg-gray-900'
        : 'bg-gradient-to-b from-gray-100 to-gray-900';

  const lineColor =
    mode === 'light'
      ? 'bg-gray-300'
      : mode === 'dark'
        ? 'bg-gray-600'
        : 'bg-gray-400';

  const labels: Record<ThemeMode, string> = {
    light: 'Light',
    dark: 'Dark',
    system: 'System',
  };

  return (
    <div
      className={`flex flex-col items-center gap-2 cursor-pointer group ${
        selected ? 'opacity-100' : 'opacity-70 hover:opacity-90'
      }`}
    >
      <div
        className={`w-full aspect-[4/3] rounded-lg border-2 overflow-hidden flex ${
          selected
            ? 'border-brand-600 ring-2 ring-brand-200'
            : 'border-gray-200 group-hover:border-gray-300'
        }`}
      >
        {/* Mini sidebar */}
        <div className={`w-1/4 ${sidebarColor} p-1.5 flex flex-col gap-1`}>
          <div className={`h-1.5 w-full rounded ${lineColor}`} />
          <div className={`h-1.5 w-3/4 rounded ${lineColor}`} />
          <div className={`h-1.5 w-2/3 rounded ${lineColor}`} />
        </div>
        {/* Mini content area */}
        <div className={`flex-1 ${bgColor} p-2 flex flex-col gap-1`}>
          <div className={`h-1.5 w-3/4 rounded ${lineColor}`} />
          <div className={`h-1.5 w-1/2 rounded ${lineColor}`} />
          <div className="flex-1 flex gap-1 mt-1">
            <div className={`flex-1 rounded ${lineColor} opacity-40`} />
            <div className={`flex-1 rounded ${lineColor} opacity-40`} />
          </div>
        </div>
      </div>
      <span
        className={`text-sm font-medium ${
          selected ? 'text-brand-600' : 'text-gray-600'
        }`}
      >
        {labels[mode]}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Radio option helper
// ---------------------------------------------------------------------------

function OptionCard<T extends string | number>({
  value,
  selected,
  label,
  description,
  onSelect,
}: {
  value: T;
  selected: boolean;
  label: string;
  description?: string;
  onSelect: (v: T) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(value)}
      className={`flex-1 rounded-lg border-2 px-4 py-3 text-left transition-colors ${
        selected
          ? 'border-brand-600 bg-brand-50 ring-1 ring-brand-200'
          : 'border-gray-200 hover:border-gray-300 bg-white'
      }`}
    >
      <span
        className={`text-sm font-medium ${
          selected ? 'text-brand-700' : 'text-gray-700'
        }`}
      >
        {label}
      </span>
      {description && (
        <span className="block text-xs text-gray-500 mt-0.5">{description}</span>
      )}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Toggle
// ---------------------------------------------------------------------------

function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
}) {
  return (
    <label className="flex items-center justify-between cursor-pointer">
      <span className="text-sm text-gray-700">{label}</span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-5 w-9 shrink-0 rounded-full transition-colors ${
          checked ? 'bg-brand-600' : 'bg-gray-200'
        }`}
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform mt-0.5 ${
            checked ? 'translate-x-[18px]' : 'translate-x-[2px]'
          }`}
        />
      </button>
    </label>
  );
}

// ---------------------------------------------------------------------------
// Select
// ---------------------------------------------------------------------------

function SelectField({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 bg-white"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function AppearanceTab() {
  const [prefs, setPrefs] = useState<AppearancePreferences>(DEFAULT_PREFS);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  // Load from localStorage on mount
  useEffect(() => {
    const loaded = loadPrefs();
    setPrefs(loaded);
    applyTheme(loaded.theme);
  }, []);

  // Listen for system theme changes when mode is "system"
  useEffect(() => {
    if (prefs.theme !== 'system') return;

    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => applyTheme('system');
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, [prefs.theme]);

  const update = useCallback(
    <K extends keyof AppearancePreferences>(
      key: K,
      value: AppearancePreferences[K],
    ) => {
      setPrefs((prev) => {
        const next = { ...prev, [key]: value };
        // Apply theme immediately
        if (key === 'theme') {
          applyTheme(value as ThemeMode);
        }
        return next;
      });
      setSaved(false);
    },
    [],
  );

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      // Persist to localStorage first for instant reload
      savePrefsLocal(prefs);

      // Sync to backend
      await api.put('/api/settings/appearance', prefs);

      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      // Backend may not be available; localStorage is the fallback
      savePrefsLocal(prefs);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  }, [prefs]);

  return (
    <div className="space-y-6">
      {/* ------------------------------------------------------------------ */}
      {/* A. Theme */}
      {/* ------------------------------------------------------------------ */}
      <Card title="Theme">
        <div className="grid grid-cols-3 gap-4 max-w-md">
          {(['light', 'dark', 'system'] as ThemeMode[]).map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => update('theme', mode)}
              className="focus:outline-none"
            >
              <ThemePreview mode={mode} selected={prefs.theme === mode} />
            </button>
          ))}
        </div>
        <p className="text-xs text-gray-500 mt-3">
          Theme is applied immediately. Your preference is saved in your browser.
        </p>
      </Card>

      {/* ------------------------------------------------------------------ */}
      {/* B. Sidebar */}
      {/* ------------------------------------------------------------------ */}
      <Card title="Sidebar">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Sidebar Width
            </label>
            <div className="flex gap-3">
              {(
                [
                  { value: 'compact' as SidebarWidth, label: 'Compact', desc: '200px' },
                  { value: 'normal' as SidebarWidth, label: 'Normal', desc: '256px' },
                  { value: 'wide' as SidebarWidth, label: 'Wide', desc: '320px' },
                ] as const
              ).map((opt) => (
                <OptionCard
                  key={opt.value}
                  value={opt.value}
                  label={opt.label}
                  description={opt.desc}
                  selected={prefs.sidebarWidth === opt.value}
                  onSelect={(v) => update('sidebarWidth', v)}
                />
              ))}
            </div>
          </div>

          <Toggle
            checked={prefs.sidebarAutoCollapse}
            onChange={(v) => update('sidebarAutoCollapse', v)}
            label="Auto-collapse sidebar on mobile"
          />
        </div>
      </Card>

      {/* ------------------------------------------------------------------ */}
      {/* C. Dashboard Layout */}
      {/* ------------------------------------------------------------------ */}
      <Card title="Dashboard Layout">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Default View
            </label>
            <div className="flex gap-3">
              <OptionCard
                value={'grid' as DashboardView}
                label="Grid"
                description="Card-based grid layout"
                selected={prefs.dashboardView === 'grid'}
                onSelect={(v) => update('dashboardView', v)}
              />
              <OptionCard
                value={'list' as DashboardView}
                label="List"
                description="Compact list layout"
                selected={prefs.dashboardView === 'list'}
                onSelect={(v) => update('dashboardView', v)}
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Cards Per Row
            </label>
            <div className="flex gap-3">
              {(
                [
                  { value: 0 as CardsPerRow, label: 'Auto' },
                  { value: 2 as CardsPerRow, label: '2' },
                  { value: 3 as CardsPerRow, label: '3' },
                  { value: 4 as CardsPerRow, label: '4' },
                ] as const
              ).map((opt) => (
                <OptionCard
                  key={opt.value}
                  value={opt.value}
                  label={opt.label}
                  selected={prefs.cardsPerRow === opt.value}
                  onSelect={(v) => update('cardsPerRow', v)}
                />
              ))}
            </div>
          </div>
        </div>
      </Card>

      {/* ------------------------------------------------------------------ */}
      {/* D. Language & Region */}
      {/* ------------------------------------------------------------------ */}
      <Card title="Language &amp; Region">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <SelectField
            label="Language"
            value={prefs.language}
            onChange={(v) => update('language', v)}
            options={LANGUAGES}
          />

          <SelectField
            label="Timezone"
            value={prefs.timezone}
            onChange={(v) => update('timezone', v)}
            options={TIMEZONES.map((tz) => ({ value: tz, label: tz.replace(/_/g, ' ') }))}
          />

          <SelectField
            label="Date Format"
            value={prefs.dateFormat}
            onChange={(v) => update('dateFormat', v as DateFormat)}
            options={[
              { value: 'MM/DD/YYYY', label: 'MM/DD/YYYY' },
              { value: 'DD/MM/YYYY', label: 'DD/MM/YYYY' },
              { value: 'YYYY-MM-DD', label: 'YYYY-MM-DD' },
            ]}
          />

          <SelectField
            label="Time Format"
            value={prefs.timeFormat}
            onChange={(v) => update('timeFormat', v as TimeFormat)}
            options={[
              { value: '12h', label: '12-hour (AM/PM)' },
              { value: '24h', label: '24-hour' },
            ]}
          />
        </div>
      </Card>

      {/* ------------------------------------------------------------------ */}
      {/* Save Button */}
      {/* ------------------------------------------------------------------ */}
      <div className="flex items-center justify-end gap-3">
        {saved && (
          <span className="text-sm text-green-600 font-medium">
            Preferences saved
          </span>
        )}
        <Button
          variant="primary"
          size="md"
          loading={saving}
          onClick={handleSave}
        >
          Save preferences
        </Button>
      </div>
    </div>
  );
}
