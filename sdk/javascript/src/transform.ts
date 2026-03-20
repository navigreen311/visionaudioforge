import type {
  AudioTransformRequest,
  AudioTransformResult,
  VideoTransformRequest,
  VideoTransformResult,
  RequestOptions,
} from './types';

type RequestFn = (
  method: string,
  path: string,
  options?: { body?: unknown; formData?: FormData; options?: RequestOptions },
) => Promise<unknown>;

/**
 * Client for audio and video transform endpoints.
 */
export class TransformClient {
  constructor(private readonly _request: RequestFn) {}

  // ─── Audio Transforms ──────────────────────────────────────────────

  /** Denoise audio. */
  async audioDenoise(file: Blob | FormData, params?: Record<string, unknown>, options?: RequestOptions): Promise<AudioTransformResult> {
    const form = file instanceof FormData ? file : this._buildForm(file, params);
    return this._request('POST', '/api/transform/audio/denoise', { formData: form, options }) as Promise<AudioTransformResult>;
  }

  /** Remove silence from audio. */
  async audioSilenceRemove(file: Blob | FormData, params?: Record<string, unknown>, options?: RequestOptions): Promise<AudioTransformResult> {
    const form = file instanceof FormData ? file : this._buildForm(file, params);
    return this._request('POST', '/api/transform/audio/silence-remove', { formData: form, options }) as Promise<AudioTransformResult>;
  }

  /** Pitch shift audio. */
  async audioPitchShift(file: Blob | FormData, params?: Record<string, unknown>, options?: RequestOptions): Promise<AudioTransformResult> {
    const form = file instanceof FormData ? file : this._buildForm(file, params);
    return this._request('POST', '/api/transform/audio/pitch-shift', { formData: form, options }) as Promise<AudioTransformResult>;
  }

  /** Time stretch audio. */
  async audioTimeStretch(file: Blob | FormData, params?: Record<string, unknown>, options?: RequestOptions): Promise<AudioTransformResult> {
    const form = file instanceof FormData ? file : this._buildForm(file, params);
    return this._request('POST', '/api/transform/audio/time-stretch', { formData: form, options }) as Promise<AudioTransformResult>;
  }

  /** Apply EQ preset to audio. */
  async audioEq(file: Blob | FormData, params?: Record<string, unknown>, options?: RequestOptions): Promise<AudioTransformResult> {
    const form = file instanceof FormData ? file : this._buildForm(file, params);
    return this._request('POST', '/api/transform/audio/eq', { formData: form, options }) as Promise<AudioTransformResult>;
  }

  /** Run a composable audio transform chain. */
  async audioChain(file: Blob | FormData, chain: AudioTransformRequest[], options?: RequestOptions): Promise<AudioTransformResult> {
    const form = file instanceof FormData ? file : this._buildForm(file);
    form.append('chain', JSON.stringify(chain));
    return this._request('POST', '/api/transform/audio/chain', { formData: form, options }) as Promise<AudioTransformResult>;
  }

  /** Generic audio transform (dispatches by operation name). */
  async audioTransform(operation: string, file: Blob | FormData, params?: Record<string, unknown>, options?: RequestOptions): Promise<AudioTransformResult> {
    const form = file instanceof FormData ? file : this._buildForm(file, params);
    return this._request('POST', `/api/transform/audio/${operation}`, { formData: form, options }) as Promise<AudioTransformResult>;
  }

  // ─── Video Transforms ──────────────────────────────────────────────

  /** Remove video background. */
  async videoBackgroundRemove(file: Blob | FormData, params?: Record<string, unknown>, options?: RequestOptions): Promise<VideoTransformResult> {
    const form = file instanceof FormData ? file : this._buildForm(file, params);
    return this._request('POST', '/api/transform/video/background-remove', { formData: form, options }) as Promise<VideoTransformResult>;
  }

  /** Upscale video with super-resolution. */
  async videoSuperResolution(file: Blob | FormData, params?: Record<string, unknown>, options?: RequestOptions): Promise<VideoTransformResult> {
    const form = file instanceof FormData ? file : this._buildForm(file, params);
    return this._request('POST', '/api/transform/video/super-resolution', { formData: form, options }) as Promise<VideoTransformResult>;
  }

  /** Apply style transfer to video. */
  async videoStyle(file: Blob | FormData, params?: Record<string, unknown>, options?: RequestOptions): Promise<VideoTransformResult> {
    const form = file instanceof FormData ? file : this._buildForm(file, params);
    return this._request('POST', '/api/transform/video/style', { formData: form, options }) as Promise<VideoTransformResult>;
  }

  /** Auto crop video. */
  async videoAutoCrop(file: Blob | FormData, params?: Record<string, unknown>, options?: RequestOptions): Promise<VideoTransformResult> {
    const form = file instanceof FormData ? file : this._buildForm(file, params);
    return this._request('POST', '/api/transform/video/auto-crop', { formData: form, options }) as Promise<VideoTransformResult>;
  }

  /** Generate video thumbnail. */
  async videoThumbnail(file: Blob | FormData, params?: Record<string, unknown>, options?: RequestOptions): Promise<VideoTransformResult> {
    const form = file instanceof FormData ? file : this._buildForm(file, params);
    return this._request('POST', '/api/transform/video/thumbnail', { formData: form, options }) as Promise<VideoTransformResult>;
  }

  /** Generic video transform (dispatches by operation name). */
  async videoTransform(operation: string, file: Blob | FormData, params?: Record<string, unknown>, options?: RequestOptions): Promise<VideoTransformResult> {
    const form = file instanceof FormData ? file : this._buildForm(file, params);
    return this._request('POST', `/api/transform/video/${operation}`, { formData: form, options }) as Promise<VideoTransformResult>;
  }

  private _buildForm(file: Blob, params?: Record<string, unknown>): FormData {
    const form = new FormData();
    form.append('file', file);
    if (params) {
      form.append('params', JSON.stringify(params));
    }
    return form;
  }
}
