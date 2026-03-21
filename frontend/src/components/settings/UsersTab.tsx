'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import DataTable, { Column } from '@/components/ui/DataTable';
import EmptyState from '@/components/ui/EmptyState';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import InviteUserModal from './InviteUserModal';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type UserRole = 'admin' | 'operator' | 'analyst' | 'viewer';
type UserStatus = 'active' | 'pending' | 'inactive';

interface WorkspaceUser {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  status: UserStatus;
  avatar_url: string | null;
  last_active: string | null;
}

/* ------------------------------------------------------------------ */
/*  Role display helpers                                               */
/* ------------------------------------------------------------------ */

const ROLE_DISPLAY: Record<UserRole, string> = {
  admin: 'Admin',
  operator: 'Editor',
  analyst: 'Analyst',
  viewer: 'Viewer',
};

const ROLE_VARIANT: Record<UserRole, string> = {
  admin: 'danger',
  operator: 'warning',
  analyst: 'info',
  viewer: 'neutral',
};

const STATUS_DOT: Record<UserStatus, string> = {
  active: 'bg-green-500',
  pending: 'bg-yellow-500',
  inactive: 'bg-gray-400',
};

const STATUS_LABEL: Record<UserStatus, string> = {
  active: 'Active',
  pending: 'Pending',
  inactive: 'Inactive',
};

/* ------------------------------------------------------------------ */
/*  Role permissions reference                                         */
/* ------------------------------------------------------------------ */

interface PermissionRow {
  permission: string;
  admin: boolean;
  operator: boolean;
  analyst: boolean;
  viewer: boolean;
}

const PERMISSIONS: PermissionRow[] = [
  { permission: 'View dashboards & reports', admin: true, operator: true, analyst: true, viewer: true },
  { permission: 'Run pipelines', admin: true, operator: true, analyst: true, viewer: false },
  { permission: 'Create & edit assets', admin: true, operator: true, analyst: false, viewer: false },
  { permission: 'Manage integrations', admin: true, operator: true, analyst: false, viewer: false },
  { permission: 'Invite & remove users', admin: true, operator: false, analyst: false, viewer: false },
  { permission: 'Change user roles', admin: true, operator: false, analyst: false, viewer: false },
  { permission: 'Workspace settings', admin: true, operator: false, analyst: false, viewer: false },
];

function PermissionsTable() {
  const [open, setOpen] = useState(false);

  const check = (v: boolean) =>
    v ? (
      <svg className="h-4 w-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
      </svg>
    ) : (
      <svg className="h-4 w-4 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
      </svg>
    );

  return (
    <div className="mt-4">
      <button
        onClick={() => setOpen((p) => !p)}
        className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 transition-colors"
      >
        <svg
          className={`h-4 w-4 transition-transform ${open ? 'rotate-90' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        Role permissions reference
      </button>

      {open && (
        <div className="mt-3 overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left font-medium text-gray-500">Permission</th>
                <th className="px-4 py-2 text-center font-medium text-red-700">Admin</th>
                <th className="px-4 py-2 text-center font-medium text-amber-700">Editor</th>
                <th className="px-4 py-2 text-center font-medium text-blue-700">Analyst</th>
                <th className="px-4 py-2 text-center font-medium text-gray-600">Viewer</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {PERMISSIONS.map((row) => (
                <tr key={row.permission}>
                  <td className="px-4 py-2 text-gray-700">{row.permission}</td>
                  <td className="px-4 py-2 text-center">{check(row.admin)}</td>
                  <td className="px-4 py-2 text-center">{check(row.operator)}</td>
                  <td className="px-4 py-2 text-center">{check(row.analyst)}</td>
                  <td className="px-4 py-2 text-center">{check(row.viewer)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Role edit dropdown                                                 */
/* ------------------------------------------------------------------ */

interface RoleDropdownProps {
  currentRole: UserRole;
  onSelect: (role: UserRole) => void;
  disabled: boolean;
}

function RoleDropdown({ currentRole, onSelect, disabled }: RoleDropdownProps) {
  const [open, setOpen] = useState(false);
  const roles: UserRole[] = ['admin', 'operator', 'analyst', 'viewer'];

  return (
    <div className="relative">
      <Button
        variant="ghost"
        size="sm"
        disabled={disabled}
        onClick={() => setOpen((p) => !p)}
      >
        Edit Role
      </Button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-50 mt-1 w-36 rounded-lg border border-gray-200 bg-white shadow-lg py-1">
            {roles.map((role) => (
              <button
                key={role}
                className={`w-full px-4 py-2 text-left text-sm hover:bg-gray-50 ${
                  role === currentRole ? 'font-semibold text-brand-600' : 'text-gray-700'
                }`}
                onClick={() => {
                  onSelect(role);
                  setOpen(false);
                }}
              >
                {ROLE_DISPLAY[role]}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Confirm remove dialog                                              */
/* ------------------------------------------------------------------ */

interface ConfirmRemoveProps {
  user: WorkspaceUser;
  onConfirm: () => void;
  onCancel: () => void;
}

function ConfirmRemoveInline({ user, onConfirm, onCancel }: ConfirmRemoveProps) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-red-600">Remove {user.name || user.email}?</span>
      <Button variant="danger" size="sm" onClick={onConfirm}>
        Yes
      </Button>
      <Button variant="ghost" size="sm" onClick={onCancel}>
        No
      </Button>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  UsersTab                                                           */
/* ------------------------------------------------------------------ */

export default function UsersTab() {
  const [users, setUsers] = useState<WorkspaceUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [confirmRemoveId, setConfirmRemoveId] = useState<string | null>(null);

  // ASSUMPTION: current user id comes from /api/auth/me — stored in local state for now
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);

  /* ---- Fetch current user ---- */
  useEffect(() => {
    fetch('/api/auth/me')
      .then((r) => r.json())
      .then((data: { id: string }) => setCurrentUserId(data.id))
      .catch(() => {
        /* fail silently — worst case the row won't be disabled */
      });
  }, []);

  /* ---- Fetch users ---- */
  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch('/api/settings/users');
      if (!res.ok) throw new Error(`Failed to load users (${res.status})`);
      const data: WorkspaceUser[] = await res.json();
      setUsers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  /* ---- Change role ---- */
  const handleRoleChange = async (userId: string, role: UserRole) => {
    try {
      const res = await fetch(`/api/settings/users/${userId}/role`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role }),
      });
      if (!res.ok) throw new Error('Failed to update role');
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, role } : u)),
      );
    } catch {
      setError('Failed to update role. Please try again.');
    }
  };

  /* ---- Remove user ---- */
  const handleRemove = async (userId: string) => {
    try {
      const res = await fetch(`/api/settings/users/${userId}`, {
        method: 'DELETE',
      });
      if (!res.ok) throw new Error('Failed to remove user');
      setUsers((prev) => prev.filter((u) => u.id !== userId));
      setConfirmRemoveId(null);
    } catch {
      setError('Failed to remove user. Please try again.');
    }
  };

  /* ---- Resend invite ---- */
  const handleResend = async (userId: string) => {
    try {
      await fetch(`/api/settings/users/${userId}/resend`, { method: 'POST' });
    } catch {
      setError('Failed to resend invite.');
    }
  };

  /* ---- Avatar helper ---- */
  const renderAvatar = (user: WorkspaceUser) => {
    const initials = (user.name || user.email)
      .split(/[\s@]/)
      .slice(0, 2)
      .map((s) => s[0]?.toUpperCase() ?? '')
      .join('');

    return (
      <div className="flex items-center gap-3">
        {user.avatar_url ? (
          <img
            src={user.avatar_url}
            alt={user.name}
            className="h-8 w-8 rounded-full object-cover"
          />
        ) : (
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-200 text-xs font-medium text-gray-600">
            {initials}
          </div>
        )}
        <span className="font-medium text-gray-900">
          {user.name || user.email.split('@')[0]}
        </span>
      </div>
    );
  };

  /* ---- Columns ---- */
  const columns: Column<WorkspaceUser>[] = [
    {
      key: 'name',
      label: 'User',
      sortable: true,
      render: (_v, row) => renderAvatar(row),
    },
    {
      key: 'email',
      label: 'Email',
      sortable: true,
    },
    {
      key: 'role',
      label: 'Role',
      sortable: true,
      render: (v) => {
        const role = v as UserRole;
        return <Badge variant={ROLE_VARIANT[role]}>{ROLE_DISPLAY[role]}</Badge>;
      },
    },
    {
      key: 'status',
      label: 'Status',
      sortable: true,
      render: (v) => {
        const st = v as UserStatus;
        return (
          <span className="inline-flex items-center gap-2 text-sm">
            <span className={`inline-block h-2 w-2 rounded-full ${STATUS_DOT[st]}`} />
            {STATUS_LABEL[st]}
          </span>
        );
      },
    },
    {
      key: 'last_active',
      label: 'Last Active',
      sortable: true,
      render: (v) => (
        <span className="text-gray-500">{v ? String(v) : 'Never'}</span>
      ),
    },
    {
      key: 'id',
      label: 'Actions',
      render: (_v, row) => {
        const isSelf = row.id === currentUserId;
        const isPending = row.status === 'pending';

        if (confirmRemoveId === row.id) {
          return (
            <ConfirmRemoveInline
              user={row}
              onConfirm={() => handleRemove(row.id)}
              onCancel={() => setConfirmRemoveId(null)}
            />
          );
        }

        return (
          <div className="flex items-center gap-2">
            {isPending && (
              <Button variant="ghost" size="sm" onClick={() => handleResend(row.id)}>
                Resend
              </Button>
            )}
            <RoleDropdown
              currentRole={row.role}
              onSelect={(role) => handleRoleChange(row.id, role)}
              disabled={isSelf}
            />
            <Button
              variant="danger"
              size="sm"
              disabled={isSelf}
              onClick={() => setConfirmRemoveId(row.id)}
            >
              Remove
            </Button>
          </div>
        );
      },
    },
  ];

  /* ---- Render ---- */
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold text-gray-900">Users</h3>
        <Button onClick={() => setInviteOpen(true)}>Invite User</Button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
          <button
            className="ml-2 underline hover:no-underline"
            onClick={() => setError(null)}
          >
            Dismiss
          </button>
        </div>
      )}

      {users.length === 0 ? (
        <Card>
          <EmptyState
            title="No users yet"
            description="Invite team members to collaborate in your workspace."
            action={{
              label: 'Invite User',
              onClick: () => setInviteOpen(true),
            }}
          />
        </Card>
      ) : (
        <Card>
          <DataTable columns={columns} data={users} />
        </Card>
      )}

      <PermissionsTable />

      <InviteUserModal
        isOpen={inviteOpen}
        onClose={() => setInviteOpen(false)}
        onInvited={fetchUsers}
      />
    </div>
  );
}
