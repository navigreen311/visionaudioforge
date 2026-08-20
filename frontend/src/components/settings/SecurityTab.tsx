"use client";

import { API_BASE_URL } from "@/lib/api";

import React, { useCallback, useEffect, useState } from "react";
import Button from "../ui/Button";
import Card from "../ui/Card";
import Modal from "../ui/Modal";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Session {
  id: string;
  device: string;
  browser: string;
  location: string;
  ip_address: string;
  last_active: string;
  is_current: boolean;
}

interface LoginEvent {
  id: string;
  timestamp: string;
  device: string;
  browser: string;
  ip_address: string;
  location: string;
  status: "success" | "failed";
}

interface TwoFactorStatus {
  enabled: boolean;
  enabled_at: string | null;
}

type PasswordStrength = "weak" | "medium" | "strong";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const API_BASE = API_BASE_URL;

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error((body as { detail?: string }).detail ?? "Request failed");
  }
  return res.json() as Promise<T>;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString();
}

function evaluateStrength(password: string): PasswordStrength {
  let score = 0;
  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score++;
  if (/\d/.test(password)) score++;
  if (/[^A-Za-z0-9]/.test(password)) score++;
  if (score <= 2) return "weak";
  if (score <= 3) return "medium";
  return "strong";
}

const strengthConfig: Record<PasswordStrength, { color: string; width: string; label: string }> = {
  weak: { color: "bg-red-500", width: "w-1/3", label: "Weak" },
  medium: { color: "bg-yellow-500", width: "w-2/3", label: "Medium" },
  strong: { color: "bg-green-500", width: "w-full", label: "Strong" },
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function TwoFactorSection() {
  const [status, setStatus] = useState<TwoFactorStatus>({ enabled: false, enabled_at: null });
  const [showEnableModal, setShowEnableModal] = useState(false);
  const [showDisableModal, setShowDisableModal] = useState(false);
  const [qrUrl, setQrUrl] = useState("");
  const [totpCode, setTotpCode] = useState("");
  const [disablePassword, setDisablePassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchStatus = useCallback(async () => {
    try {
      const data = await apiFetch<TwoFactorStatus>("/api/security/2fa/status");
      setStatus(data);
    } catch {
      /* silent — status defaults to disabled */
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const handleEnableSetup = async () => {
    setError("");
    setLoading(true);
    try {
      const data = await apiFetch<{ qr_code_url: string }>("/api/security/2fa/enable", {
        method: "POST",
      });
      setQrUrl(data.qr_code_url);
      setShowEnableModal(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start 2FA setup");
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async () => {
    setError("");
    setLoading(true);
    try {
      await apiFetch("/api/security/2fa/verify", {
        method: "POST",
        body: JSON.stringify({ code: totpCode }),
      });
      setShowEnableModal(false);
      setTotpCode("");
      await fetchStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed");
    } finally {
      setLoading(false);
    }
  };

  const handleDisable = async () => {
    setError("");
    setLoading(true);
    try {
      await apiFetch("/api/security/2fa/disable", {
        method: "POST",
        body: JSON.stringify({ password: disablePassword }),
      });
      setShowDisableModal(false);
      setDisablePassword("");
      await fetchStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to disable 2FA");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card title="Two-Factor Authentication">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-gray-700">Status:</span>
          {status.enabled ? (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-green-100 px-3 py-1 text-sm font-medium text-green-800">
              <span className="h-2 w-2 rounded-full bg-green-500" />
              Enabled
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-red-100 px-3 py-1 text-sm font-medium text-red-800">
              <span className="h-2 w-2 rounded-full bg-red-500" />
              Disabled
            </span>
          )}
        </div>
        {status.enabled ? (
          <Button variant="danger" size="sm" onClick={() => setShowDisableModal(true)}>
            Disable 2FA
          </Button>
        ) : (
          <Button size="sm" loading={loading} onClick={handleEnableSetup}>
            Enable 2FA
          </Button>
        )}
      </div>

      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

      {/* Enable 2FA Modal */}
      <Modal
        isOpen={showEnableModal}
        onClose={() => {
          setShowEnableModal(false);
          setTotpCode("");
          setError("");
        }}
        title="Enable Two-Factor Authentication"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowEnableModal(false)}>
              Cancel
            </Button>
            <Button loading={loading} disabled={totpCode.length !== 6} onClick={handleVerify}>
              Verify &amp; Enable
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Scan the QR code below with your authenticator app (Google Authenticator, Authy, etc.),
            then enter the 6-digit verification code.
          </p>
          {/* QR Code Placeholder */}
          <div className="flex items-center justify-center rounded-lg border-2 border-dashed border-gray-300 bg-gray-50 p-8">
            <div className="text-center">
              <svg
                className="mx-auto h-16 w-16 text-gray-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm12 0h2a1 1 0 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z"
                />
              </svg>
              <p className="mt-2 text-xs text-gray-500">QR Code Placeholder</p>
              {qrUrl && (
                <p className="mt-1 max-w-xs break-all text-xs text-gray-400">{qrUrl}</p>
              )}
            </div>
          </div>
          <div>
            <label htmlFor="totp-code" className="block text-sm font-medium text-gray-700">
              Verification Code
            </label>
            <input
              id="totp-code"
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              maxLength={6}
              value={totpCode}
              onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ""))}
              placeholder="000000"
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-center text-lg tracking-widest shadow-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>
      </Modal>

      {/* Disable 2FA Modal */}
      <Modal
        isOpen={showDisableModal}
        onClose={() => {
          setShowDisableModal(false);
          setDisablePassword("");
          setError("");
        }}
        title="Disable Two-Factor Authentication"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowDisableModal(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              loading={loading}
              disabled={!disablePassword}
              onClick={handleDisable}
            >
              Disable 2FA
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Enter your password to confirm disabling two-factor authentication. This will make your
            account less secure.
          </p>
          <div>
            <label htmlFor="disable-password" className="block text-sm font-medium text-gray-700">
              Password
            </label>
            <input
              id="disable-password"
              type="password"
              value={disablePassword}
              onChange={(e) => setDisablePassword(e.target.value)}
              placeholder="Enter your password"
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>
      </Modal>
    </Card>
  );
}

// ---------------------------------------------------------------------------

function ActiveSessionsSection() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchSessions = useCallback(async () => {
    try {
      const data = await apiFetch<{ sessions: Session[] }>("/api/security/sessions");
      setSessions(data.sessions);
    } catch {
      /* silent */
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const handleRevoke = async (id: string) => {
    setLoading(true);
    try {
      await apiFetch(`/api/security/sessions/${id}`, { method: "DELETE" });
      await fetchSessions();
    } catch {
      /* silent */
    } finally {
      setLoading(false);
    }
  };

  const handleRevokeAll = async () => {
    setLoading(true);
    try {
      await apiFetch("/api/security/sessions", { method: "DELETE" });
      await fetchSessions();
    } catch {
      /* silent */
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card
      title="Active Sessions"
      footer={
        <div className="flex justify-end">
          <Button variant="danger" size="sm" loading={loading} onClick={handleRevokeAll}>
            Revoke All Other Sessions
          </Button>
        </div>
      }
    >
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {["Device", "Browser", "Location", "IP", "Last Active", "Actions"].map((h) => (
                <th
                  key={h}
                  className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {sessions.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-500">
                  No active sessions
                </td>
              </tr>
            ) : (
              sessions.map((s) => (
                <tr
                  key={s.id}
                  className={
                    s.is_current
                      ? "bg-blue-50 border-l-4 border-l-blue-500"
                      : "hover:bg-gray-50 transition-colors"
                  }
                >
                  <td className="px-4 py-3 text-sm text-gray-900 whitespace-nowrap">
                    {s.device}
                    {s.is_current && (
                      <span className="ml-2 inline-flex rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">
                        Current
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900 whitespace-nowrap">{s.browser}</td>
                  <td className="px-4 py-3 text-sm text-gray-900 whitespace-nowrap">{s.location}</td>
                  <td className="px-4 py-3 text-sm font-mono text-gray-600 whitespace-nowrap">
                    {s.ip_address}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">
                    {formatDate(s.last_active)}
                  </td>
                  <td className="px-4 py-3 text-sm whitespace-nowrap">
                    {s.is_current ? (
                      <span className="text-xs text-gray-400">Current session</span>
                    ) : (
                      <Button
                        variant="danger"
                        size="sm"
                        loading={loading}
                        onClick={() => handleRevoke(s.id)}
                      >
                        Revoke
                      </Button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------

function LoginHistorySection() {
  const [entries, setEntries] = useState<LoginEvent[]>([]);

  useEffect(() => {
    (async () => {
      try {
        const data = await apiFetch<{ entries: LoginEvent[] }>("/api/security/login-history");
        setEntries(data.entries);
      } catch {
        /* silent */
      }
    })();
  }, []);

  return (
    <Card title="Login History">
      <p className="mb-3 text-sm text-gray-500">Last 20 login events</p>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {["Date", "Device", "Browser", "IP", "Location", "Status"].map((h) => (
                <th
                  key={h}
                  className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {entries.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-500">
                  No login history
                </td>
              </tr>
            ) : (
              entries.map((e) => (
                <tr
                  key={e.id}
                  className={
                    e.status === "failed"
                      ? "bg-red-50 border-l-4 border-l-red-400"
                      : "hover:bg-gray-50 transition-colors"
                  }
                >
                  <td className="px-4 py-3 text-sm text-gray-900 whitespace-nowrap">
                    {formatDate(e.timestamp)}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900 whitespace-nowrap">{e.device}</td>
                  <td className="px-4 py-3 text-sm text-gray-900 whitespace-nowrap">{e.browser}</td>
                  <td className="px-4 py-3 text-sm font-mono text-gray-600 whitespace-nowrap">
                    {e.ip_address}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900 whitespace-nowrap">{e.location}</td>
                  <td className="px-4 py-3 text-sm whitespace-nowrap">
                    {e.status === "success" ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800">
                        Success
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800">
                        Failed
                      </span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------

function ChangePasswordSection() {
  const [showModal, setShowModal] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const strength = evaluateStrength(newPassword);
  const cfg = strengthConfig[strength];
  const passwordsMatch = newPassword === confirmPassword;
  const canSubmit =
    currentPassword.length > 0 &&
    newPassword.length >= 8 &&
    confirmPassword.length >= 8 &&
    passwordsMatch;

  const resetForm = () => {
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
    setError("");
    setSuccess("");
  };

  const handleSubmit = async () => {
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      const data = await apiFetch<{ message: string }>("/api/security/password", {
        method: "POST",
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
          confirm_password: confirmPassword,
        }),
      });
      setSuccess(data.message);
      setTimeout(() => {
        setShowModal(false);
        resetForm();
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to change password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card title="Change Password">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-600">
          Update your password regularly to keep your account secure.
        </p>
        <Button size="sm" onClick={() => setShowModal(true)}>
          Change Password
        </Button>
      </div>

      <Modal
        isOpen={showModal}
        onClose={() => {
          setShowModal(false);
          resetForm();
        }}
        title="Change Password"
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => {
                setShowModal(false);
                resetForm();
              }}
            >
              Cancel
            </Button>
            <Button loading={loading} disabled={!canSubmit} onClick={handleSubmit}>
              Update Password
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          {/* Current Password */}
          <div>
            <label htmlFor="current-pw" className="block text-sm font-medium text-gray-700">
              Current Password
            </label>
            <input
              id="current-pw"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
            />
          </div>

          {/* New Password */}
          <div>
            <label htmlFor="new-pw" className="block text-sm font-medium text-gray-700">
              New Password
            </label>
            <input
              id="new-pw"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
            />
            {/* Strength Indicator */}
            {newPassword.length > 0 && (
              <div className="mt-2">
                <div className="h-1.5 w-full rounded-full bg-gray-200">
                  <div
                    className={`h-1.5 rounded-full transition-all ${cfg.color} ${cfg.width}`}
                  />
                </div>
                <p className={`mt-1 text-xs ${
                  strength === "weak"
                    ? "text-red-600"
                    : strength === "medium"
                      ? "text-yellow-600"
                      : "text-green-600"
                }`}>
                  Strength: {cfg.label}
                </p>
              </div>
            )}
          </div>

          {/* Confirm Password */}
          <div>
            <label htmlFor="confirm-pw" className="block text-sm font-medium text-gray-700">
              Confirm New Password
            </label>
            <input
              id="confirm-pw"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
            />
            {confirmPassword.length > 0 && !passwordsMatch && (
              <p className="mt-1 text-xs text-red-600">Passwords do not match</p>
            )}
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}
          {success && <p className="text-sm text-green-600">{success}</p>}
        </div>
      </Modal>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Main Export
// ---------------------------------------------------------------------------

export default function SecurityTab() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-900">Security</h2>
        <p className="mt-1 text-sm text-gray-500">
          Manage two-factor authentication, active sessions, and password settings.
        </p>
      </div>

      <TwoFactorSection />
      <ActiveSessionsSection />
      <LoginHistorySection />
      <ChangePasswordSection />
    </div>
  );
}
