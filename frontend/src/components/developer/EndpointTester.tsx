"use client";

import React, { useState } from "react";
import api, { API_BASE_URL } from "@/lib/api";

export interface EndpointDef {
  method: "GET" | "POST" | "PATCH" | "DELETE";
  path: string;
  description: string;
}

function methodColor(m: string) {
  switch (m) {
    case "GET":
      return "bg-green-100 text-green-800";
    case "POST":
      return "bg-blue-100 text-blue-800";
    case "PATCH":
      return "bg-amber-100 text-amber-800";
    case "DELETE":
      return "bg-red-100 text-red-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
}

function statusColor(code: number) {
  if (code < 300) return "bg-green-100 text-green-800";
  if (code < 400) return "bg-amber-100 text-amber-800";
  return "bg-red-100 text-red-800";
}

function generateCurl(endpoint: EndpointDef, body: string): string {
  const base = API_BASE_URL;
  const url = `${base}${endpoint.path}`;
  if (endpoint.method === "GET") {
    return `curl -X GET "${url}" \\\n  -H "Authorization: Bearer <token>"`;
  }
  return `curl -X ${endpoint.method} "${url}" \\\n  -H "Content-Type: application/json" \\\n  -H "Authorization: Bearer <token>" \\\n  -d '${body || "{}"}'`;
}

function generatePython(endpoint: EndpointDef, body: string): string {
  const base = API_BASE_URL;
  const url = `${base}${endpoint.path}`;
  if (endpoint.method === "GET") {
    return `import requests\n\nresponse = requests.get(\n    "${url}",\n    headers={"Authorization": "Bearer <token>"}\n)\nprint(response.json())`;
  }
  return `import requests\n\nresponse = requests.${endpoint.method.toLowerCase()}(\n    "${url}",\n    headers={"Authorization": "Bearer <token>"},\n    json=${body || "{}"}\n)\nprint(response.json())`;
}

function generateJavaScript(endpoint: EndpointDef, body: string): string {
  const base = API_BASE_URL;
  const url = `${base}${endpoint.path}`;
  if (endpoint.method === "GET") {
    return `const res = await fetch("${url}", {\n  headers: { "Authorization": "Bearer <token>" }\n});\nconst data = await res.json();\nconsole.log(data);`;
  }
  return `const res = await fetch("${url}", {\n  method: "${endpoint.method}",\n  headers: {\n    "Content-Type": "application/json",\n    "Authorization": "Bearer <token>"\n  },\n  body: JSON.stringify(${body || "{}"})\n});\nconst data = await res.json();\nconsole.log(data);`;
}

const CODE_TABS = ["cURL", "Python", "JavaScript"] as const;

export default function EndpointTester({ endpoint }: { endpoint: EndpointDef }) {
  const [body, setBody] = useState("{}");
  const [response, setResponse] = useState<{ status: number; data: unknown } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [codeTab, setCodeTab] = useState<(typeof CODE_TABS)[number]>("cURL");

  const sendRequest = async () => {
    setLoading(true);
    setError(null);
    setResponse(null);
    try {
      let parsed: unknown = undefined;
      if (endpoint.method !== "GET" && body.trim()) {
        parsed = JSON.parse(body);
      }
      const res = await api.request({
        method: endpoint.method,
        url: endpoint.path,
        data: parsed,
      });
      setResponse({ status: res.status, data: res.data });
    } catch (err: unknown) {
      if (err && typeof err === "object" && "response" in err) {
        const axErr = err as { response: { status: number; data: unknown } };
        setResponse({ status: axErr.response.status, data: axErr.response.data });
      } else {
        setError(String(err));
      }
    } finally {
      setLoading(false);
    }
  };

  const snippet =
    codeTab === "cURL"
      ? generateCurl(endpoint, body)
      : codeTab === "Python"
        ? generatePython(endpoint, body)
        : generateJavaScript(endpoint, body);

  return (
    <div className="space-y-6">
      {/* Try it section */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Try it</h3>
        {endpoint.method !== "GET" && (
          <div className="mb-3">
            <label className="block text-xs text-gray-500 mb-1">Request Body</label>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={6}
              className="w-full font-mono text-sm border border-gray-300 rounded-md p-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        )}
        <button
          onClick={sendRequest}
          disabled={loading}
          className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Sending..." : "Send Request"}
        </button>
      </div>

      {/* Response */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-3 text-sm text-red-700">
          {error}
        </div>
      )}
      {response && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Response</h3>
          <span
            className={`inline-block px-2 py-0.5 rounded text-xs font-medium mb-2 ${statusColor(response.status)}`}
          >
            {response.status}
          </span>
          <pre className="bg-gray-50 border border-gray-200 rounded-md p-4 text-sm overflow-auto max-h-96 font-mono">
            {JSON.stringify(response.data, null, 2)}
          </pre>
        </div>
      )}

      {/* Code snippets */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Code Snippets</h3>
        <div className="flex gap-1 mb-2">
          {CODE_TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setCodeTab(tab)}
              className={`px-3 py-1 text-xs rounded-md font-medium ${
                codeTab === tab
                  ? "bg-gray-800 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
        <pre className="bg-gray-900 text-gray-100 rounded-md p-4 text-sm overflow-auto font-mono">
          {snippet}
        </pre>
      </div>
    </div>
  );
}
