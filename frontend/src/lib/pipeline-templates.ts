/**
 * Static pipeline template definitions.
 *
 * Each template provides a pre-built pipeline that users can load
 * into the canvas as a starting point.
 */

export interface TemplateNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  config: Record<string, unknown>;
}

export interface TemplateEdge {
  id: string;
  source: string;
  target: string;
}

export interface PipelineTemplate {
  key: string;
  name: string;
  description: string;
  category: "Vision" | "Audio" | "Transform" | "Monitoring" | "Reporting" | "Evidence";
  nodes: TemplateNode[];
  edges: TemplateEdge[];
}

export const PIPELINE_TEMPLATES: PipelineTemplate[] = [
  {
    key: "screen_ocr",
    name: "Screen OCR Pipeline",
    description:
      "Capture screen frames, extract text via OCR, and log structured results for downstream analysis.",
    category: "Vision",
    nodes: [
      {
        id: "screen_capture_1",
        type: "screen_capture",
        position: { x: 80, y: 140 },
        config: { interval_ms: 2000, region: "full" },
      },
      {
        id: "ocr_extract_2",
        type: "ocr_extract",
        position: { x: 360, y: 140 },
        config: { language: "eng", confidence_threshold: 0.6 },
      },
      {
        id: "log_output_3",
        type: "log_output",
        position: { x: 640, y: 140 },
        config: { format: "json", destination: "stdout" },
      },
    ],
    edges: [
      { id: "e-1-2", source: "screen_capture_1", target: "ocr_extract_2" },
      { id: "e-2-3", source: "ocr_extract_2", target: "log_output_3" },
    ],
  },
  {
    key: "camera_object_detection",
    name: "Camera Object Detection",
    description:
      "Stream from a camera source, run object detection, and trigger alerts on specific classes.",
    category: "Vision",
    nodes: [
      {
        id: "camera_input_1",
        type: "camera_input",
        position: { x: 80, y: 140 },
        config: { device_index: 0, fps: 15 },
      },
      {
        id: "object_detect_2",
        type: "object_detect",
        position: { x: 360, y: 140 },
        config: { model: "yolov8n", confidence: 0.5, classes: "person,vehicle" },
      },
      {
        id: "alert_trigger_3",
        type: "alert_trigger",
        position: { x: 640, y: 100 },
        config: { condition: "count > 0", severity: "high" },
      },
      {
        id: "log_output_4",
        type: "log_output",
        position: { x: 640, y: 220 },
        config: { format: "json", destination: "stdout" },
      },
    ],
    edges: [
      { id: "e-1-2", source: "camera_input_1", target: "object_detect_2" },
      { id: "e-2-3", source: "object_detect_2", target: "alert_trigger_3" },
      { id: "e-2-4", source: "object_detect_2", target: "log_output_4" },
    ],
  },
  {
    key: "audio_monitor",
    name: "Audio Monitor",
    description:
      "Capture microphone input, compute spectral features, and classify audio events in real-time.",
    category: "Audio",
    nodes: [
      {
        id: "mic_input_1",
        type: "mic_input",
        position: { x: 80, y: 140 },
        config: { sample_rate: 16000, chunk_ms: 500 },
      },
      {
        id: "spectral_analysis_2",
        type: "spectral_analysis",
        position: { x: 360, y: 100 },
        config: { features: ["mfcc", "mel"], n_mfcc: 13 },
      },
      {
        id: "audio_classify_3",
        type: "audio_classify",
        position: { x: 640, y: 100 },
        config: { model: "audio_event_classifier", threshold: 0.7 },
      },
      {
        id: "alert_trigger_4",
        type: "alert_trigger",
        position: { x: 920, y: 100 },
        config: { condition: "class in [gunshot,glass_break,scream]", severity: "critical" },
      },
    ],
    edges: [
      { id: "e-1-2", source: "mic_input_1", target: "spectral_analysis_2" },
      { id: "e-2-3", source: "spectral_analysis_2", target: "audio_classify_3" },
      { id: "e-3-4", source: "audio_classify_3", target: "alert_trigger_4" },
    ],
  },
  {
    key: "video_transform",
    name: "Video Transform",
    description:
      "Ingest video files, apply frame-level transformations (resize, normalize, augment), and export processed output.",
    category: "Transform",
    nodes: [
      {
        id: "video_input_1",
        type: "video_input",
        position: { x: 80, y: 140 },
        config: { source: "file", path: "" },
      },
      {
        id: "frame_resize_2",
        type: "frame_resize",
        position: { x: 360, y: 100 },
        config: { width: 640, height: 480, interpolation: "bilinear" },
      },
      {
        id: "normalize_3",
        type: "normalize",
        position: { x: 360, y: 240 },
        config: { method: "min_max", per_channel: true },
      },
      {
        id: "video_export_4",
        type: "video_export",
        position: { x: 640, y: 140 },
        config: { format: "mp4", codec: "h264", quality: 85 },
      },
    ],
    edges: [
      { id: "e-1-2", source: "video_input_1", target: "frame_resize_2" },
      { id: "e-1-3", source: "video_input_1", target: "normalize_3" },
      { id: "e-2-4", source: "frame_resize_2", target: "video_export_4" },
      { id: "e-3-4", source: "normalize_3", target: "video_export_4" },
    ],
  },
  {
    key: "scheduled_report",
    name: "Scheduled Report",
    description:
      "Aggregate pipeline run metrics on a schedule, build a summary report, and deliver it via webhook or email.",
    category: "Reporting",
    nodes: [
      {
        id: "metrics_query_1",
        type: "metrics_query",
        position: { x: 80, y: 140 },
        config: { source: "pipeline_runs", window: "24h" },
      },
      {
        id: "aggregate_2",
        type: "aggregate",
        position: { x: 360, y: 140 },
        config: { operations: ["count", "avg_duration", "error_rate"] },
      },
      {
        id: "report_builder_3",
        type: "report_builder",
        position: { x: 640, y: 140 },
        config: { template: "daily_summary", format: "html" },
      },
      {
        id: "webhook_4",
        type: "webhook",
        position: { x: 920, y: 140 },
        config: { url: "", method: "POST" },
      },
    ],
    edges: [
      { id: "e-1-2", source: "metrics_query_1", target: "aggregate_2" },
      { id: "e-2-3", source: "aggregate_2", target: "report_builder_3" },
      { id: "e-3-4", source: "report_builder_3", target: "webhook_4" },
    ],
  },
  {
    key: "evidence_collector",
    name: "Evidence Collector",
    description:
      "Monitor multiple streams, detect anomalies, snapshot evidence frames, and store tagged artifacts for review.",
    category: "Evidence",
    nodes: [
      {
        id: "multi_stream_1",
        type: "multi_stream_input",
        position: { x: 80, y: 140 },
        config: { streams: [], max_concurrent: 4 },
      },
      {
        id: "anomaly_detect_2",
        type: "anomaly_detect",
        position: { x: 360, y: 100 },
        config: { model: "isolation_forest", sensitivity: 0.8 },
      },
      {
        id: "snapshot_3",
        type: "snapshot",
        position: { x: 640, y: 100 },
        config: { quality: 95, include_metadata: true },
      },
      {
        id: "asset_store_4",
        type: "asset_store",
        position: { x: 920, y: 100 },
        config: { tags: ["evidence", "auto"], retention_days: 90 },
      },
      {
        id: "log_output_5",
        type: "log_output",
        position: { x: 640, y: 240 },
        config: { format: "json", destination: "stdout" },
      },
    ],
    edges: [
      { id: "e-1-2", source: "multi_stream_1", target: "anomaly_detect_2" },
      { id: "e-2-3", source: "anomaly_detect_2", target: "snapshot_3" },
      { id: "e-3-4", source: "snapshot_3", target: "asset_store_4" },
      { id: "e-2-5", source: "anomaly_detect_2", target: "log_output_5" },
    ],
  },
];

export function getTemplateByKey(key: string): PipelineTemplate | undefined {
  return PIPELINE_TEMPLATES.find((t) => t.key === key);
}
