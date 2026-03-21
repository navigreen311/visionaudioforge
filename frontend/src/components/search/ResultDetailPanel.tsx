'use client';

import { useState, useEffect, useCallback } from 'react';
import type { SearchResult } from './ResultCard';

interface ResultDetailPanelProps {
  result: SearchResult | null;
  isOpen: boolean;
  onClose: () => void;
}

const typeColors: Record<string, string> = {
  image: 'bg-blue-100 text-blue-700',
  audio: 'bg-purple-100 text-purple-700',
  video: 'bg-red-100 text-red-700',
  unknown: 'bg-gray-100 text-gray-600',
};

export default function ResultDetailPanel({
  result,
  isOpen,
  onClose,
}: ResultDetailPanelProps) {
  const [whyExpanded, setWhyExpanded] = useState(false);
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState('');

  // Reset state when result changes
  useEffect(() => {
    setWhyExpanded(false);
    setTags([]); // Would load from API for real result
    setTagInput('');
  }, [result?.asset_id]);

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

  const handleAddTag = useCallback(() => {
    const tag = tagInput.trim();
    if (tag && !tags.includes(tag)) {
      setTags((prev) => [...prev, tag]);
      setTagInput('');
    }
  }, [tagInput, tags]);

  const handleRemoveTag = useCallback((tag: string) => {
    setTags((prev) => prev.filter((t) => t !== tag));
  }, []);

  if (!result) return null;

  const scorePercent = Math.round(result.score * 100);
  const badgeClass = typeColors[result.asset_type] || typeColors.unknown;

  // Mock similar assets (would come from API)
  const similarAssets: SearchResult[] = Array.from({ length: 4 }, (_, i) => ({
    asset_id: `similar-${i}`,
    score: Math.max(0.5, result.score - (i + 1) * 0.08),
    rank: i + 1,
    asset_type: result.asset_type,
    filename: `similar_${i + 1}.${result.asset_type === 'audio' ? 'wav' : result.asset_type === 'video' ? 'mp4' : 'jpg'}`,
    path: '',
  }));

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
        className={`fixed top-0 right-0 h-full z-50 bg-white shadow-2xl transition-transform duration-300 ease-in-out w-full sm:w-[400px] ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900 truncate pr-4">
              {result.filename || `Asset ${result.asset_id.slice(0, 8)}`}
            </h2>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition-colors flex-shrink-0"
              aria-label="Close detail panel"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Scrollable Body */}
          <div className="flex-1 overflow-y-auto">
            {/* Preview */}
            <div className="aspect-video bg-gray-100 flex items-center justify-center relative">
              {result.asset_type === 'image' ? (
                <div className="w-full h-full bg-gray-200 flex items-center justify-center">
                  <svg className="w-16 h-16 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
              ) : result.asset_type === 'audio' ? (
                <div className="w-full h-full flex flex-col items-center justify-center gap-3 px-6">
                  <svg className="w-12 h-12 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                  </svg>
                  {/* Audio player placeholder */}
                  <div className="w-full bg-gray-200 rounded-full h-1.5">
                    <div className="bg-purple-500 h-1.5 rounded-full w-1/3" />
                  </div>
                  <div className="flex items-center gap-3">
                    <button className="p-2 rounded-full bg-purple-100 text-purple-600 hover:bg-purple-200 transition-colors">
                      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M8 5v14l11-7z" />
                      </svg>
                    </button>
                    <span className="text-xs text-gray-500">0:00 / 0:00</span>
                  </div>
                </div>
              ) : result.asset_type === 'video' ? (
                <div className="w-full h-full flex flex-col items-center justify-center gap-3">
                  <svg className="w-12 h-12 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  <button className="p-3 rounded-full bg-red-100 text-red-600 hover:bg-red-200 transition-colors">
                    <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M8 5v14l11-7z" />
                    </svg>
                  </button>
                </div>
              ) : (
                <svg className="w-16 h-16 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
              )}
            </div>

            <div className="px-6 py-5 space-y-5">
              {/* Metadata */}
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${badgeClass}`}>
                    {result.asset_type}
                  </span>
                  <span className="text-xs text-gray-400">Rank #{result.rank}</span>
                </div>

                <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
                  <div>
                    <dt className="text-gray-500 text-xs">Filename</dt>
                    <dd className="text-gray-900 mt-0.5 truncate font-medium">
                      {result.filename || 'N/A'}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-gray-500 text-xs">File Size</dt>
                    <dd className="text-gray-900 mt-0.5">--</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500 text-xs">Created</dt>
                    <dd className="text-gray-900 mt-0.5">--</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500 text-xs">Similarity Score</dt>
                    <dd className="mt-0.5">
                      <span
                        className={`font-semibold ${
                          scorePercent >= 80
                            ? 'text-green-600'
                            : scorePercent >= 50
                            ? 'text-yellow-600'
                            : 'text-red-500'
                        }`}
                      >
                        {scorePercent}%
                      </span>
                    </dd>
                  </div>
                  {result.path && (
                    <div className="col-span-2">
                      <dt className="text-gray-500 text-xs">Path</dt>
                      <dd className="font-mono text-gray-900 text-xs mt-0.5 break-all">
                        {result.path}
                      </dd>
                    </div>
                  )}
                </dl>
              </div>

              {/* Why This Result? */}
              <section className="border border-gray-200 rounded-lg overflow-hidden">
                <button
                  onClick={() => setWhyExpanded(!whyExpanded)}
                  className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                >
                  <span>Why this result?</span>
                  <svg
                    className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${
                      whyExpanded ? 'rotate-180' : ''
                    }`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                {whyExpanded && (
                  <div className="px-4 pb-4 text-sm text-gray-600 space-y-2 border-t border-gray-100">
                    <p className="pt-3">
                      This asset matched with a <strong>{scorePercent}%</strong> similarity score
                      based on cross-modal vector embedding comparison.
                    </p>
                    <ul className="list-disc list-inside space-y-1 text-xs text-gray-500">
                      <li>Embedding distance: {(1 - result.score).toFixed(4)}</li>
                      <li>Index: FAISS HNSW (approximate nearest neighbor)</li>
                      <li>Modality: {result.asset_type} embedding space</li>
                    </ul>
                  </div>
                )}
              </section>

              {/* Tags */}
              <section>
                <h3 className="text-sm font-medium text-gray-700 mb-2">Tags</h3>
                <div className="flex gap-2 mb-2">
                  <input
                    type="text"
                    value={tagInput}
                    onChange={(e) => setTagInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleAddTag()}
                    placeholder="Add tag..."
                    className="flex-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                  />
                  <button
                    onClick={handleAddTag}
                    disabled={!tagInput.trim()}
                    className="px-3 py-1.5 text-xs font-medium text-brand-600 border border-brand-300 rounded-lg hover:bg-brand-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    Add
                  </button>
                </div>
                {tags.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {tags.map((tag) => (
                      <span
                        key={tag}
                        className="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-100 text-gray-700 text-xs font-medium rounded-full"
                      >
                        {tag}
                        <button
                          onClick={() => handleRemoveTag(tag)}
                          className="text-gray-400 hover:text-gray-600"
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
                {tags.length === 0 && (
                  <p className="text-xs text-gray-400">No tags yet</p>
                )}
              </section>

              {/* Actions */}
              <section className="space-y-2">
                <h3 className="text-sm font-medium text-gray-700 mb-2">Actions</h3>
                <div className="grid grid-cols-2 gap-2">
                  <button className="flex items-center justify-center gap-2 px-3 py-2.5 text-sm font-medium text-gray-700 bg-gray-50 border border-gray-200 rounded-lg hover:bg-gray-100 transition-colors">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                    <span className="truncate">
                      {result.asset_type === 'audio' ? 'Open in Audio' : result.asset_type === 'video' ? 'Open in Transform' : 'Open in Vision'}
                    </span>
                  </button>
                  <button className="flex items-center justify-center gap-2 px-3 py-2.5 text-sm font-medium text-gray-700 bg-gray-50 border border-gray-200 rounded-lg hover:bg-gray-100 transition-colors">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    Download
                  </button>
                  <button className="flex items-center justify-center gap-2 px-3 py-2.5 text-sm font-medium text-gray-700 bg-gray-50 border border-gray-200 rounded-lg hover:bg-gray-100 transition-colors">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                    </svg>
                    Save to Case
                  </button>
                  <button className="flex items-center justify-center gap-2 px-3 py-2.5 text-sm font-medium text-gray-700 bg-gray-50 border border-gray-200 rounded-lg hover:bg-gray-100 transition-colors">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                    </svg>
                    Copy Link
                  </button>
                </div>
              </section>

              {/* Similar Assets */}
              <section>
                <h3 className="text-sm font-medium text-gray-700 mb-3">Similar Assets</h3>
                <div className="grid grid-cols-4 gap-2">
                  {similarAssets.map((asset) => (
                    <div
                      key={asset.asset_id}
                      className="aspect-square bg-gray-100 rounded-lg flex items-center justify-center relative cursor-pointer hover:ring-2 hover:ring-brand-400 transition-all group"
                    >
                      {asset.asset_type === 'image' ? (
                        <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                      ) : asset.asset_type === 'audio' ? (
                        <svg className="w-6 h-6 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19V6l12-3v13" />
                        </svg>
                      ) : (
                        <svg className="w-6 h-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                      )}
                      <div className="absolute bottom-1 right-1 bg-black/60 text-white text-[10px] px-1 rounded">
                        {Math.round(asset.score * 100)}%
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
