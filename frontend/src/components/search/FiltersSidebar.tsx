'use client';

import { useState, useCallback, useEffect } from 'react';

export interface SearchFilters {
  modalities: ('image' | 'audio' | 'video')[];
  similarityThreshold: number;
  dateFrom: string;
  dateTo: string;
  tags: string[];
  fileSizeMin: number;
  fileSizeMax: number;
}

export const DEFAULT_FILTERS: SearchFilters = {
  modalities: [],
  similarityThreshold: 50,
  dateFrom: '',
  dateTo: '',
  tags: [],
  fileSizeMin: 0,
  fileSizeMax: 500,
};

interface FiltersSidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onApply: (filters: SearchFilters) => void;
  activeFilters: SearchFilters;
}

function getActiveFilterCount(filters: SearchFilters): number {
  let count = 0;
  if (filters.modalities.length > 0) count++;
  if (filters.similarityThreshold !== DEFAULT_FILTERS.similarityThreshold) count++;
  if (filters.dateFrom || filters.dateTo) count++;
  if (filters.tags.length > 0) count++;
  if (
    filters.fileSizeMin !== DEFAULT_FILTERS.fileSizeMin ||
    filters.fileSizeMax !== DEFAULT_FILTERS.fileSizeMax
  )
    count++;
  return count;
}

export { getActiveFilterCount };

export default function FiltersSidebar({
  isOpen,
  onClose,
  onApply,
  activeFilters,
}: FiltersSidebarProps) {
  const [filters, setFilters] = useState<SearchFilters>(activeFilters);
  const [tagInput, setTagInput] = useState('');

  useEffect(() => {
    setFilters(activeFilters);
  }, [activeFilters]);

  // Lock body scroll when open on mobile
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  const handleModalityToggle = useCallback(
    (modality: 'image' | 'audio' | 'video') => {
      setFilters((prev) => ({
        ...prev,
        modalities: prev.modalities.includes(modality)
          ? prev.modalities.filter((m) => m !== modality)
          : [...prev.modalities, modality],
      }));
    },
    []
  );

  const handleAddTag = useCallback(() => {
    const tag = tagInput.trim();
    if (tag && !filters.tags.includes(tag)) {
      setFilters((prev) => ({ ...prev, tags: [...prev.tags, tag] }));
      setTagInput('');
    }
  }, [tagInput, filters.tags]);

  const handleRemoveTag = useCallback((tag: string) => {
    setFilters((prev) => ({
      ...prev,
      tags: prev.tags.filter((t) => t !== tag),
    }));
  }, []);

  const handleClear = useCallback(() => {
    setFilters(DEFAULT_FILTERS);
    setTagInput('');
  }, []);

  const handleApply = useCallback(() => {
    onApply(filters);
    onClose();
  }, [filters, onApply, onClose]);

  const activeCount = getActiveFilterCount(filters);

  const modalityOptions: { value: 'image' | 'audio' | 'video'; label: string; icon: string }[] = [
    { value: 'image', label: 'Images', icon: 'M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z' },
    { value: 'audio', label: 'Audio', icon: 'M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3' },
    { value: 'video', label: 'Video', icon: 'M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z' },
  ];

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-40 md:bg-black/20"
          onClick={onClose}
        />
      )}

      {/* Panel */}
      <div
        className={`fixed top-0 right-0 h-full z-50 bg-white shadow-2xl transition-transform duration-300 ease-in-out w-full sm:w-[380px] ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-semibold text-gray-900">Filters</h2>
              {activeCount > 0 && (
                <span className="inline-flex items-center justify-center w-6 h-6 text-xs font-bold text-white bg-brand-600 rounded-full">
                  {activeCount}
                </span>
              )}
            </div>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition-colors"
              aria-label="Close filters"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Scrollable Body */}
          <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
            {/* Modality */}
            <section>
              <h3 className="text-sm font-medium text-gray-700 mb-3">Modality</h3>
              <div className="space-y-2">
                {modalityOptions.map((opt) => (
                  <label
                    key={opt.value}
                    className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
                  >
                    <input
                      type="checkbox"
                      checked={filters.modalities.includes(opt.value)}
                      onChange={() => handleModalityToggle(opt.value)}
                      className="w-4 h-4 text-brand-600 border-gray-300 rounded focus:ring-brand-500"
                    />
                    <svg className="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={opt.icon} />
                    </svg>
                    <span className="text-sm text-gray-700">{opt.label}</span>
                  </label>
                ))}
              </div>
            </section>

            {/* Similarity Threshold */}
            <section>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-medium text-gray-700">Similarity Threshold</h3>
                <span className="text-sm font-medium text-brand-600">
                  {filters.similarityThreshold}%
                </span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                value={filters.similarityThreshold}
                onChange={(e) =>
                  setFilters((prev) => ({
                    ...prev,
                    similarityThreshold: Number(e.target.value),
                  }))
                }
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-brand-600"
              />
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>0%</span>
                <span>50%</span>
                <span>100%</span>
              </div>
            </section>

            {/* Date Range */}
            <section>
              <h3 className="text-sm font-medium text-gray-700 mb-3">Date Range</h3>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">From</label>
                  <input
                    type="date"
                    value={filters.dateFrom}
                    onChange={(e) =>
                      setFilters((prev) => ({ ...prev, dateFrom: e.target.value }))
                    }
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">To</label>
                  <input
                    type="date"
                    value={filters.dateTo}
                    onChange={(e) =>
                      setFilters((prev) => ({ ...prev, dateTo: e.target.value }))
                    }
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                  />
                </div>
              </div>
            </section>

            {/* Tags */}
            <section>
              <h3 className="text-sm font-medium text-gray-700 mb-3">Tags</h3>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAddTag()}
                  placeholder="Add a tag..."
                  className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                />
                <button
                  onClick={handleAddTag}
                  disabled={!tagInput.trim()}
                  className="px-3 py-2 text-sm font-medium text-brand-600 border border-brand-300 rounded-lg hover:bg-brand-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  Add
                </button>
              </div>
              {filters.tags.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-3">
                  {filters.tags.map((tag) => (
                    <span
                      key={tag}
                      className="inline-flex items-center gap-1 px-2.5 py-1 bg-gray-100 text-gray-700 text-xs font-medium rounded-full"
                    >
                      {tag}
                      <button
                        onClick={() => handleRemoveTag(tag)}
                        className="ml-0.5 text-gray-400 hover:text-gray-600"
                        aria-label={`Remove tag ${tag}`}
                      >
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </section>

            {/* File Size Range */}
            <section>
              <h3 className="text-sm font-medium text-gray-700 mb-3">File Size (MB)</h3>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Min</label>
                  <input
                    type="number"
                    min={0}
                    max={filters.fileSizeMax}
                    value={filters.fileSizeMin}
                    onChange={(e) =>
                      setFilters((prev) => ({
                        ...prev,
                        fileSizeMin: Math.max(0, Number(e.target.value)),
                      }))
                    }
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Max</label>
                  <input
                    type="number"
                    min={filters.fileSizeMin}
                    max={10000}
                    value={filters.fileSizeMax}
                    onChange={(e) =>
                      setFilters((prev) => ({
                        ...prev,
                        fileSizeMax: Math.max(prev.fileSizeMin, Number(e.target.value)),
                      }))
                    }
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                  />
                </div>
              </div>
              {/* Visual range bar */}
              <div className="mt-3 h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-brand-500 rounded-full"
                  style={{
                    marginLeft: `${(filters.fileSizeMin / 500) * 100}%`,
                    width: `${((filters.fileSizeMax - filters.fileSizeMin) / 500) * 100}%`,
                  }}
                />
              </div>
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>{filters.fileSizeMin} MB</span>
                <span>{filters.fileSizeMax} MB</span>
              </div>
            </section>
          </div>

          {/* Footer Actions */}
          <div className="border-t border-gray-200 px-6 py-4 space-y-2">
            <button
              onClick={handleApply}
              className="w-full px-4 py-2.5 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-700 transition-colors"
            >
              Apply Filters
            </button>
            <button
              onClick={handleClear}
              className="w-full px-4 py-2.5 text-gray-600 text-sm font-medium rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors"
            >
              Clear Filters
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
