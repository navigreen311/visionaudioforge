/** Shared types for integration settings components. */

export type IntegrationType = "slack" | "webhook" | "s3" | "email";

export type ConnectionStatus = "connected" | "not_connected";

export interface IntegrationCardInfo {
  type: IntegrationType;
  name: string;
  description: string;
  status: ConnectionStatus;
  icon: React.ComponentType<{ className?: string }>;
}

// ── Slack ──────────────────────────────────────────────────────────

export interface SlackConfig {
  webhookUrl: string;
  channel: string;
}

// ── Webhook ────────────────────────────────────────────────────────

export type WebhookEventKind = "alert" | "pipeline" | "model" | "asset";

export interface WebhookHeader {
  key: string;
  value: string;
}

export type PayloadFormat = "json" | "form";

export interface WebhookConfig {
  url: string;
  headers: WebhookHeader[];
  events: WebhookEventKind[];
  payloadFormat: PayloadFormat;
}

// ── S3 / Object Storage ────────────────────────────────────────────

export type StorageProvider = "aws" | "gcs" | "azure";

export interface S3Config {
  provider: StorageProvider;
  bucket: string;
  region: string;
  accessKey: string;
  secretKey: string;
}

// ── Email SMTP ─────────────────────────────────────────────────────

export interface EmailConfig {
  host: string;
  port: number;
  username: string;
  password: string;
  useTls: boolean;
}

// ── Discriminated union for all integration configs ────────────────

export type IntegrationConfig =
  | { type: "slack"; config: SlackConfig }
  | { type: "webhook"; config: WebhookConfig }
  | { type: "s3"; config: S3Config }
  | { type: "email"; config: EmailConfig };

// ── API response shapes ────────────────────────────────────────────

export interface IntegrationRecord {
  id: string;
  type: IntegrationType;
  name: string;
  status: ConnectionStatus;
  config: Record<string, unknown>;
  updatedAt: string;
}

export interface TestResult {
  ok: boolean;
  message: string;
}
