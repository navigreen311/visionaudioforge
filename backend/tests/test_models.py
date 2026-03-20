"""Tests for SQLAlchemy model definitions.

Verifies that all models can be instantiated and have the expected fields.
"""

import uuid
from datetime import datetime

from app.models import (
    Agent,
    AgentMemory,
    Alert,
    AlertRule,
    Asset,
    AuditLog,
    Base,
    Dataset,
    Embedding,
    Event,
    Experiment,
    ExperimentEpoch,
    ModelRecord,
    Pipeline,
    PipelineRun,
    TimestampMixin,
    UUIDMixin,
    User,
    Workspace,
)


class TestBaseMixins:
    def test_base_is_declarative(self):
        assert hasattr(Base, "metadata")
        assert hasattr(Base, "registry")

    def test_uuid_mixin_has_id(self):
        assert hasattr(UUIDMixin, "id")

    def test_timestamp_mixin_has_fields(self):
        assert hasattr(TimestampMixin, "created_at")
        assert hasattr(TimestampMixin, "updated_at")


class TestUserModel:
    def test_tablename(self):
        assert User.__tablename__ == "users"

    def test_fields_exist(self):
        columns = {c.name for c in User.__table__.columns}
        assert "id" in columns
        assert "email" in columns
        assert "hashed_password" in columns
        assert "role" in columns
        assert "workspace_id" in columns
        assert "last_login" in columns
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_email_is_unique(self):
        col = User.__table__.columns["email"]
        assert col.unique is True

    def test_email_is_not_nullable(self):
        col = User.__table__.columns["email"]
        assert col.nullable is False


class TestWorkspaceModel:
    def test_tablename(self):
        assert Workspace.__tablename__ == "workspaces"

    def test_fields_exist(self):
        columns = {c.name for c in Workspace.__table__.columns}
        assert "id" in columns
        assert "name" in columns
        assert "slug" in columns
        assert "owner_id" in columns
        assert "plan" in columns
        assert "settings" in columns
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_slug_is_unique(self):
        col = Workspace.__table__.columns["slug"]
        assert col.unique is True

    def test_owner_id_nullable(self):
        col = Workspace.__table__.columns["owner_id"]
        assert col.nullable is True


class TestModelRecordModel:
    def test_tablename(self):
        assert ModelRecord.__tablename__ == "model_registry"

    def test_fields_exist(self):
        columns = {c.name for c in ModelRecord.__table__.columns}
        assert "id" in columns
        assert "name" in columns
        assert "version" in columns
        assert "status" in columns
        assert "backbone" in columns
        assert "metrics" in columns
        assert "workspace_id" in columns

    def test_backbone_nullable(self):
        col = ModelRecord.__table__.columns["backbone"]
        assert col.nullable is True


class TestExperimentModel:
    def test_tablename(self):
        assert Experiment.__tablename__ == "experiments"

    def test_fields_exist(self):
        columns = {c.name for c in Experiment.__table__.columns}
        assert "id" in columns
        assert "name" in columns
        assert "config" in columns
        assert "status" in columns
        assert "best_epoch" in columns
        assert "model_id" in columns
        assert "workspace_id" in columns


class TestExperimentEpochModel:
    def test_tablename(self):
        assert ExperimentEpoch.__tablename__ == "experiment_epochs"

    def test_fields_exist(self):
        columns = {c.name for c in ExperimentEpoch.__table__.columns}
        assert "id" in columns
        assert "experiment_id" in columns
        assert "epoch" in columns
        assert "metrics" in columns
        assert "timestamp" in columns


class TestDatasetModel:
    def test_tablename(self):
        assert Dataset.__tablename__ == "datasets"

    def test_fields_exist(self):
        columns = {c.name for c in Dataset.__table__.columns}
        assert "id" in columns
        assert "name" in columns
        assert "modality" in columns
        assert "version" in columns
        assert "stats" in columns
        assert "workspace_id" in columns
        assert "sample_count" in columns


class TestAssetModel:
    def test_tablename(self):
        assert Asset.__tablename__ == "assets"

    def test_fields_exist(self):
        columns = {c.name for c in Asset.__table__.columns}
        assert "id" in columns
        assert "type" in columns
        assert "path" in columns
        assert "filename" in columns
        assert "size_bytes" in columns
        assert "metadata" in columns  # mapped column name
        assert "tags" in columns
        assert "workspace_id" in columns


class TestPipelineModel:
    def test_tablename(self):
        assert Pipeline.__tablename__ == "pipelines"

    def test_fields_exist(self):
        columns = {c.name for c in Pipeline.__table__.columns}
        assert "id" in columns
        assert "name" in columns
        assert "version" in columns
        assert "definition" in columns
        assert "status" in columns
        assert "workspace_id" in columns


class TestPipelineRunModel:
    def test_tablename(self):
        assert PipelineRun.__tablename__ == "pipeline_runs"

    def test_fields_exist(self):
        columns = {c.name for c in PipelineRun.__table__.columns}
        assert "id" in columns
        assert "pipeline_id" in columns
        assert "status" in columns
        assert "started_at" in columns
        assert "finished_at" in columns
        assert "results" in columns


class TestAlertRuleModel:
    def test_tablename(self):
        assert AlertRule.__tablename__ == "alert_rules"

    def test_fields_exist(self):
        columns = {c.name for c in AlertRule.__table__.columns}
        assert "id" in columns
        assert "name" in columns
        assert "conditions" in columns
        assert "actions" in columns
        assert "enabled" in columns
        assert "workspace_id" in columns


class TestAlertModel:
    def test_tablename(self):
        assert Alert.__tablename__ == "alerts"

    def test_fields_exist(self):
        columns = {c.name for c in Alert.__table__.columns}
        assert "id" in columns
        assert "rule_id" in columns
        assert "severity" in columns
        assert "payload" in columns
        assert "status" in columns
        assert "acknowledged_by" in columns
        assert "workspace_id" in columns


class TestEmbeddingModel:
    def test_tablename(self):
        assert Embedding.__tablename__ == "embeddings"

    def test_fields_exist(self):
        columns = {c.name for c in Embedding.__table__.columns}
        assert "id" in columns
        assert "asset_id" in columns
        assert "modality" in columns
        assert "vector_data" in columns
        assert "model_name" in columns
        assert "created_at" in columns


class TestEventModel:
    def test_tablename(self):
        assert Event.__tablename__ == "events"

    def test_fields_exist(self):
        columns = {c.name for c in Event.__table__.columns}
        assert "id" in columns
        assert "type" in columns
        assert "payload" in columns
        assert "timestamp" in columns
        assert "source" in columns
        assert "workspace_id" in columns
        assert "linked_asset_ids" in columns


class TestAuditLogModel:
    def test_tablename(self):
        assert AuditLog.__tablename__ == "audit_logs"

    def test_fields_exist(self):
        columns = {c.name for c in AuditLog.__table__.columns}
        assert "id" in columns
        assert "user_id" in columns
        assert "action" in columns
        assert "resource" in columns
        assert "payload" in columns
        assert "timestamp" in columns
        assert "workspace_id" in columns


class TestAgentModel:
    def test_tablename(self):
        assert Agent.__tablename__ == "agents"

    def test_fields_exist(self):
        columns = {c.name for c in Agent.__table__.columns}
        assert "id" in columns
        assert "name" in columns
        assert "agent_type" in columns
        assert "config" in columns
        assert "status" in columns
        assert "workspace_id" in columns


class TestAgentMemoryModel:
    def test_tablename(self):
        assert AgentMemory.__tablename__ == "agent_memories"

    def test_fields_exist(self):
        columns = {c.name for c in AgentMemory.__table__.columns}
        assert "id" in columns
        assert "agent_id" in columns
        assert "content" in columns
        assert "importance_score" in columns
        assert "freshness_score" in columns
        assert "created_at" in columns
        assert "expires_at" in columns
