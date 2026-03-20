import type {
  VisionAnalysisResult,
  DetectionResult,
  OpticalFlowResult,
  OCRResult,
  FrameDiffResult,
  ScreenAnalyzeResult,
  ErrorAnalysisResult,
  RequestOptions,
} from './types';

type RequestFn = (
  method: string,
  path: string,
  options?: { body?: unknown; formData?: FormData; options?: RequestOptions },
) => Promise<unknown>;

/**
 * Client for vision analysis endpoints.
 */
export class VisionClient {
  constructor(private readonly _request: RequestFn) {}

  /** Analyze an uploaded image. */
  async analyze(file: Blob | FormData, options?: RequestOptions): Promise<VisionAnalysisResult> {
    const form = file instanceof FormData ? file : this._buildForm(file);
    return this._request('POST', '/api/vision/analyze', { formData: form, options }) as Promise<VisionAnalysisResult>;
  }

  /** Run object detection (YOLO). */
  async detect(file: Blob | FormData, options?: RequestOptions): Promise<DetectionResult> {
    const form = file instanceof FormData ? file : this._buildForm(file);
    return this._request('POST', '/api/vision/detect', { formData: form, options }) as Promise<DetectionResult>;
  }

  /** Compute optical flow between frames. */
  async opticalFlow(file: Blob | FormData, options?: RequestOptions): Promise<OpticalFlowResult> {
    const form = file instanceof FormData ? file : this._buildForm(file);
    return this._request('POST', '/api/vision/optical-flow', { formData: form, options }) as Promise<OpticalFlowResult>;
  }

  /** Extract text via OCR. */
  async ocr(file: Blob | FormData, options?: RequestOptions): Promise<OCRResult> {
    const form = file instanceof FormData ? file : this._buildForm(file);
    return this._request('POST', '/api/vision/ocr', { formData: form, options }) as Promise<OCRResult>;
  }

  /** Frame differencing for motion detection. */
  async frameDiff(file: Blob | FormData, options?: RequestOptions): Promise<FrameDiffResult> {
    const form = file instanceof FormData ? file : this._buildForm(file);
    return this._request('POST', '/api/vision/frame-diff', { formData: form, options }) as Promise<FrameDiffResult>;
  }

  /** Analyze a screen capture. */
  async screenAnalyze(file: Blob | FormData, options?: RequestOptions): Promise<ScreenAnalyzeResult> {
    const form = file instanceof FormData ? file : this._buildForm(file);
    return this._request('POST', '/api/vision/screen-analyze', { formData: form, options }) as Promise<ScreenAnalyzeResult>;
  }

  /** Generate confusion matrix and quality reports. */
  async errorAnalysis(body: Record<string, unknown>, options?: RequestOptions): Promise<ErrorAnalysisResult> {
    return this._request('POST', '/api/vision/error-analysis', { body, options }) as Promise<ErrorAnalysisResult>;
  }

  private _buildForm(file: Blob): FormData {
    const form = new FormData();
    form.append('file', file);
    return form;
  }
}
