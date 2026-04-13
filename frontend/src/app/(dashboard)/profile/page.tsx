"use client";

import { useState, useEffect } from "react";
import api from "@/lib/api";

interface ProfileActivity {
  tasks_completed: number;
  assets_uploaded: number;
  pipelines_created: number;
  reviews_completed: number;
}

interface Profile {
  id: string;
  email: string;
  display_name: string;
  bio: string;
  role: string;
  avatar_url: string | null;
  member_since: string;
  activity: ProfileActivity;
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [bio, setBio] = useState("");
  const [saving, setSaving] = useState<"name" | "bio" | null>(null);

  useEffect(() => {
    api.get("/api/profile").then((res) => {
      setProfile(res.data);
      setDisplayName(res.data.display_name);
      setBio(res.data.bio);
    });
  }, []);

  const saveName = async () => {
    setSaving("name");
    try {
      const res = await api.patch("/api/profile", { display_name: displayName });
      setProfile(res.data);
    } finally {
      setSaving(null);
    }
  };

  const saveBio = async () => {
    setSaving("bio");
    try {
      const res = await api.patch("/api/profile", { bio });
      setProfile(res.data);
    } finally {
      setSaving(null);
    }
  };

  const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    const res = await api.post("/api/profile/avatar", form);
    setProfile((p) => (p ? { ...p, avatar_url: res.data.avatar_url } : p));
  };

  if (!profile) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-4 border-brand-600 border-t-transparent rounded-full" />
      </div>
    );
  }

  const initial = profile.display_name?.charAt(0).toUpperCase() || "U";
  const memberDate = new Date(profile.member_since).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  const activityCards = [
    { label: "Tasks Completed", value: profile.activity.tasks_completed },
    { label: "Assets Uploaded", value: profile.activity.assets_uploaded },
    { label: "Pipelines Created", value: profile.activity.pipelines_created },
    { label: "Reviews Completed", value: profile.activity.reviews_completed },
  ];

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <h1 className="text-2xl font-bold text-gray-900">My Profile</h1>

      {/* Avatar Section */}
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <div className="flex items-center gap-6">
          <div className="relative">
            {profile.avatar_url ? (
              <img
                src={profile.avatar_url}
                alt="Avatar"
                className="h-20 w-20 rounded-full object-cover"
              />
            ) : (
              <div className="h-20 w-20 rounded-full bg-brand-600 flex items-center justify-center text-white text-2xl font-bold">
                {initial}
              </div>
            )}
          </div>
          <div>
            <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
              Change Avatar
              <input
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleAvatarChange}
              />
            </label>
          </div>
        </div>
      </div>

      {/* Display Name */}
      <div className="rounded-lg border border-gray-200 bg-white p-6 space-y-3">
        <label className="block text-sm font-medium text-gray-700">
          Display Name
        </label>
        <div className="flex gap-3">
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
          <button
            onClick={saveName}
            disabled={saving === "name"}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {saving === "name" ? "Saving..." : "Save"}
          </button>
        </div>
      </div>

      {/* Email (read-only) */}
      <div className="rounded-lg border border-gray-200 bg-white p-6 space-y-3">
        <label className="block text-sm font-medium text-gray-700">Email</label>
        <input
          type="email"
          value={profile.email}
          readOnly
          className="w-full rounded-lg border border-gray-200 bg-gray-50 px-4 py-2 text-sm text-gray-500 cursor-not-allowed"
        />
      </div>

      {/* Bio */}
      <div className="rounded-lg border border-gray-200 bg-white p-6 space-y-3">
        <label className="block text-sm font-medium text-gray-700">Bio</label>
        <textarea
          value={bio}
          onChange={(e) => setBio(e.target.value)}
          rows={3}
          className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          placeholder="Tell us about yourself..."
        />
        <button
          onClick={saveBio}
          disabled={saving === "bio"}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {saving === "bio" ? "Saving..." : "Save"}
        </button>
      </div>

      {/* Role + Member Since */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="rounded-lg border border-gray-200 bg-white p-6 space-y-2">
          <p className="text-sm font-medium text-gray-700">Role</p>
          <span className="inline-block rounded-full bg-brand-100 px-3 py-1 text-xs font-semibold text-brand-700 capitalize">
            {profile.role}
          </span>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-6 space-y-2">
          <p className="text-sm font-medium text-gray-700">Member Since</p>
          <p className="text-sm text-gray-900">{memberDate}</p>
        </div>
      </div>

      {/* Activity Summary */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Activity Summary
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {activityCards.map((card) => (
            <div
              key={card.label}
              className="rounded-lg border border-gray-200 bg-white p-4 text-center"
            >
              <p className="text-2xl font-bold text-brand-600">{card.value}</p>
              <p className="mt-1 text-xs text-gray-500">{card.label}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
