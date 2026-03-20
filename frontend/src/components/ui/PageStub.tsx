"use client";

interface PageStubProps {
  moduleName: string;
  description?: string;
}

export default function PageStub({ moduleName, description }: PageStubProps) {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="bg-white rounded-xl shadow-lg p-8 max-w-md w-full text-center border border-gray-100">
        <div className="w-16 h-16 bg-brand-50 rounded-full flex items-center justify-center mx-auto mb-4">
          <span className="text-2xl text-brand-600 font-bold">
            {moduleName.charAt(0).toUpperCase()}
          </span>
        </div>
        <h2 className="text-xl font-semibold text-gray-900 mb-2">{moduleName}</h2>
        <p className="text-gray-500">
          {description || "Module coming soon. This feature is under development."}
        </p>
        <div className="mt-4 inline-block px-3 py-1 bg-yellow-50 text-yellow-700 text-sm rounded-full border border-yellow-200">
          Not Implemented
        </div>
      </div>
    </div>
  );
}
