"""Tests for Pydantic schema validation.

Tests both valid and invalid inputs for all schemas.
"""

import uuid
from datetime import datetime

import pytest

from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.schemas.workspace import WorkspaceCreate, WorkspaceRead, WorkspaceUpdate
from app.schemas.model import ModelCreate, ModelRead, ModelUpdate, ModelCompare
from app.schemas.experiment import ExperimentCreate, ExperimentRead, EpochLog
from app.schemas.dataset import DatasetCreate, DatasetRead, DatasetStats
from app.schemas.asset import AssetCreate, AssetRead, AssetFilter
from app.schemas.pipeline import PipelineCreate, PipelineRead, PipelineRunRead
from app.schemas.alert import AlertRuleCreate, AlertRuleRead, AlertRead
from app.schemas.agent import AgentCreate, AgentRead, AgentMemoryRead, ChatMessage
from app.schemas.common import ErrorResponse, SuccessResponse, PaginatedResponse


# --- User Schemas ---

class TestUserSchemas:
    def test_user_create_valid(self):
        u = UserCreate(email="test@example.com", password="secret123")
        assert u.email == "test@example.com"
        assert u.role == "viewer"

    def test_user_create_with_role(self):
        u = UserCreate(email="admin@example.com", password="secret", role="admin")
        assert u.role == "admin"

    def test_user_create_invalid_email(self):
        with pytest.raises(Exception):
            UserCreate(email="not-an-email", password="secret")

    def test_user_create_missing_password(self):
        with pytest.raises(Exception):
            UserCreate(email="test@example.com")

    def test_user_read(self):
        u = UserRead(
            id=uuid.uuid4(),
            email="test@example.com",
            role="viewer",
            workspace_id=None,
            created_at=datetime.now(),
        )
        assert u.email == "test@example.com"

    def test_user_update_partial(self):
        u = UserUpdate(role="admin")
        assert u.email is None
        assert u.role == "admin"

    def test_user_update_empty(self):
        u = UserUpdate()
        assert u.email is None
        assert u.role is None


# --- Workspace Schemas ---

class TestWorkspaceSchemas:
    def test_workspace_create(self):
        w = WorkspaceCreate(name="My Workspace")
        assert w.name == "My Workspace"

    def test_workspace_create_missing_name(self):
        with pytest.raises(Exception):
            WorkspaceCreate()

    def test_workspace_read(self):
        w = WorkspaceRead(
            id=uuid.uuid4(),
            name="Test",
            slug="test",
            plan="free",
            created_at=datetime.now(),
        )
        assert w.slug == "test"

    def test_workspace_update_partial(self):
        w = WorkspaceUpdate(plan="pro")
        assert w.name is None
        assert w.plan == "pro"


# --- Model Schemas ---

class TestModelSchemas:
    def test_model_create(self):
        m = ModelCreate(name="ResNet50", version="1.0")
        assert m.backbone is None

    def test_model_create_with_backbone(self):
        m = ModelCreate(name="ResNet50", version="1.0", backbone="resnet50")
        assert m.backbone == "resnet50"

    def test_model_create_missing_fields(self):
        with pytest.raises(Exception):
            ModelCreate(name="ResNet50")

    def test_model_read(self):
        m = ModelRead(
            id=uuid.uuid4(),
            name="ResNet50",
            version="1.0",
            status="registered",
            metrics={},
            workspace_id=uuid.uuid4(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert m.status == "registered"

    def test_model_update(self):
        m = ModelUpdate(status="production")
        assert m.status == "production"

    def test_model_compare(self):
        ids = [uuid.uuid4(), uuid.uuid4()]
        c = ModelCompare(model_ids=ids)
        assert len(c.model_ids) == 2


# --- Experiment Schemas ---

class TestExperimentSchemas:
    def test_experiment_create(self):
        e = ExperimentCreate(name="exp-1", config={"lr": 0.001})
        assert e.model_id is None

    def test_experiment_create_missing_config(self):
        with pytest.raises(Exception):
            ExperimentCreate(name="exp-1")

    def test_experiment_read(self):
        e = ExperimentRead(
            id=uuid.uuid4(),
            name="exp-1",
            config={"lr": 0.001},
            status="created",
            workspace_id=uuid.uuid4(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert e.status == "created"

    def test_epoch_log(self):
        e = EpochLog(epoch=1, metrics={"loss": 0.5})
        assert e.epoch == 1


# --- Dataset Schemas ---

class TestDatasetSchemas:
    def test_dataset_create(self):
        d = DatasetCreate(name="ImageNet", modality="image")
        assert d.modality == "image"

    def test_dataset_create_missing_modality(self):
        with pytest.raises(Exception):
            DatasetCreate(name="ImageNet")

    def test_dataset_read(self):
        d = DatasetRead(
            id=uuid.uuid4(),
            name="ImageNet",
            modality="image",
            version="1.0",
            stats={},
            workspace_id=uuid.uuid4(),
            sample_count=1000,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert d.sample_count == 1000

    def test_dataset_stats(self):
        s = DatasetStats(total_samples=5000, modality_breakdown={"image": 5000}, version="1.0")
        assert s.total_samples == 5000


# --- Asset Schemas ---

class TestAssetSchemas:
    def test_asset_create(self):
        a = AssetCreate(type="image", path="/data/img.png", filename="img.png")
        assert a.tags is None

    def test_asset_create_with_tags(self):
        a = AssetCreate(type="image", path="/data/img.png", filename="img.png", tags=["train"])
        assert "train" in a.tags

    def test_asset_create_missing_fields(self):
        with pytest.raises(Exception):
            AssetCreate(type="image")

    def test_asset_filter(self):
        f = AssetFilter(type="image", tags=["train", "val"])
        assert len(f.tags) == 2

    def test_asset_filter_empty(self):
        f = AssetFilter()
        assert f.type is None


# --- Pipeline Schemas ---

class TestPipelineSchemas:
    def test_pipeline_create(self):
        p = PipelineCreate(name="preprocess", definition={"steps": []})
        assert p.name == "preprocess"

    def test_pipeline_create_missing_definition(self):
        with pytest.raises(Exception):
            PipelineCreate(name="preprocess")

    def test_pipeline_read(self):
        p = PipelineRead(
            id=uuid.uuid4(),
            name="preprocess",
            version="1.0",
            definition={"steps": []},
            status="draft",
            workspace_id=uuid.uuid4(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert p.status == "draft"

    def test_pipeline_run_read(self):
        r = PipelineRunRead(
            id=uuid.uuid4(),
            pipeline_id=uuid.uuid4(),
            status="completed",
            started_at=datetime.now(),
            finished_at=datetime.now(),
            results={"accuracy": 0.95},
        )
        assert r.status == "completed"


# --- Alert Schemas ---

class TestAlertSchemas:
    def test_alert_rule_create(self):
        r = AlertRuleCreate(
            name="High loss",
            conditions={"metric": "loss", "threshold": 0.9},
            actions={"notify": "email"},
        )
        assert r.enabled is True

    def test_alert_rule_create_missing_fields(self):
        with pytest.raises(Exception):
            AlertRuleCreate(name="High loss")

    def test_alert_rule_read(self):
        r = AlertRuleRead(
            id=uuid.uuid4(),
            name="High loss",
            conditions={"metric": "loss"},
            actions={"notify": "email"},
            enabled=True,
            workspace_id=uuid.uuid4(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert r.enabled is True

    def test_alert_read(self):
        a = AlertRead(
            id=uuid.uuid4(),
            rule_id=uuid.uuid4(),
            severity="high",
            status="new",
            workspace_id=uuid.uuid4(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert a.severity == "high"


# --- Agent Schemas ---

class TestAgentSchemas:
    def test_agent_create(self):
        a = AgentCreate(name="assistant", agent_type="chat")
        assert a.config is None

    def test_agent_create_with_config(self):
        a = AgentCreate(name="assistant", agent_type="chat", config={"model": "gpt-4"})
        assert a.config["model"] == "gpt-4"

    def test_agent_create_missing_type(self):
        with pytest.raises(Exception):
            AgentCreate(name="assistant")

    def test_agent_read(self):
        a = AgentRead(
            id=uuid.uuid4(),
            name="assistant",
            agent_type="chat",
            config={},
            status="idle",
            workspace_id=uuid.uuid4(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert a.status == "idle"

    def test_agent_memory_read(self):
        m = AgentMemoryRead(
            id=uuid.uuid4(),
            agent_id=uuid.uuid4(),
            content="Remember this.",
            importance_score=0.8,
            freshness_score=1.0,
            created_at=datetime.now(),
        )
        assert m.importance_score == 0.8

    def test_chat_message(self):
        c = ChatMessage(role="user", content="Hello")
        assert c.role == "user"


# --- Common Schemas ---

class TestCommonSchemas:
    def test_error_response(self):
        e = ErrorResponse(detail="Not found", code=404)
        assert e.code == 404

    def test_success_response(self):
        s = SuccessResponse(message="OK")
        assert s.message == "OK"

    def test_paginated_response(self):
        p = PaginatedResponse(items=["a", "b"], total=10, page=1, size=2)
        assert p.total == 10
        assert len(p.items) == 2
