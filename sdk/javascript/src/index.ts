export { VAFClient } from './client';
export type { VAFClientOptions } from './client';

// Sub-clients
export { VisionClient } from './vision';
export { AudioClient } from './audio';
export { ModelClient } from './models';
export { SearchClient } from './search';
export { PipelineClient } from './pipeline';
export { AgentClient } from './agents';
export { DatasetClient } from './datasets';
export { AlertClient } from './alerts';
export { AssetClient } from './assets';
export { TransformClient } from './transform';

// Errors
export {
  VAFError,
  AuthError,
  NotFoundError,
  ValidationError,
  ServerError,
  mapError,
} from './errors';

// Types
export type {
  LoginRequest,
  LoginResponse,
  UserProfile,
  HealthResponse,
  VisionAnalysisResult,
  DetectionResult,
  OpticalFlowResult,
  OCRResult,
  FrameDiffResult,
  ScreenAnalyzeResult,
  ErrorAnalysisResult,
  AudioAnalysisResult,
  AudioAugmentResult,
  TranscriptionResult,
  DiarizationResult,
  AudioClassificationResult,
  ModelRegistration,
  ModelInfo,
  ModelComparison,
  TrainingJob,
  SearchQuery,
  SearchResult,
  SearchIndexRequest,
  SearchStats,
  PipelineDefinition,
  PipelineInfo,
  PipelineRunInfo,
  PipelineNodeType,
  ChatMessage,
  ChatResponse,
  AgentInfo,
  AgentCreateRequest,
  MemoryEntry,
  DatasetCreateRequest,
  DatasetInfo,
  DatasetSplitRequest,
  DatasetSplitResult,
  DatasetStats,
  AlertRule,
  AlertInfo,
  AssetInfo,
  AssetUploadResult,
  AudioTransformRequest,
  AudioTransformResult,
  VideoTransformRequest,
  VideoTransformResult,
  PaginatedResponse,
  RequestOptions,
} from './types';
