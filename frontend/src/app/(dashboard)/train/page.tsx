"use client";

import { readWorkspaceId } from "@/lib/session";

import { useState } from "react";
import Tabs from "@/components/ui/Tabs";
import ModelRegistryTable from "@/components/train/ModelRegistryTable";
import type { ModelItem } from "@/components/train/ModelRegistryTable";
import RegisterModelModal from "@/components/train/RegisterModelModal";
import ExperimentsTab from "@/components/train/ExperimentsTab";
import DatasetsTab from "@/components/train/DatasetsTab";
import FineTuneWizard from "@/components/train/FineTuneWizard";
import ModelDetailPanel from "@/components/train/ModelDetailPanel";
import ModelCompareModal from "@/components/train/ModelCompareModal";
import type { ModelRecord } from "@/lib/api";

// ASSUMPTION: workspace_id comes from context/auth in real app. Placeholder for now.

// ---------------------------------------------------------------------------
// Adapter: ModelItem (from table) -> ModelRecord (used by detail/compare)
// ---------------------------------------------------------------------------
function toModelRecord(item: ModelItem): ModelRecord {
  return {
    id: item.id,
    name: item.name,
    version: item.version,
    status: item.status,
    backbone: item.backbone,
    metrics: item.metrics,
    workspace_id: item.workspace_id,
    created_at: item.created_at,
    updated_at: item.updated_at,
  };
}

// ---------------------------------------------------------------------------
// Tab content: Models (with detail panel, compare modal, fine-tune wizard)
// ---------------------------------------------------------------------------
function ModelsTab() {
  const [showRegister, setShowRegister] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  // Fine-tune wizard
  const [showFineTune, setShowFineTune] = useState(false);

  // Model detail panel
  const [detailModel, setDetailModel] = useState<ModelRecord | null>(null);

  // Model compare modal
  const [compareModel, setCompareModel] = useState<ModelRecord | null>(null);
  const [compareModelsList, setCompareModelsList] = useState<ModelRecord[]>([]);

  const handleViewDetail = (model: ModelItem) => {
    setDetailModel(toModelRecord(model));
  };

  const handleCompare = (model: ModelItem, allModels: ModelItem[]) => {
    setCompareModel(toModelRecord(model));
    setCompareModelsList(allModels.map(toModelRecord));
  };

  const handleDetailAction = (action: string, modelId: string) => {
    if (action === "compare" && detailModel) {
      setCompareModel(detailModel);
      setDetailModel(null);
    }
    // After promote/archive/shadow, refresh the table
    if (action === "promote" || action === "archive" || action === "shadow") {
      setRefreshKey((k) => k + 1);
    }
  };

  return (
    <>
      {/* Fine-tune button above the table */}
      <div className="flex justify-end mb-4">
        <button
          onClick={() => setShowFineTune(true)}
          className="px-4 py-2 bg-emerald-600 text-white text-sm rounded-lg hover:bg-emerald-700 transition-colors"
        >
          New Fine-Tune Job
        </button>
      </div>

      <ModelRegistryTable
        workspaceId={readWorkspaceId() ?? ""}
        onRegisterClick={() => setShowRegister(true)}
        refreshKey={refreshKey}
        onViewDetail={handleViewDetail}
        onCompare={handleCompare}
      />

      <RegisterModelModal
        isOpen={showRegister}
        onClose={() => setShowRegister(false)}
        onRegistered={() => setRefreshKey((k) => k + 1)}
        workspaceId={readWorkspaceId() ?? ""}
      />

      <FineTuneWizard
        isOpen={showFineTune}
        onClose={() => setShowFineTune(false)}
        onStart={(config) => {
          console.log("Fine-tune started with config:", config);
          setShowFineTune(false);
        }}
      />

      {detailModel && (
        <ModelDetailPanel
          model={detailModel}
          isOpen={!!detailModel}
          onClose={() => setDetailModel(null)}
          onAction={handleDetailAction}
        />
      )}

      {compareModel && (
        <ModelCompareModal
          modelA={compareModel}
          models={compareModelsList}
          isOpen={!!compareModel}
          onClose={() => {
            setCompareModel(null);
            setCompareModelsList([]);
          }}
          onPromote={(modelId) => {
            setRefreshKey((k) => k + 1);
            setCompareModel(null);
            setCompareModelsList([]);
          }}
        />
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------
export default function TrainPage() {
  const [activeTab, setActiveTab] = useState("models");

  const tabs = [
    {
      id: "models",
      label: "Models",
      content: <ModelsTab />,
    },
    {
      id: "experiments",
      label: "Experiments",
      content: <ExperimentsTab />,
    },
    {
      id: "datasets",
      label: "Datasets",
      content: <DatasetsTab />,
    },
  ];

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-2">
        <h1 className="text-2xl font-bold text-gray-900">Train</h1>
        <p className="text-sm text-gray-500 mt-1">
          Model registry, experiments, and dataset management.
        </p>
      </div>
      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />
    </div>
  );
}
