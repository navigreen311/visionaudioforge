"use client";

import { useCallback, useEffect, useRef, useState } from "react";

// ---------------------------------------------------------------------------
// SpeechRecognition type shim (Web Speech API is not in lib.dom by default)
// ---------------------------------------------------------------------------

interface SpeechRecognitionEvent {
  resultIndex: number;
  results: SpeechRecognitionResultList;
}

interface SpeechRecognitionErrorEvent {
  error: string;
  message: string;
}

interface SpeechRecognitionInstance extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
}

type SpeechRecognitionConstructor = new () => SpeechRecognitionInstance;

function getSpeechRecognition(): SpeechRecognitionConstructor | null {
  if (typeof window === "undefined") return null;

  const win = window as unknown as Record<string, unknown>;
  return (
    (win.SpeechRecognition as SpeechRecognitionConstructor | undefined) ??
    (win.webkitSpeechRecognition as SpeechRecognitionConstructor | undefined) ??
    null
  );
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface VoiceInputProps {
  onTranscript: (text: string) => void;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MAX_LISTEN_MS = 30_000;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function VoiceInput({ onTranscript }: VoiceInputProps) {
  const [supported, setSupported] = useState(false);
  const [listening, setListening] = useState(false);

  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const transcriptRef = useRef("");

  // -----------------------------------------------------------------------
  // Feature-detect on mount
  // -----------------------------------------------------------------------

  useEffect(() => {
    setSupported(getSpeechRecognition() !== null);
  }, []);

  // -----------------------------------------------------------------------
  // Cleanup on unmount
  // -----------------------------------------------------------------------

  useEffect(() => {
    return () => {
      recognitionRef.current?.abort();
      recognitionRef.current = null;
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };
  }, []);

  // -----------------------------------------------------------------------
  // Start / stop toggle
  // -----------------------------------------------------------------------

  const stopListening = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    recognitionRef.current?.stop();
  }, []);

  const startListening = useCallback(() => {
    const Ctor = getSpeechRecognition();
    if (!Ctor) return;

    // Reset transcript accumulator
    transcriptRef.current = "";

    const recognition = new Ctor();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let transcript = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          transcript += result[0].transcript;
        }
      }
      transcriptRef.current += transcript;
    };

    recognition.onerror = () => {
      setListening(false);
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };

    recognition.onend = () => {
      setListening(false);
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
      const final = transcriptRef.current.trim();
      if (final) {
        onTranscript(final);
      }
    };

    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);

    // Auto-stop after MAX_LISTEN_MS
    timeoutRef.current = setTimeout(() => {
      stopListening();
    }, MAX_LISTEN_MS);
  }, [onTranscript, stopListening]);

  const toggle = useCallback(() => {
    if (listening) {
      stopListening();
    } else {
      startListening();
    }
  }, [listening, startListening, stopListening]);

  // -----------------------------------------------------------------------
  // Render — hidden if browser doesn't support SpeechRecognition
  // -----------------------------------------------------------------------

  if (!supported) return null;

  return (
    <button
      type="button"
      onClick={toggle}
      className={`relative flex items-center justify-center w-10 h-10 rounded-lg transition-colors ${
        listening
          ? "bg-red-100 text-red-600 hover:bg-red-200"
          : "bg-gray-50 text-gray-500 hover:bg-gray-100 hover:text-gray-700"
      }`}
      title={listening ? "Stop recording" : "Voice input"}
      aria-label={listening ? "Stop recording" : "Start voice input"}
    >
      {/* Pulsing ring when listening */}
      {listening && (
        <span className="absolute inset-0 rounded-lg border-2 border-red-400 animate-ping opacity-50" />
      )}

      {/* Mic SVG icon */}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        className="w-5 h-5 relative z-10"
      >
        <rect x="9" y="1" width="6" height="12" rx="3" />
        <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
        <line x1="12" y1="19" x2="12" y2="23" />
        <line x1="8" y1="23" x2="16" y2="23" />
      </svg>
    </button>
  );
}
