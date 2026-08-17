"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Button from "@/components/ui/Button";
import { useAuthStore } from "@/stores/auth";

/**
 * Where to land after signing in.
 *
 * `src/middleware.ts` puts the page the visitor originally asked for in a
 * `next` query parameter. Only same-origin *paths* are honoured — an absolute
 * URL here would turn the login form into an open redirect, which is a
 * ready-made phishing hop.
 *
 * Read from `location` rather than `useSearchParams` so this page does not
 * need a Suspense boundary at build time.
 */
function resolveDestination(): string {
  if (typeof window === "undefined") return "/";
  const next = new URLSearchParams(window.location.search).get("next");
  if (!next) return "/";
  if (!next.startsWith("/") || next.startsWith("//")) return "/";
  return next;
}

export default function LoginPage() {
  const router = useRouter();
  const login = useAuthStore((s) => s.login);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      router.replace(resolveDestination());
    } catch (err: unknown) {
      // Never surface the server's message verbatim: on a bad password the
      // backend says "Invalid email or password", which is right, but an
      // unexpected 500 would otherwise put backend detail on the login screen.
      const status =
        typeof err === "object" && err !== null
          ? (err as { response?: { status?: number } }).response?.status
          : undefined;
      setError(
        status === 401
          ? "Invalid email or password."
          : "Login failed. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md rounded-lg border border-gray-200 bg-white p-8 shadow-sm">
        {/* Logo */}
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-bold text-brand-900">VisionAudioForge</h1>
          <p className="mt-1 text-sm text-gray-500">
            AI-powered vision and audio platform
          </p>
        </div>

        <h2 className="mb-6 text-xl font-semibold text-gray-900 text-center">
          Sign In
        </h2>

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              placeholder="Enter your password"
            />
          </div>

          <Button
            type="submit"
            variant="primary"
            size="lg"
            loading={loading}
            className="w-full"
          >
            Sign In
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-500">
          Don&apos;t have an account?{" "}
          <Link href="/register" className="text-brand-600 hover:text-brand-700 font-medium">
            Register
          </Link>
        </p>
      </div>
    </div>
  );
}
