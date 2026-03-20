"use client";

import { Node } from "reactflow";

interface NodeConfigProps {
  node: Node | null;
  onUpdate: (nodeId: string, params: Record<string, unknown>) => void;
}

export default function NodeConfig({ node, onUpdate }: NodeConfigProps) {
  if (!node) {
    return (
      <aside className="w-72 bg-white border-l border-gray-200 p-4 flex items-center justify-center text-sm text-gray-400">
        Select a node to configure
      </aside>
    );
  }

  const { data } = node;
  const inputs: Record<string, Record<string, unknown>> = data.inputs || {};
  const params: Record<string, unknown> = data.params || {};

  const handleChange = (key: string, value: unknown) => {
    onUpdate(node.id, { ...params, [key]: value });
  };

  return (
    <aside className="w-72 bg-white border-l border-gray-200 overflow-y-auto flex-shrink-0">
      <div className="p-3 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-700">
          {data.label || node.type}
        </h3>
        <p className="text-xs text-gray-400 mt-0.5">{data.description}</p>
      </div>
      <div className="p-3 space-y-3">
        {Object.entries(inputs).map(([key, spec]) => {
          const fieldType = (spec.type as string) || "string";
          const enumValues = (spec.enum as string[]) || null;
          const isRequired = !!spec.required;

          return (
            <div key={key}>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                {key}
                {isRequired && <span className="text-red-400 ml-0.5">*</span>}
              </label>
              {enumValues ? (
                <select
                  className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:ring-1 focus:ring-brand-500 focus:border-brand-500"
                  value={(params[key] as string) ?? ""}
                  onChange={(e) => handleChange(key, e.target.value)}
                >
                  <option value="">Select...</option>
                  {enumValues.map((v) => (
                    <option key={v} value={v}>
                      {v}
                    </option>
                  ))}
                </select>
              ) : fieldType === "integer" || fieldType === "number" ? (
                <input
                  type="number"
                  className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:ring-1 focus:ring-brand-500 focus:border-brand-500"
                  value={(params[key] as number) ?? ""}
                  onChange={(e) =>
                    handleChange(
                      key,
                      fieldType === "integer"
                        ? parseInt(e.target.value)
                        : parseFloat(e.target.value),
                    )
                  }
                />
              ) : (
                <input
                  type="text"
                  className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:ring-1 focus:ring-brand-500 focus:border-brand-500"
                  value={(params[key] as string) ?? ""}
                  onChange={(e) => handleChange(key, e.target.value)}
                  placeholder={spec.description as string}
                />
              )}
              {spec.description ? (
                <p className="text-xs text-gray-400 mt-0.5">
                  {spec.description as string}
                </p>
              ) : null}
            </div>
          );
        })}
      </div>
    </aside>
  );
}
