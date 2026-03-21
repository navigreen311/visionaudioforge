'use client';

import { useState } from 'react';
import PluginReviews from './PluginReviews';
import PluginChangelog from './PluginChangelog';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Review {
  id: string;
  user: string;
  avatar: string;
  rating: number;
  date: string;
  comment: string;
  helpful: number;
}

interface RatingBreakdown {
  stars: number;
  count: number;
  percentage: number;
}

interface ChangelogEntry {
  version: string;
  date: string;
  changes: string[];
  type: 'major' | 'minor' | 'patch';
}

export interface PluginDetail {
  name: string;
  category: string;
  description: string;
  version: string;
  author: string;
  install_count: number;
  avg_rating: number;
  icon: string;
  // Extended detail fields
  full_description: string;
  features: string[];
  requirements: string[];
  compatibility: string[];
  license: string;
  screenshots: string[];
  reviews: Review[];
  rating_breakdown: RatingBreakdown[];
  total_reviews: number;
  changelog: ChangelogEntry[];
}

interface PluginDetailPanelProps {
  plugin: PluginDetail | null;
  isOpen: boolean;
  onClose: () => void;
  onInstall: (plugin: PluginDetail) => void;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const CATEGORY_COLORS: Record<string, string> = {
  vision: 'bg-purple-100 text-purple-700',
  audio: 'bg-blue-100 text-blue-700',
  transform: 'bg-green-100 text-green-700',
  pipeline_node: 'bg-yellow-100 text-yellow-700',
  integration: 'bg-pink-100 text-pink-700',
  analytics: 'bg-indigo-100 text-indigo-700',
  model: 'bg-red-100 text-red-700',
};

const CATEGORY_ICONS: Record<string, string> = {
  vision: '\u{1F441}',
  audio: '\u{1F3A7}',
  transform: '\u{1F504}',
  pipeline_node: '\u2699\uFE0F',
  integration: '\u{1F517}',
  analytics: '\u{1F4CA}',
  model: '\u{1F9E0}',
};

const LICENSE_COLORS: Record<string, string> = {
  MIT: 'bg-green-100 text-green-700',
  'Apache-2.0': 'bg-blue-100 text-blue-700',
  'GPL-3.0': 'bg-orange-100 text-orange-700',
  Proprietary: 'bg-red-100 text-red-700',
};

type DetailTab = 'about' | 'screenshots' | 'reviews' | 'changelog';

// ---------------------------------------------------------------------------
// Stars helper
// ---------------------------------------------------------------------------

function Stars({ rating }: { rating: number }) {
  return (
    <span className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((n) => (
        <svg
          key={n}
          className={`h-4 w-4 ${n <= Math.round(rating) ? 'text-yellow-400' : 'text-gray-300'}`}
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      ))}
      <span className="ml-1 text-xs text-gray-500">
        {rating > 0 ? rating.toFixed(1) : 'N/A'}
      </span>
    </span>
  );
}

// ---------------------------------------------------------------------------
// Screenshot lightbox
// ---------------------------------------------------------------------------

function ScreenshotLightbox({
  src,
  alt,
  onClose,
}: {
  src: string;
  alt: string;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-[60] bg-black/70 flex items-center justify-center p-8"
      onClick={onClose}
    >
      <div className="relative max-w-4xl w-full" onClick={(e) => e.stopPropagation()}>
        <button
          onClick={onClose}
          className="absolute -top-10 right-0 text-white hover:text-gray-300 transition-colors"
        >
          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        <div className="bg-gray-800 rounded-xl overflow-hidden">
          <div className="aspect-video flex items-center justify-center text-gray-400 text-sm">
            <div className="text-center space-y-2">
              <svg className="h-16 w-16 mx-auto text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              <p>{alt}</p>
              <p className="text-xs text-gray-600">{src}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function PluginDetailPanel({
  plugin,
  isOpen,
  onClose,
  onInstall,
}: PluginDetailPanelProps) {
  const [activeTab, setActiveTab] = useState<DetailTab>('about');
  const [expandedScreenshot, setExpandedScreenshot] = useState<string | null>(null);

  if (!plugin) return null;

  const tabs: { key: DetailTab; label: string }[] = [
    { key: 'about', label: 'About' },
    { key: 'screenshots', label: 'Screenshots' },
    { key: 'reviews', label: 'Reviews' },
    { key: 'changelog', label: 'Changelog' },
  ];

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 z-40 bg-black/30 transition-opacity duration-300 ${
          isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
        }`}
        onClick={onClose}
      />

      {/* Slide-over panel */}
      <div
        className={`fixed inset-y-0 right-0 z-50 w-[60%] max-w-4xl bg-white shadow-2xl transform transition-transform duration-300 ease-in-out flex flex-col ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {/* ============================================================== */}
        {/* Header                                                         */}
        {/* ============================================================== */}
        <div className="border-b border-gray-200 px-6 py-5 shrink-0">
          <div className="flex items-start gap-4">
            {/* Close button */}
            <button
              onClick={onClose}
              className="mt-1 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>

            {/* Icon */}
            <span className="text-4xl shrink-0">
              {CATEGORY_ICONS[plugin.category] || '\u{1F50C}'}
            </span>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 flex-wrap">
                <h2 className="text-xl font-bold text-gray-900">{plugin.name}</h2>
                <span className="text-xs text-gray-400">v{plugin.version}</span>
                <span
                  className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${
                    CATEGORY_COLORS[plugin.category] || 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {plugin.category.replace('_', ' ')}
                </span>
              </div>

              <div className="flex items-center gap-4 mt-1.5 flex-wrap">
                <Stars rating={plugin.avg_rating} />
                <span className="text-xs text-gray-500">
                  {plugin.install_count.toLocaleString()} installs
                </span>
                <span className="text-xs text-gray-500">
                  by <span className="font-medium text-gray-700">{plugin.author}</span>
                </span>
              </div>
            </div>

            {/* Install button */}
            <button
              onClick={() => onInstall(plugin)}
              className="shrink-0 px-5 py-2 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-700 transition-colors"
            >
              Install
            </button>
          </div>
        </div>

        {/* ============================================================== */}
        {/* Sub-tabs                                                       */}
        {/* ============================================================== */}
        <div className="border-b border-gray-200 px-6 shrink-0">
          <div className="flex gap-1">
            {tabs.map((t) => (
              <button
                key={t.key}
                onClick={() => setActiveTab(t.key)}
                className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === t.key
                    ? 'border-brand-600 text-brand-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* ============================================================== */}
        {/* Tab content (scrollable)                                       */}
        {/* ============================================================== */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {/* ------ About ------ */}
          {activeTab === 'about' && (
            <div className="space-y-6">
              {/* Full description */}
              <div>
                <h3 className="text-sm font-semibold text-gray-900 mb-2">Description</h3>
                <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">
                  {plugin.full_description}
                </p>
              </div>

              {/* Features */}
              <div>
                <h3 className="text-sm font-semibold text-gray-900 mb-2">Features</h3>
                <ul className="space-y-1.5">
                  {plugin.features.map((f, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                      <svg className="h-4 w-4 text-green-500 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                      {f}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Requirements */}
              <div>
                <h3 className="text-sm font-semibold text-gray-900 mb-2">Requirements</h3>
                <ul className="space-y-1">
                  {plugin.requirements.map((r, i) => (
                    <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                      <span className="text-gray-400 mt-0.5 shrink-0">&#8226;</span>
                      {r}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Compatibility */}
              <div>
                <h3 className="text-sm font-semibold text-gray-900 mb-2">Compatibility</h3>
                <div className="flex flex-wrap gap-2">
                  {plugin.compatibility.map((c, i) => (
                    <span
                      key={i}
                      className="px-2.5 py-1 bg-gray-100 text-gray-700 text-xs rounded-lg font-medium"
                    >
                      {c}
                    </span>
                  ))}
                </div>
              </div>

              {/* License */}
              <div>
                <h3 className="text-sm font-semibold text-gray-900 mb-2">License</h3>
                <span
                  className={`px-3 py-1 rounded-full text-xs font-semibold ${
                    LICENSE_COLORS[plugin.license] || 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {plugin.license}
                </span>
              </div>
            </div>
          )}

          {/* ------ Screenshots ------ */}
          {activeTab === 'screenshots' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {plugin.screenshots.map((src, i) => (
                <button
                  key={i}
                  onClick={() => setExpandedScreenshot(src)}
                  className="group border border-gray-200 rounded-xl overflow-hidden bg-gray-50 hover:border-brand-300 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500"
                >
                  <div className="aspect-video flex items-center justify-center text-gray-400">
                    <div className="text-center space-y-1 group-hover:text-brand-500 transition-colors">
                      <svg className="h-10 w-10 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                      <p className="text-xs">Screenshot {i + 1}</p>
                      <p className="text-[10px] text-gray-400">Click to expand</p>
                    </div>
                  </div>
                </button>
              ))}
              {plugin.screenshots.length === 0 && (
                <p className="col-span-full text-center text-sm text-gray-400 py-6">
                  No screenshots available.
                </p>
              )}
            </div>
          )}

          {/* ------ Reviews ------ */}
          {activeTab === 'reviews' && (
            <PluginReviews
              pluginName={plugin.name}
              avgRating={plugin.avg_rating}
              totalReviews={plugin.total_reviews}
              reviews={plugin.reviews}
              ratingBreakdown={plugin.rating_breakdown}
            />
          )}

          {/* ------ Changelog ------ */}
          {activeTab === 'changelog' && (
            <PluginChangelog entries={plugin.changelog} />
          )}
        </div>
      </div>

      {/* Screenshot lightbox */}
      {expandedScreenshot && (
        <ScreenshotLightbox
          src={expandedScreenshot}
          alt={`${plugin.name} screenshot`}
          onClose={() => setExpandedScreenshot(null)}
        />
      )}
    </>
  );
}
