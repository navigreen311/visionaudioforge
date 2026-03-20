import type {
  AudioAnalysisResult,
  AudioAugmentResult,
  TranscriptionResult,
  DiarizationResult,
  AudioClassificationResult,
  RequestOptions,
} from './types';

type RequestFn = (
  method: string,
  path: string,
  options?: { body?: unknown; formData?: FormData; options?: RequestOptions },
) => Promise<unknown>;

/**
 * Client for audio processing endpoints.
 */
export class AudioClient {
  constructor(private readonly _request: RequestFn) {}

  /** Spectral analysis of an audio file. */
  async analyze(file: Blob | FormData, options?: RequestOptions): Promise<AudioAnalysisResult> {
    const form = file instanceof FormData ? file : this._buildForm(file);
    return this._request('POST', '/api/audio/analyze', { formData: form, options }) as Promise<AudioAnalysisResult>;
  }

  /** Run audio augmentation pipeline. */
  async augment(file: Blob | FormData, params?: Record<string, unknown>, options?: RequestOptions): Promise<AudioAugmentResult> {
    const form = file instanceof FormData ? file : this._buildForm(file);
    if (params) {
      form.append('params', JSON.stringify(params));
    }
    return this._request('POST', '/api/audio/augment', { formData: form, options }) as Promise<AudioAugmentResult>;
  }

  /** Transcribe audio to text. */
  async transcribe(file: Blob | FormData, options?: RequestOptions): Promise<TranscriptionResult> {
    const form = file instanceof FormData ? file : this._buildForm(file);
    return this._request('POST', '/api/audio/transcribe', { formData: form, options }) as Promise<TranscriptionResult>;
  }

  /** Speaker diarization. */
  async diarize(file: Blob | FormData, options?: RequestOptions): Promise<DiarizationResult> {
    const form = file instanceof FormData ? file : this._buildForm(file);
    return this._request('POST', '/api/audio/diarize', { formData: form, options }) as Promise<DiarizationResult>;
  }

  /** Classify audio content. */
  async classify(file: Blob | FormData, options?: RequestOptions): Promise<AudioClassificationResult> {
    const form = file instanceof FormData ? file : this._buildForm(file);
    return this._request('POST', '/api/audio/classify', { formData: form, options }) as Promise<AudioClassificationResult>;
  }

  private _buildForm(file: Blob): FormData {
    const form = new FormData();
    form.append('file', file);
    return form;
  }
}
