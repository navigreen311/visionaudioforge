import Link from "next/link";

export default function Home() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-brand-900 mb-4">
          VisionAudioForge
        </h1>
        <p className="text-gray-500 mb-8">
          AI-powered vision and audio analysis platform
        </p>
        <Link
          href="/"
          className="px-6 py-3 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors"
        >
          Go to Dashboard
        </Link>
      </div>
    </div>
  );
}
