import Link from "next/link";

const quickLinks = [
  { label: "Dashboard", href: "/" },
  { label: "Capture", href: "/capture" },
  { label: "Vision", href: "/vision" },
  { label: "Audio", href: "/audio" },
  { label: "Agents", href: "/agents" },
];

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 text-center">
      <h1 className="text-2xl font-bold text-gray-900">VisionAudioForge</h1>
      <p className="mt-6 text-8xl font-extrabold text-gray-300">404</p>
      <p className="mt-4 text-lg text-gray-600">Page not found</p>
      <Link
        href="/"
        className="mt-8 rounded-lg bg-blue-600 px-6 py-3 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
      >
        Go to Dashboard
      </Link>
      <div className="mt-10">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-400">
          Quick links
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          {quickLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="rounded-md border border-gray-200 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
            >
              {link.label}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
