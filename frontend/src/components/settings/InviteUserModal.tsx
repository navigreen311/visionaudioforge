'use client';

import React, { useState } from 'react';
import Modal from '@/components/ui/Modal';
import Button from '@/components/ui/Button';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type UserRole = 'admin' | 'operator' | 'analyst' | 'viewer';

interface InviteUserModalProps {
  isOpen: boolean;
  onClose: () => void;
  onInvited: () => void;
}

/* ------------------------------------------------------------------ */
/*  Role metadata                                                      */
/* ------------------------------------------------------------------ */

interface RoleOption {
  value: UserRole;
  label: string;
  description: string;
  color: string;
  selectedColor: string;
}

const ROLES: RoleOption[] = [
  {
    value: 'admin',
    label: 'Admin',
    description: 'Full access. Manage users, settings, and all resources.',
    color: 'border-gray-200 hover:border-red-300',
    selectedColor: 'border-red-500 bg-red-50 ring-1 ring-red-500',
  },
  {
    value: 'operator',
    label: 'Editor',
    description: 'Create and edit assets, manage integrations, run pipelines.',
    color: 'border-gray-200 hover:border-amber-300',
    selectedColor: 'border-amber-500 bg-amber-50 ring-1 ring-amber-500',
  },
  {
    value: 'analyst',
    label: 'Analyst',
    description: 'View dashboards, run pipelines, and export reports.',
    color: 'border-gray-200 hover:border-blue-300',
    selectedColor: 'border-blue-500 bg-blue-50 ring-1 ring-blue-500',
  },
  {
    value: 'viewer',
    label: 'Viewer',
    description: 'Read-only access to dashboards and reports.',
    color: 'border-gray-200 hover:border-gray-400',
    selectedColor: 'border-gray-500 bg-gray-50 ring-1 ring-gray-500',
  },
];

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function InviteUserModal({ isOpen, onClose, onInvited }: InviteUserModalProps) {
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<UserRole>('viewer');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const resetForm = () => {
    setEmail('');
    setRole('viewer');
    setError(null);
    setSuccess(false);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleSubmit = async () => {
    if (!email.trim()) {
      setError('Email is required.');
      return;
    }

    // Basic email validation
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      setError('Please enter a valid email address.');
      return;
    }

    try {
      setSending(true);
      setError(null);

      const res = await fetch('/api/settings/users/invite', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim(), role }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(
          body?.detail ?? `Failed to send invite (${res.status})`,
        );
      }

      setSuccess(true);
      onInvited();

      // Auto-close after brief success message
      setTimeout(() => {
        handleClose();
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send invite.');
    } finally {
      setSending(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Invite User"
      footer={
        <>
          <Button variant="secondary" onClick={handleClose} disabled={sending}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} loading={sending} disabled={success}>
            {success ? 'Invite Sent!' : 'Send Invite'}
          </Button>
        </>
      }
    >
      <div className="space-y-5">
        {/* Email */}
        <div>
          <label
            htmlFor="invite-email"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Email Address
          </label>
          <input
            id="invite-email"
            type="email"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              setError(null);
            }}
            placeholder="colleague@company.com"
            className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            disabled={sending || success}
          />
        </div>

        {/* Role selector */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Role
          </label>
          <div className="grid grid-cols-2 gap-3">
            {ROLES.map((r) => (
              <button
                key={r.value}
                type="button"
                onClick={() => setRole(r.value)}
                disabled={sending || success}
                className={`rounded-lg border-2 p-3 text-left transition-all ${
                  role === r.value ? r.selectedColor : r.color
                } disabled:opacity-60`}
              >
                <span className="block text-sm font-semibold text-gray-900">
                  {r.label}
                </span>
                <span className="block text-xs text-gray-500 mt-0.5">
                  {r.description}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Success */}
        {success && (
          <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-700">
            Invitation sent to <strong>{email}</strong>. They will appear as Pending.
          </div>
        )}
      </div>
    </Modal>
  );
}
