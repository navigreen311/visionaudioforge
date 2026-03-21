'use client';

import { useState, useEffect, useCallback, useRef } from 'react';

// ------------------------------------------------------------------
// Types
// ------------------------------------------------------------------

type ReviewType =
  | 'annotation_qa'
  | 'detection_verify'
  | 'alert_review'
  | 'content_moderation'
  | 'model_output_check';

type Priority = 'low' | 'normal' | 'high' | 'critical';
type TaskStatus = 'pending' | 'assigned' | 'in_review' | 'completed' | 'escalated';
type Decision = 'approved' | 'rejected' | 'escalated';

interface PreviousReview {
  review_id: string;
  reviewer_id: string;
  decision: string;
  score: number | null;
  notes: string | null;
  created_at: string;
}

interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface Annotation {
  id: string;
  label: string;
  confidence: number;
  bbox: BoundingBox | null;
  flagged: boolean;
}

interface DatasetRow {
  [key: string]: string | number | boolean | null;
}

interface ModelPrediction {
  input: string;
  prediction: string;
  confidence: number;
}

interface TaskData {
  media_url: string | null;
  media_type: 'image' | 'video' | null;
  annotations: Annotation[];
  dataset_sample: DatasetRow[];
  model_prediction: ModelPrediction | null;
}

interface ReviewTask {
  task_id: string;
  workspace_id: string;
  asset_id: string;
  review_type: ReviewType;
  priority: Priority;
  status: TaskStatus;
  required_reviews: number;
  sla_hours: number;
  sla_deadline: string;
  assigned_to: string | null;
  assigned_at: string | null;
  reviews: PreviousReview[];
  created_at: string;
  updated_at: string;
  title?: string;
}

interface ReviewWorkspaceProps {
  task: ReviewTask | null;
  isOpen: boolean;
  onClose: () => void;
  onDecision: (taskId: string, decision: Decision | 'skip') => void;
}

// ------------------------------------------------------------------
// Constants
// ------------------------------------------------------------------

const API = '/api/reviewops';
const NOTE_MAX_LENGTH = 500;

const PRIORITY_COLORS: Record<Priority, string> = {
  critical: 'bg-red-100 text-red-800',
  high: 'bg-orange-100 text-orange-800',
  normal: 'bg-blue-100 text-blue-800',
  low: 'bg-gray-100 text-gray-700',
};

const REVIEW_TYPE_LABELS: Record<ReviewType, string> = {
  annotation_qa: 'Annotation QA',
  detection_verify: 'Detection Verify',
  alert_review: 'Alert Review',
  content_moderation: 'Content Moderation',
  model_output_check: 'Model Output Check',
};

// ------------------------------------------------------------------
// Helpers
// ------------------------------------------------------------------

function formatSLARemaining(deadline: string): { text: string; overdue: boolean } {
  const diff = new Date(deadline).getTime() - Date.now();
  const absDiff = Math.abs(diff);
  const hours = Math.floor(absDiff / 3600000);
  const minutes = Math.floor((absDiff % 3600000) / 60000);
  const text = diff <= 0 ? `-${hours}h ${minutes}m` : `${hours}h ${minutes}m`;
  return { text, overdue: diff <= 0 };
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// ------------------------------------------------------------------
// Sub-components
// ------------------------------------------------------------------

function Badge({ className, children }: { className: string; children: React.ReactNode }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${className}`}>
      {children}
    </span>
  );
}

// -- Section A: Header ---

function WorkspaceHeader({
  task,
  sla,
  submitting,
  canApprove,
  onApprove,
  onReject,
  onSkip,
  onEscalate,
}: {
  task: ReviewTask;
  sla: { text: string; overdue: boolean };
  submitting: boolean;
  canApprove: boolean;
  onApprove: () => void;
  onReject: () => void;
  onSkip: () => void;
  onEscalate: () => void;
}) {
  const title = task.title || `Task ${task.task_id.slice(0, 8)}`;

  return (
    <div className="space-y-3">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="text-lg font-semibold text-gray-900 truncate">{title}</h2>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <Badge className="bg-indigo-100 text-indigo-800">
              {REVIEW_TYPE_LABELS[task.review_type] ?? task.review_type}
            </Badge>
            <Badge className={PRIORITY_COLORS[task.priority]}>{task.priority}</Badge>
            <span
              className={`text-xs font-mono px-2 py-0.5 rounded ${
                sla.overdue ? 'bg-red-100 text-red-700' : 'bg-green-50 text-green-700'
              }`}
            >
              SLA {sla.text}
            </span>
          </div>
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={onApprove}
          disabled={submitting || !canApprove}
          className="rounded-lg bg-green-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Approve
        </button>
        <button
          onClick={onReject}
          disabled={submitting || !canApprove}
          className="rounded-lg bg-red-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Reject
        </button>
        <button
          onClick={onSkip}
          disabled={submitting}
          className="rounded-lg bg-gray-200 px-4 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Skip
        </button>
        <button
          onClick={onEscalate}
          disabled={submitting}
          className="rounded-lg bg-amber-500 px-4 py-1.5 text-sm font-medium text-white hover:bg-amber-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Escalate
        </button>
      </div>
    </div>
  );
}

// -- Section B: Media Preview ---

function AnnotationCanvas({
  mediaUrl,
  annotations,
}: {
  mediaUrl: string;
  annotations: Annotation[];
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const img = imgRef.current;
    if (!canvas || !img) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;
    ctx.drawImage(img, 0, 0);

    annotations.forEach((ann) => {
      if (!ann.bbox) return;
      const { x, y, width, height } = ann.bbox;
      ctx.strokeStyle = ann.flagged ? '#ef4444' : '#3b82f6';
      ctx.lineWidth = 2;
      ctx.strokeRect(x, y, width, height);

      ctx.fillStyle = ann.flagged ? '#ef4444' : '#3b82f6';
      ctx.font = '12px sans-serif';
      const labelText = `${ann.label} (${(ann.confidence * 100).toFixed(0)}%)`;
      const textMetrics = ctx.measureText(labelText);
      ctx.fillRect(x, y - 16, textMetrics.width + 8, 16);
      ctx.fillStyle = '#ffffff';
      ctx.fillText(labelText, x + 4, y - 4);
    });
  }, [annotations]);

  useEffect(() => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      imgRef.current = img;
      draw();
    };
    img.src = mediaUrl;
  }, [mediaUrl, draw]);

  return (
    <canvas
      ref={canvasRef}
      className="w-full h-auto rounded-lg border border-gray-200 bg-gray-50"
    />
  );
}

function MediaPreview({
  reviewType,
  taskData,
}: {
  reviewType: ReviewType;
  taskData: TaskData | null;
}) {
  if (!taskData) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center text-sm text-gray-400">
        Loading media preview...
      </div>
    );
  }

  // Annotation QA / Detection Verify: canvas with bounding boxes
  if (
    (reviewType === 'annotation_qa' || reviewType === 'detection_verify') &&
    taskData.media_url
  ) {
    return (
      <AnnotationCanvas mediaUrl={taskData.media_url} annotations={taskData.annotations} />
    );
  }

  // Alert review: video or image
  if (reviewType === 'alert_review' && taskData.media_url) {
    if (taskData.media_type === 'video') {
      return (
        <video
          src={taskData.media_url}
          controls
          className="w-full rounded-lg border border-gray-200"
        />
      );
    }
    return (
      <img
        src={taskData.media_url}
        alt="Alert media"
        className="w-full rounded-lg border border-gray-200 object-contain max-h-96"
      />
    );
  }

  // Dataset: sample rows table
  if (reviewType === 'content_moderation' && taskData.dataset_sample.length > 0) {
    const columns = Object.keys(taskData.dataset_sample[0]);
    return (
      <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
        <table className="min-w-full divide-y divide-gray-200 text-xs">
          <thead className="bg-gray-50">
            <tr>
              {columns.map((col) => (
                <th key={col} className="px-3 py-2 text-left font-medium text-gray-500">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {taskData.dataset_sample.map((row, idx) => (
              <tr key={idx} className="hover:bg-gray-50">
                {columns.map((col) => (
                  <td key={col} className="px-3 py-2 text-gray-700 max-w-[200px] truncate">
                    {String(row[col] ?? '')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  // Model output check: input + prediction
  if (reviewType === 'model_output_check' && taskData.model_prediction) {
    const pred = taskData.model_prediction;
    return (
      <div className="space-y-3">
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <p className="text-xs font-medium text-gray-500 mb-1">Input</p>
          <p className="text-sm text-gray-800 whitespace-pre-wrap">{pred.input}</p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <p className="text-xs font-medium text-gray-500 mb-1">Prediction</p>
          <p className="text-sm text-gray-800 whitespace-pre-wrap">{pred.prediction}</p>
          <p className="text-xs text-gray-500 mt-2">
            Confidence: {(pred.confidence * 100).toFixed(1)}%
          </p>
        </div>
      </div>
    );
  }

  // Fallback
  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center text-sm text-gray-400">
      No preview available for this task type.
    </div>
  );
}

// -- Section C: Annotation List ---

function AnnotationList({
  annotations,
  onToggleFlag,
}: {
  annotations: Annotation[];
  onToggleFlag: (annotationId: string) => void;
}) {
  if (annotations.length === 0) {
    return (
      <p className="text-sm text-gray-400 text-center py-4">No annotations to review.</p>
    );
  }

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-gray-700">Annotations</h3>
      <div className="space-y-1.5 max-h-60 overflow-y-auto">
        {annotations.map((ann) => (
          <div
            key={ann.id}
            className={`flex items-center justify-between rounded-lg border px-3 py-2 text-sm ${
              ann.flagged
                ? 'border-red-300 bg-red-50'
                : 'border-gray-200 bg-white'
            }`}
          >
            <div className="flex items-center gap-3 min-w-0">
              <span className="font-medium text-gray-800 truncate">{ann.label}</span>
              <span className="text-xs text-gray-500">
                {(ann.confidence * 100).toFixed(0)}%
              </span>
              {ann.bbox && (
                <span className="text-xs text-gray-400 font-mono hidden sm:inline">
                  [{ann.bbox.x}, {ann.bbox.y}, {ann.bbox.width}, {ann.bbox.height}]
                </span>
              )}
            </div>
            <button
              onClick={() => onToggleFlag(ann.id)}
              className={`shrink-0 ml-2 rounded px-2 py-0.5 text-xs font-medium transition-colors ${
                ann.flagged
                  ? 'bg-red-600 text-white hover:bg-red-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
              title={ann.flagged ? 'Unflag annotation' : 'Flag annotation'}
            >
              {ann.flagged ? 'Flagged' : 'Flag'}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

// -- Section D: Quality Note ---

function QualityNote({
  value,
  onChange,
  required,
}: {
  value: string;
  onChange: (val: string) => void;
  required: boolean;
}) {
  const remaining = NOTE_MAX_LENGTH - value.length;

  return (
    <div className="space-y-1">
      <label className="flex items-center gap-1 text-sm font-medium text-gray-700">
        Quality Notes
        {required && <span className="text-red-500">*</span>}
      </label>
      <textarea
        value={value}
        onChange={(e) => {
          if (e.target.value.length <= NOTE_MAX_LENGTH) {
            onChange(e.target.value);
          }
        }}
        rows={3}
        placeholder={
          required
            ? 'Required: explain the reason for rejection...'
            : 'Optional: add review notes...'
        }
        className={`w-full rounded-lg border px-3 py-2 text-sm resize-none transition-colors ${
          required && value.length === 0
            ? 'border-red-300 focus:ring-red-500 focus:border-red-500'
            : 'border-gray-300 focus:ring-brand-500 focus:border-brand-500'
        }`}
      />
      <p className={`text-xs text-right ${remaining < 50 ? 'text-amber-600' : 'text-gray-400'}`}>
        {remaining} characters remaining
      </p>
    </div>
  );
}

// -- Section E: Previous Reviews ---

function PreviousReviews({ reviews }: { reviews: PreviousReview[] }) {
  if (reviews.length === 0) {
    return (
      <p className="text-sm text-gray-400 text-center py-4">No previous reviews.</p>
    );
  }

  const decisionColors: Record<string, string> = {
    approved: 'bg-green-100 text-green-800',
    rejected: 'bg-red-100 text-red-800',
    needs_correction: 'bg-yellow-100 text-yellow-800',
    escalated: 'bg-amber-100 text-amber-800',
  };

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-gray-700">Previous Reviews</h3>
      <div className="space-y-2 max-h-48 overflow-y-auto">
        {reviews.map((r) => (
          <div
            key={r.review_id}
            className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs text-gray-500">
                  {r.reviewer_id.slice(0, 8)}
                </span>
                <Badge className={decisionColors[r.decision] ?? 'bg-gray-100 text-gray-700'}>
                  {r.decision}
                </Badge>
                {r.score !== null && (
                  <span className="text-xs text-gray-500">{r.score}/5</span>
                )}
              </div>
              <span className="text-xs text-gray-400">{formatDateTime(r.created_at)}</span>
            </div>
            {r.notes && (
              <p className="text-xs text-gray-600 mt-1 line-clamp-2">{r.notes}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
// Main Component
// ------------------------------------------------------------------

export default function ReviewWorkspace({ task, isOpen, onClose, onDecision }: ReviewWorkspaceProps) {
  const [taskData, setTaskData] = useState<TaskData | null>(null);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [qualityNote, setQualityNote] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [noteRequired, setNoteRequired] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch task data when task changes
  const fetchTaskData = useCallback(async (taskId: string) => {
    try {
      setError(null);
      const res = await fetch(`${API}/tasks/${taskId}/data`);
      if (!res.ok) throw new Error('Failed to load task data');
      const data: TaskData = await res.json();
      setTaskData(data);
      setAnnotations(data.annotations.map((a) => ({ ...a })));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load task data';
      setError(message);
    }
  }, []);

  useEffect(() => {
    if (task && isOpen) {
      setQualityNote('');
      setNoteRequired(false);
      setTaskData(null);
      setAnnotations([]);
      setError(null);
      fetchTaskData(task.task_id);
    }
  }, [task, isOpen, fetchTaskData]);

  // Toggle flag on annotation
  const handleToggleFlag = useCallback((annotationId: string) => {
    setAnnotations((prev) =>
      prev.map((a) =>
        a.id === annotationId ? { ...a, flagged: !a.flagged } : a,
      ),
    );
  }, []);

  // Submit decision
  const handleSubmit = useCallback(
    async (decision: Decision) => {
      if (!task) return;

      // Reject requires a quality note
      if (decision === 'rejected' && qualityNote.trim().length === 0) {
        setNoteRequired(true);
        return;
      }

      setSubmitting(true);
      setError(null);

      try {
        const flaggedAnnotations = annotations
          .filter((a) => a.flagged)
          .map((a) => a.id);

        const res = await fetch(`${API}/tasks/${task.task_id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            decision,
            notes: qualityNote || null,
            flagged_annotations: flaggedAnnotations,
          }),
        });

        if (!res.ok) {
          const body = await res.json().catch(() => ({ detail: 'Request failed' }));
          throw new Error(body.detail || 'Failed to submit decision');
        }

        onDecision(task.task_id, decision);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Submission failed';
        setError(message);
      } finally {
        setSubmitting(false);
      }
    },
    [task, qualityNote, annotations, onDecision],
  );

  // Skip handler
  const handleSkip = useCallback(() => {
    if (!task) return;
    onDecision(task.task_id, 'skip');
  }, [task, onDecision]);

  // Close on Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Derived state
  const sla = task ? formatSLARemaining(task.sla_deadline) : { text: '', overdue: false };

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/30 z-40 transition-opacity"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Slide-over panel */}
      <div
        className={`fixed inset-y-0 right-0 z-50 flex transform transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
        style={{ width: '60%', minWidth: '480px', maxWidth: '960px' }}
        role="dialog"
        aria-modal="true"
        aria-label="Review workspace"
      >
        <div className="flex h-full w-full flex-col bg-gray-50 shadow-2xl">
          {/* Top bar with close */}
          <div className="flex items-center justify-between border-b border-gray-200 bg-white px-6 py-3">
            <span className="text-sm font-medium text-gray-500">Review Workspace</span>
            <button
              onClick={onClose}
              className="rounded-lg p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
              aria-label="Close review workspace"
            >
              <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path
                  fillRule="evenodd"
                  d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          </div>

          {/* Scrollable content */}
          <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
            {!task ? (
              <div className="text-center py-20 text-gray-400">
                <p className="text-lg">No task selected</p>
                <p className="text-sm mt-1">Select a task from the queue to begin reviewing.</p>
              </div>
            ) : (
              <>
                {/* Error banner */}
                {error && (
                  <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700">
                    {error}
                  </div>
                )}

                {/* A. Header */}
                <WorkspaceHeader
                  task={task}
                  sla={sla}
                  submitting={submitting}
                  canApprove={!submitting}
                  onApprove={() => handleSubmit('approved')}
                  onReject={() => handleSubmit('rejected')}
                  onSkip={handleSkip}
                  onEscalate={() => handleSubmit('escalated')}
                />

                {/* B. Media Preview */}
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-2">Preview</h3>
                  <MediaPreview reviewType={task.review_type} taskData={taskData} />
                </div>

                {/* C. Annotation List */}
                <AnnotationList annotations={annotations} onToggleFlag={handleToggleFlag} />

                {/* D. Quality Note */}
                <QualityNote
                  value={qualityNote}
                  onChange={(val) => {
                    setQualityNote(val);
                    if (noteRequired && val.trim().length > 0) {
                      setNoteRequired(false);
                    }
                  }}
                  required={noteRequired}
                />

                {/* E. Previous Reviews */}
                <PreviousReviews reviews={task.reviews} />
              </>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
