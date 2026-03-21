"use client";

import { useState, useCallback, useRef } from "react";
import api from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface RTSPTestResponse {
  success: boolean;
  latency_ms: number;
}

interface ConnectionLogEntry {
  id: number;
  timestamp: string;
  message: string;
  type: "info" | "success" | "error";
}

interface RTSPConnectPanelProps {
  onConnect?: (url: string) => void;
  onDisconnect?: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function RTSPConnectPanel({
  onConnect,
  onDisconnect,
}: RTSPConnectPanelProps) {
  const [url, setUrl] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [authOpen, setAuthOpen] = useState(false);

  const [testing, setTesting] = useState(false);
  const [testPassed, setTestPassed] = useState(false);
  const [testResult, setTestResult] = useState<RTSPTestResponse | null>(null);
  const [testError, setTestError] = useState<string | null>(null);

  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);

  const [log, setLog] = useState<ConnectionLogEntry[]>([]);
  const logCounterRef = useRef(0);

  // -----------------------------------------------------------------------
  // Helpers
  // -----------------------------------------------------------------------

  const addLog = useCallback(
    (message: string, type: ConnectionLogEntry["type"]) => {
      logCounterRef.current += 1;
      const entry: ConnectionLogEntry = {
        id: logCounterRef.current,
        timestamp: new Date().toLocaleTimeString(),
        message,
        type,
      };
      setLog((current) => [entry, ...current].slice(0, 5));
    },
    [],
  );

  const buildFullUrl = useCallback((): string => {
    if (!username && !password) return url;
    try {
      const parsed = new URL(url);
      if (username) parsed.username = username;
      if (password) parsed.password = password;
      return parsed.toString();
    } catch {
      return url;
    }
  }, [url, username, password]);

  // Reset test state when URL or credentials change
  const resetTest = useCallback(() => {
    setTestPassed(false);
    setTestResult(null);
    setTestError(null);
  }, []);

  const handleUrlChange = useCallback(
    (value: string) => {
      setUrl(value);
      resetTest();
    },
    [resetTest],
  );

  const handleUsernameChange = useCallback(
    (value: string) => {
      setUsername(value);
      resetTest();
    },
    [resetTest],
  );

  const handlePasswordChange = useCallback(
    (value: string) => {
      setPassword(value);
      resetTest();
    },
    [resetTest],
  );

  // -----------------------------------------------------------------------
  // Test Connection
  // -----------------------------------------------------------------------

  const handleTest = useCallback(async () => {
    setTesting(true);
    setTestResult(null);
    setTestError(null);
    setTestPassed(false);
    addLog("Testing connection...", "info");

    try {
      const fullUrl = buildFullUrl();
      const { data } = await api.get<RTSPTestResponse>(
        "/api/capture/rtsp/test",
        { params: { url: fullUrl } },
      );
      setTestResult(data);
      if (data.success) {
        setTestPassed(true);
        addLog(`Connection OK (${data.latency_ms}ms)`, "success");
      } else {
        setTestPassed(false);
        addLog("Test failed: stream unreachable", "error");
        setTestError("Stream unreachable or invalid URL");
      }
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Network error";
      setTestError(message);
      setTestPassed(false);
      addLog(`Test error: ${message}`, "error");
    } finally {
      setTesting(false);
    }
  }, [addLog, buildFullUrl]);

  // -----------------------------------------------------------------------
  // Connect / Disconnect
  // -----------------------------------------------------------------------

  const handleConnect = useCallback(() => {
    setConnecting(true);
    const fullUrl = buildFullUrl();
    addLog(`Connecting to ${url}...`, "info");

    // Small delay so the UI shows a loading state before the parent takes
    // over stream handling.
    setTimeout(() => {
      setConnected(true);
      setConnecting(false);
      addLog("Connected", "success");
      onConnect?.(fullUrl);
    }, 400);
  }, [url, addLog, buildFullUrl, onConnect]);

  const handleDisconnect = useCallback(() => {
    setConnected(false);
    setTestPassed(false);
    setTestResult(null);
    setTestError(null);
    addLog("Disconnected", "info");
    onDisconnect?.();
  }, [addLog, onDisconnect]);

  // -----------------------------------------------------------------------
  // Derived state
  // -----------------------------------------------------------------------

  const canTest = url.trim().length > 0 && !testing && !connected;
  const canConnect =
    url.trim().length > 0 && testPassed && !connected && !connecting;

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-5">
      <h3 className="text-sm font-medium text-gray-700">
        RTSP Stream Connection
      </h3>

      {/* URL input — full width */}
      <div>
        <label
          htmlFor="rtsp-url"
          className="block text-sm font-medium text-gray-700 mb-1"
        >
          RTSP Stream URL
        </label>
        <input
          id="rtsp-url"
          type="text"
          value={url}
          onChange={(e) => handleUrlChange(e.target.value)}
          placeholder="rtsp://192.168.1.100:554/stream"
          disabled={connected}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
        />
      </div>

      {/* Collapsible Authentication section */}
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <button
          type="button"
          onClick={() => setAuthOpen((v) => !v)}
          className="flex items-center justify-between w-full px-4 py-2 text-sm font-medium text-gray-700 bg-gray-50 hover:bg-gray-100 transition-colors"
        >
          <span>Authentication</span>
          <svg
            className={`w-4 h-4 transition-transform ${authOpen ? "rotate-180" : ""}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </button>

        {authOpen && (
          <div className="px-4 py-3 space-y-3 border-t border-gray-200">
            <div>
              <label
                htmlFor="rtsp-user"
                className="block text-sm font-medium text-gray-600 mb-1"
              >
                Username
              </label>
              <input
                id="rtsp-user"
                type="text"
                value={username}
                onChange={(e) => handleUsernameChange(e.target.value)}
                placeholder="admin"
                disabled={connected}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500 disabled:bg-gray-100"
              />
            </div>
            <div>
              <label
                htmlFor="rtsp-pass"
                className="block text-sm font-medium text-gray-600 mb-1"
              >
                Password
              </label>
              <input
                id="rtsp-pass"
                type="password"
                value={password}
                onChange={(e) => handlePasswordChange(e.target.value)}
                placeholder="password"
                disabled={connected}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500 disabled:bg-gray-100"
              />
            </div>
          </div>
        )}
      </div>

      {/* Test result banner */}
      {testResult && (
        <div
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm ${
            testResult.success
              ? "bg-green-50 text-green-700 border border-green-200"
              : "bg-red-50 text-red-700 border border-red-200"
          }`}
        >
          {testResult.success ? (
            <>
              <span className="font-medium">&#10003; Connected</span>
              <span className="text-green-600">
                &mdash; latency {testResult.latency_ms}ms
              </span>
            </>
          ) : (
            <>
              <span className="font-medium">&#10007; Failed</span>
              <span className="text-red-600">
                &mdash; stream unreachable
              </span>
            </>
          )}
        </div>
      )}

      {/* Error from network / catch block */}
      {testError && !testResult && (
        <div className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm bg-red-50 text-red-700 border border-red-200">
          <span className="font-medium">&#10007; Failed</span>
          <span className="text-red-600">&mdash; {testError}</span>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleTest}
          disabled={!canTest}
          className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {testing ? (
            <span className="flex items-center gap-2">
              <svg
                className="w-4 h-4 animate-spin"
                viewBox="0 0 24 24"
                fill="none"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
                />
              </svg>
              Testing...
            </span>
          ) : (
            "Test Connection"
          )}
        </button>

        {connected ? (
          <button
            onClick={handleDisconnect}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-red-600 hover:bg-red-700 text-white transition-colors"
          >
            Disconnect
          </button>
        ) : (
          <button
            onClick={handleConnect}
            disabled={!canConnect}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-brand-600 hover:bg-brand-700 text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {connecting ? (
              <span className="flex items-center gap-2">
                <svg
                  className="w-4 h-4 animate-spin"
                  viewBox="0 0 24 24"
                  fill="none"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
                  />
                </svg>
                Connecting...
              </span>
            ) : (
              "Connect"
            )}
          </button>
        )}
      </div>

      {/* Connection log — last 5 events */}
      {log.length > 0 && (
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          <div className="px-4 py-2 bg-gray-50 border-b border-gray-200">
            <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
              Connection Log
            </span>
          </div>
          <ul className="divide-y divide-gray-100 max-h-40 overflow-y-auto">
            {log.map((entry) => (
              <li
                key={entry.id}
                className="flex items-start gap-2 px-4 py-2 text-sm"
              >
                <span className="text-gray-400 font-mono text-xs pt-0.5 shrink-0">
                  {entry.timestamp}
                </span>
                <span
                  className={
                    entry.type === "success"
                      ? "text-green-700"
                      : entry.type === "error"
                        ? "text-red-700"
                        : "text-gray-700"
                  }
                >
                  {entry.message}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
