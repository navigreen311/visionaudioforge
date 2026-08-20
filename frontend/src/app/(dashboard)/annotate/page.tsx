'use client';

import { API_BASE_URL } from "@/lib/api";
import { readUserId } from "@/lib/session";

import { useState, useCallback, useEffect } from 'react';
import AnnotationCanvas from '@/components/annotation/AnnotationCanvas';
import ToolPalette, { type AnnotationTool } from '@/components/annotation/ToolPalette';
import AnnotationList, { type AnnotationItem } from '@/components/annotation/AnnotationList';
import LabelSelector from '@/components/annotation/LabelSelector';
import AssetThumbnailStrip from '@/components/annotate/AssetThumbnailStrip';
import AnnotationProgress from '@/components/annotate/AnnotationProgress';

const API_BASE = API_BASE_URL;

const DEFAULT_LABELS = ['person', 'car', 'dog', 'cat', 'truck', 'bicycle', 'bird', 'unknown'];

interface AssetInfo {
  id: string;
  filename: string;
  path: string;
  type: string;
  thumbnailUrl?: string;
  annotationCount: number;
}

interface DatasetOption {
  id: string;
  name: string;
}

export default function AnnotatePage() {
  const [activeTool, setActiveTool] = useState<AnnotationTool>('select');
  const [activeLabel, setActiveLabel] = useState(DEFAULT_LABELS[0]);
  const [annotations, setAnnotations] = useState<AnnotationItem[]>([]);
  const [selectedAnnotation, setSelectedAnnotation] = useState<string | null>(null);
  const [assets, setAssets] = useState<AssetInfo[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [datasetId, setDatasetId] = useState('');
  const [workspaceId, setWorkspaceId] = useState('');
  // Attributed to whoever is signed in, read from the token's signed claim.
  const [userId] = useState(() => readUserId() ?? '');
  const [loading, setLoading] = useState(false);
  const [exportFormat, setExportFormat] = useState('coco');
  const [status, setStatus] = useState('');
  const [datasets, setDatasets] = useState<DatasetOption[]>([]);
  const [datasetsLoading, setDatasetsLoading] = useState(false);
  const [annotationCounts, setAnnotationCounts] = useState<Record<string, number>>({});

  const currentAsset = assets[currentIndex] || null;
  const imageUrl = currentAsset
    ? `${API_BASE}/api/assets/${currentAsset.id}/download`
    : null;

  // Auto-fill workspace ID from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem('workspaceId') ?? localStorage.getItem('workspace_id');
      if (stored) setWorkspaceId(stored);
    } catch {
      // localStorage unavailable
    }
  }, []);

  // Fetch datasets when workspaceId is available
  useEffect(() => {
    if (!workspaceId) {
      setDatasets([]);
      return;
    }

    let cancelled = false;
    const fetchDatasets = async () => {
      setDatasetsLoading(true);
      try {
        const res = await fetch(
          `${API_BASE}/api/datasets?workspace_id=${workspaceId}&limit=100`,
        );
        if (!res.ok) throw new Error(`${res.status}`);
        const data = await res.json();
        if (cancelled) return;
        const items = (data.items || []).map((d: Record<string, unknown>) => ({
          id: d.id as string,
          name: (d.name as string) || (d.id as string),
        }));
        setDatasets(items);
      } catch {
        if (!cancelled) setDatasets([]);
      } finally {
        if (!cancelled) setDatasetsLoading(false);
      }
    };

    fetchDatasets();
    return () => {
      cancelled = true;
    };
  }, [workspaceId]);

  // Load assets for selected dataset
  const loadAssets = async () => {
    if (!workspaceId || !datasetId) {
      setStatus('Select a dataset first');
      return;
    }
    setLoading(true);
    setStatus('');
    try {
      const res = await fetch(
        `${API_BASE}/api/annotate/assets?workspace_id=${workspaceId}&dataset_id=${datasetId}`,
      );
      if (!res.ok) throw new Error(`Failed to load assets: ${res.status}`);
      const data = await res.json();
      const items: AssetInfo[] = (data.items || []).map(
        (a: Record<string, unknown>) => ({
          id: a.id as string,
          filename: a.filename as string,
          path: a.path as string,
          type: a.type as string,
          thumbnailUrl: (a.thumbnail_url as string | null) ?? undefined,
          annotationCount: (a.annotation_count as number) ?? 0,
        }),
      );
      setAssets(items);
      setCurrentIndex(0);
      setAnnotations([]);

      // Build counts map
      const counts: Record<string, number> = {};
      items.forEach((a) => {
        counts[a.id] = a.annotationCount;
      });
      setAnnotationCounts(counts);

      setStatus(`Loaded ${items.length} assets`);
      if (items.length > 0) {
        await loadAnnotations(items[0].id);
      }
    } catch (err) {
      setStatus(`Error: ${(err as Error).message}`);
    } finally {
      setLoading(false);
    }
  };

  // Load annotations for an asset
  const loadAnnotations = async (assetId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/annotations?asset_id=${assetId}`);
      if (!res.ok) return;
      const data = await res.json();
      setAnnotations(data);
    } catch {
      // Silently fail
    }
  };

  // Navigate between assets
  const goToAsset = async (index: number) => {
    if (index < 0 || index >= assets.length) return;
    setCurrentIndex(index);
    setAnnotations([]);
    setSelectedAnnotation(null);
    await loadAnnotations(assets[index].id);
  };

  // Create annotation
  const handleAnnotationCreate = useCallback(
    async (type: string, data: Record<string, unknown>) => {
      if (!currentAsset) return;
      try {
        const body: Record<string, unknown> = {
          asset_id: currentAsset.id,
          annotation_type: type,
          data,
          user_id: userId,
        };
        if (datasetId) body.dataset_id = datasetId;

        const res = await fetch(`${API_BASE}/api/annotations`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        if (!res.ok) throw new Error(`Failed to create: ${res.status}`);
        const ann = await res.json();
        setAnnotations((prev) => [...prev, ann]);
        // Update counts
        setAnnotationCounts((prev) => ({
          ...prev,
          [currentAsset.id]: (prev[currentAsset.id] ?? 0) + 1,
        }));
        setStatus(`Created ${type} annotation`);
      } catch (err) {
        setStatus(`Error: ${(err as Error).message}`);
      }
    },
    [currentAsset, userId, datasetId],
  );

  // Delete annotation
  const handleDelete = async (id: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/annotations/${id}`, {
        method: 'DELETE',
      });
      if (!res.ok) throw new Error(`Delete failed: ${res.status}`);
      setAnnotations((prev) => prev.filter((a) => a.id !== id));
      if (selectedAnnotation === id) setSelectedAnnotation(null);
      if (currentAsset) {
        setAnnotationCounts((prev) => ({
          ...prev,
          [currentAsset.id]: Math.max(0, (prev[currentAsset.id] ?? 1) - 1),
        }));
      }
      setStatus('Annotation deleted');
    } catch (err) {
      setStatus(`Error: ${(err as Error).message}`);
    }
  };

  // Export
  const handleExport = async () => {
    if (!datasetId) {
      setStatus('Select a dataset for export');
      return;
    }
    try {
      const res = await fetch(
        `${API_BASE}/api/datasets/${datasetId}/annotations/export?format=${exportFormat}`,
        { method: 'POST' },
      );
      if (!res.ok) throw new Error(`Export failed: ${res.status}`);
      const data = await res.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `annotations_${exportFormat}.json`;
      a.click();
      URL.revokeObjectURL(url);
      setStatus(`Exported in ${exportFormat} format`);
    } catch (err) {
      setStatus(`Error: ${(err as Error).message}`);
    }
  };

  // Annotation progress
  const annotatedCount = Object.values(annotationCounts).filter((c) => c > 0).length;

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Annotation Studio</h1>
          <p className="text-sm text-gray-500">
            Annotate assets with bounding boxes, polygons, keypoints, and labels
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={exportFormat}
            onChange={(e) => setExportFormat(e.target.value)}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
          >
            <option value="coco">COCO</option>
            <option value="yolo">YOLO</option>
            <option value="voc">VOC</option>
          </select>
          <button
            onClick={handleExport}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            Export
          </button>
        </div>
      </div>

      {/* Smart selectors bar */}
      <div className="flex gap-3 items-end flex-wrap">
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-500">Dataset</label>
          <select
            value={datasetId}
            onChange={(e) => setDatasetId(e.target.value)}
            disabled={datasetsLoading || datasets.length === 0}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm w-72 disabled:opacity-50"
          >
            <option value="">
              {datasetsLoading
                ? 'Loading datasets...'
                : datasets.length === 0
                  ? 'No datasets available'
                  : 'Select a dataset'}
            </option>
            {datasets.map((ds) => (
              <option key={ds.id} value={ds.id}>
                {ds.name}
              </option>
            ))}
          </select>
        </div>
        <button
          onClick={loadAssets}
          disabled={loading || !datasetId}
          className="rounded-lg bg-gray-800 px-4 py-2 text-sm font-medium text-white hover:bg-gray-900 disabled:opacity-50"
        >
          {loading ? 'Loading...' : 'Load Assets'}
        </button>
        {status && (
          <span className="text-sm text-gray-500 py-2">{status}</span>
        )}
      </div>

      {/* Progress bar */}
      {assets.length > 0 && (
        <AnnotationProgress annotated={annotatedCount} total={assets.length} />
      )}

      {/* Thumbnail strip */}
      {assets.length > 0 && (
        <AssetThumbnailStrip
          assets={assets}
          activeIndex={currentIndex}
          onSelect={goToAsset}
          annotationCounts={annotationCounts}
        />
      )}

      {/* Main layout */}
      <div className="flex gap-4" style={{ minHeight: 600 }}>
        {/* Left sidebar: tools + labels */}
        <div className="w-48 flex-shrink-0 flex flex-col gap-4">
          <ToolPalette activeTool={activeTool} onToolChange={setActiveTool} />
          <LabelSelector
            labels={DEFAULT_LABELS}
            selected={activeLabel}
            onChange={setActiveLabel}
          />
        </div>

        {/* Canvas area */}
        <div className="flex-1 flex flex-col gap-2">
          {/* Asset navigator */}
          <div className="flex items-center justify-between bg-white rounded-lg border border-gray-200 px-4 py-2">
            <button
              onClick={() => goToAsset(currentIndex - 1)}
              disabled={currentIndex <= 0}
              className="rounded px-3 py-1 text-sm font-medium bg-gray-100 hover:bg-gray-200 disabled:opacity-40"
            >
              Prev
            </button>
            <span className="text-sm text-gray-600">
              {assets.length > 0
                ? `${currentIndex + 1} / ${assets.length} — ${currentAsset?.filename || ''}`
                : 'No assets loaded'}
            </span>
            <button
              onClick={() => goToAsset(currentIndex + 1)}
              disabled={currentIndex >= assets.length - 1}
              className="rounded px-3 py-1 text-sm font-medium bg-gray-100 hover:bg-gray-200 disabled:opacity-40"
            >
              Next
            </button>
          </div>

          {/* Canvas */}
          <AnnotationCanvas
            imageUrl={imageUrl}
            activeTool={activeTool}
            annotations={annotations}
            selectedId={selectedAnnotation}
            activeLabel={activeLabel}
            onAnnotationCreate={handleAnnotationCreate}
            onSelect={setSelectedAnnotation}
          />
        </div>

        {/* Right sidebar: annotation list */}
        <div className="w-72 flex-shrink-0 flex flex-col gap-2">
          <div className="bg-white rounded-lg border border-gray-200 p-3">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">
              Annotations ({annotations.length})
            </h3>
            <AnnotationList
              annotations={annotations}
              selectedId={selectedAnnotation}
              onSelect={setSelectedAnnotation}
              onDelete={handleDelete}
            />
          </div>

          {/* Audio/video segment placeholder */}
          {currentAsset &&
            (currentAsset.type === 'audio' || currentAsset.type === 'video') && (
              <div className="bg-white rounded-lg border border-gray-200 p-3">
                <h3 className="text-sm font-semibold text-gray-700 mb-2">
                  Timeline Segments
                </h3>
                <p className="text-xs text-gray-400">
                  Use the segment tool to annotate time ranges for audio/video
                  assets.
                </p>
                <div className="mt-2 flex gap-2">
                  <input
                    type="number"
                    placeholder="Start (s)"
                    step="0.1"
                    min="0"
                    className="w-20 rounded border border-gray-300 px-2 py-1 text-xs"
                    id="seg-start"
                  />
                  <input
                    type="number"
                    placeholder="End (s)"
                    step="0.1"
                    min="0"
                    className="w-20 rounded border border-gray-300 px-2 py-1 text-xs"
                    id="seg-end"
                  />
                  <button
                    onClick={() => {
                      const startEl = document.getElementById(
                        'seg-start',
                      ) as HTMLInputElement;
                      const endEl = document.getElementById(
                        'seg-end',
                      ) as HTMLInputElement;
                      const start_s = parseFloat(startEl?.value || '0');
                      const end_s = parseFloat(endEl?.value || '0');
                      if (end_s > start_s) {
                        handleAnnotationCreate('segment', {
                          start_s,
                          end_s,
                          label: activeLabel,
                        });
                      }
                    }}
                    className="rounded bg-brand-600 px-2 py-1 text-xs text-white hover:bg-brand-700"
                  >
                    Add
                  </button>
                </div>
              </div>
            )}
        </div>
      </div>
    </div>
  );
}
