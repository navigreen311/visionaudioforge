/**
 * What each transform mode is called, and where its control values go.
 *
 * The transform page had three separate ideas of what a mode is called and no
 * one place that reconciled them, which cost the video tab all of its controls:
 *
 *  - the page names modes in kebab-case ("background-remove")
 *  - `OperationControls` keys its panel map in snake_case ("background_remove")
 *  - the API's routes are kebab again, but its form fields are snake ("target_size")
 *
 * So `<OperationControls operation={mode} />` looked up "background-remove" in a
 * map that had "background_remove", missed on every one of the ten modes, and
 * rendered its own fallback: an amber box reading "No controls available for
 * operation background-remove". Because that fallback is a real component
 * rendering real markup, nothing was broken from the code's point of view - the
 * page just had no controls on it, on every mode, in production.
 *
 * The second half of the same problem: the panels emit camelCase keys
 * (`scaleFactor`), the API takes snake (`scale`), and the page collected the
 * emitted params into state it then discarded with `void operationParams;`. So
 * even had the panels rendered, moving a slider would have changed nothing.
 *
 * One table now owns all three vocabularies. `forwards` maps an emitted key to
 * the form field it becomes; `notYetApplied` names the emitted keys the API has
 * no parameter for, so the page can say so rather than dropping them silently.
 * A control the server cannot honour is worse than a missing one: it reports
 * success and changes nothing.
 */

export type VideoMode =
  | "background-remove"
  | "super-resolution"
  | "style"
  | "auto-crop"
  | "color-grade"
  | "subtitle"
  | "inpaint"
  | "smart-crop"
  | "interpolate"
  | "highlight";

export interface ModeSpec {
  /** The key `OperationControls` uses for this mode's panel. */
  controlKey: string;
  /** Emitted param key -> the API form field it becomes. */
  forwards: Record<string, string>;
  /**
   * Emitted keys the endpoint has no parameter for, with the label to show.
   *
   * These are not bugs in the panels - they are settings the image pipeline has
   * not implemented. Listing them keeps the gap visible instead of letting a
   * dead slider look live.
   */
  notYetApplied: Record<string, string>;
}

export const MODE_SPECS: Record<VideoMode, ModeSpec> = {
  "background-remove": {
    controlKey: "background_remove",
    forwards: { method: "method" },
    notYetApplied: {
      edgeRefinement: "Edge refinement",
      outputFormat: "Output format",
      customColor: "Custom matte colour",
    },
  },
  "super-resolution": {
    controlKey: "super_resolution",
    forwards: { scaleFactor: "scale" },
    notYetApplied: {
      model: "Upscaler model",
      denoise: "Denoise",
      faceEnhancement: "Face enhancement",
    },
  },
  style: {
    controlKey: "style_transfer",
    forwards: { selectedStyle: "style" },
    notYetApplied: {
      styleStrength: "Style strength",
      contentWeight: "Content weight",
      preserveColors: "Preserve colours",
    },
  },
  "auto-crop": {
    controlKey: "auto_crop",
    forwards: { aspectRatio: "aspect" },
    notYetApplied: {
      subjectFocus: "Subject focus",
      padding: "Padding",
      minWidth: "Minimum width",
      minHeight: "Minimum height",
    },
  },
  "color-grade": {
    controlKey: "color_grade",
    forwards: { lutPreset: "preset" },
    notYetApplied: {
      brightness: "Brightness",
      contrast: "Contrast",
      saturation: "Saturation",
      hueShift: "Hue shift",
    },
  },
  subtitle: {
    controlKey: "subtitle",
    forwards: { text: "text", position: "position", fontSize: "font_scale" },
    notYetApplied: {
      font: "Font family",
      color: "Text colour",
      outline: "Outline",
    },
  },
  inpaint: {
    controlKey: "inpaint",
    // `maskFile` is a File, not a form value - the page appends it separately.
    forwards: {},
    notYetApplied: {
      inpaintRadius: "Inpaint radius",
      prompt: "Text prompt",
    },
  },
  "smart-crop": {
    controlKey: "smart_crop",
    forwards: {},
    notYetApplied: {
      aspectRatio: "Aspect ratio",
      subjectFocus: "Subject focus",
      padding: "Padding",
      minWidth: "Minimum width",
      minHeight: "Minimum height",
      aiFocusPoint: "AI focus point",
      showFocusPoint: "Show focus point",
    },
  },
  interpolate: {
    controlKey: "frame_interpolate",
    forwards: { targetFps: "count" },
    notYetApplied: { inputFps: "Input frame rate", method: "Interpolation method" },
  },
  highlight: {
    controlKey: "highlight_clip",
    forwards: { duration: "top_k" },
    notYetApplied: { detection: "Detection model", outputFormat: "Output format" },
  },
};

/** The panel key for a mode, or the mode itself if it is already one. */
export function controlKeyFor(mode: string): string {
  return MODE_SPECS[mode as VideoMode]?.controlKey ?? mode;
}

/**
 * The form fields a mode's emitted params become.
 *
 * Only keys the endpoint accepts are returned. Booleans become "true"/"false"
 * and numbers are stringified, because `FormData` carries strings and FastAPI
 * coerces from them; `undefined` and `null` are dropped so an untouched control
 * does not overwrite an endpoint default with an empty string.
 */
export function toFormFields(
  mode: string,
  params: Record<string, unknown>,
): Record<string, string> {
  const spec = MODE_SPECS[mode as VideoMode];
  if (!spec) return {};

  const fields: Record<string, string> = {};
  for (const [emitted, field] of Object.entries(spec.forwards)) {
    const value = params[emitted];
    if (value === undefined || value === null || value === "") continue;
    fields[field] = typeof value === "boolean" ? String(value) : String(value);
  }
  return fields;
}

/**
 * Labels for the settings this mode's panel offers that the API cannot apply.
 *
 * Only those actually present in *params*, so the notice reflects the panel on
 * screen rather than the table's full pessimism.
 */
export function unappliedLabels(
  mode: string,
  params: Record<string, unknown>,
): string[] {
  const spec = MODE_SPECS[mode as VideoMode];
  if (!spec) return [];
  return Object.entries(spec.notYetApplied)
    .filter(([key]) => key in params)
    .map(([, label]) => label);
}
