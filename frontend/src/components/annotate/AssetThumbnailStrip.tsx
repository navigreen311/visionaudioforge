'use client';

import { useEffect, useRef, useCallback } from 'react';

interface AssetThumbnailStripProps {
  assets: { id: string; filename: string; thumbnailUrl?: string }[];
  activeIndex: number;
  onSelect: (index: number) => void;
  annotationCounts: Record<string, number>;
}

export default function AssetThumbnailStrip({
  assets,
  activeIndex,
  onSelect,
  annotationCounts,
}: AssetThumbnailStripProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const activeRef = useRef<HTMLButtonElement>(null);

  // Scroll active thumbnail into view
  useEffect(() => {
    activeRef.current?.scrollIntoView({
      behavior: 'smooth',
      block: 'nearest',
      inline: 'center',
    });
  }, [activeIndex]);

  // Arrow key navigation
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        onSelect(Math.max(0, activeIndex - 1));
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        onSelect(Math.min(assets.length - 1, activeIndex + 1));
      }
    },
    [activeIndex, assets.length, onSelect],
  );

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    container.addEventListener('keydown', handleKeyDown);
    return () => container.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  if (assets.length === 0) return null;

  return (
    <div
      ref={containerRef}
      tabIndex={0}
      role="listbox"
      aria-label="Asset thumbnails"
      className="flex items-center gap-1.5 overflow-x-auto px-2 py-1 bg-white rounded-lg border border-gray-200"
      style={{ height: 80 }}
    >
      {assets.map((asset, idx) => {
        const isActive = idx === activeIndex;
        const count = annotationCounts[asset.id] ?? 0;

        return (
          <button
            key={asset.id}
            ref={isActive ? activeRef : undefined}
            role="option"
            aria-selected={isActive}
            onClick={() => onSelect(idx)}
            title={asset.filename}
            className={`relative flex-shrink-0 rounded overflow-hidden transition-all focus:outline-none focus:ring-2 focus:ring-blue-400 ${
              isActive
                ? 'ring-2 ring-blue-500 shadow-md'
                : 'ring-1 ring-gray-200 hover:ring-gray-400'
            }`}
            style={{ width: 72, height: 56 }}
          >
            {asset.thumbnailUrl ? (
              <img
                src={asset.thumbnailUrl}
                alt={asset.filename}
                className="w-full h-full object-cover"
                draggable={false}
              />
            ) : (
              <div className="w-full h-full bg-gray-100 flex items-center justify-center">
                <span className="text-[9px] text-gray-400 truncate px-1 text-center leading-tight">
                  {asset.filename}
                </span>
              </div>
            )}

            {/* Annotation count badge */}
            {count > 0 && (
              <span className="absolute top-0.5 right-0.5 min-w-[16px] h-4 flex items-center justify-center rounded-full bg-blue-600 text-white text-[10px] font-semibold px-1">
                {count}
              </span>
            )}

            {/* Active indicator */}
            {isActive && (
              <span className="absolute bottom-0 inset-x-0 h-0.5 bg-blue-500" />
            )}
          </button>
        );
      })}
    </div>
  );
}
