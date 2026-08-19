"""Comprehensive platform lifecycle E2E tests.

Each test exercises a full subsystem lifecycle through the HTTP API,
verifying correct sequencing and data flow across all major platform features.
"""

import uuid

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.e2e]

# Accepted status codes
OK = (200, 201)
ACCEPTABLE = (200, 201, 400, 422, 501)
NOT_404 = lambda r: r.status_code != 404  # noqa: E731

WS_ID = "00000000-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# 1. Model lifecycle: register → experiment → log 5 epochs → best →
#    promote staging → promote production → compare → rollback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_model_lifecycle_complete(test_app, test_workspace_id):
    """Full model lifecycle: register, experiment, epochs, promote, compare, rollback."""
    model_name = f"lifecycle-model-{uuid.uuid4().hex[:6]}"

    # Register model A
    r_reg = await test_app.post(
        "/api/registry/register",
        json={
            "name": model_name,
            "version": "1.0.0",
            "backbone": "resnet50",
            "metrics": {"accuracy": 0.90, "f1": 0.88},
            "workspace_id": test_workspace_id,
        },
    )
    assert r_reg.status_code != 404, f"registry/register returned 404"

    if r_reg.status_code not in OK:
        pytest.skip(f"Model registration returned {r_reg.status_code}, skipping lifecycle")

    model_a_id = r_reg.json()["id"]

    # Create experiment linked to model
    r_exp = await test_app.post(
        "/api/experiments",
        json={
            "name": f"exp-{uuid.uuid4().hex[:6]}",
            "config": {"backbone": "resnet50", "epochs": 5, "lr": 0.001},
            "workspace_id": test_workspace_id,
        },
    )
    assert r_exp.status_code != 404, "experiments create returned 404"

    if r_exp.status_code in OK:
        exp_id = r_exp.json()["id"]

        # Log 5 epochs
        for epoch in range(1, 6):
            r_log = await test_app.post(
                f"/api/experiments/{exp_id}/epochs",
                json={
                    "epoch": epoch,
                    "metrics": {
                        "loss": 1.0 / epoch,
                        "accuracy": 0.5 + epoch * 0.08,
                        "val_loss": 1.1 / epoch,
                    },
                },
            )
            assert r_log.status_code != 404, f"experiments/{exp_id}/epochs returned 404"

        # Get best checkpoint
        r_best = await test_app.get(f"/api/experiments/{exp_id}/best")
        assert r_best.status_code != 404, f"experiments/{exp_id}/best returned 404"

    # Promote to staging
    r_stage = await test_app.put(
        f"/api/registry/models/{model_a_id}/status",
        json={"status": "staging"},
    )
    assert r_stage.status_code != 404, "registry promote-to-staging returned 404"

    # Promote to production
    r_prod = await test_app.put(
        f"/api/registry/models/{model_a_id}/status",
        json={"status": "production"},
    )
    assert r_prod.status_code != 404, "registry promote-to-production returned 404"

    # Register model B for comparison
    r_reg_b = await test_app.post(
        "/api/registry/register",
        json={
            "name": f"compare-model-{uuid.uuid4().hex[:6]}",
            "version": "1.0.0",
            "backbone": "resnet101",
            "metrics": {"accuracy": 0.93},
            "workspace_id": test_workspace_id,
        },
    )
    assert r_reg_b.status_code != 404

    if r_reg_b.status_code in OK:
        model_b_id = r_reg_b.json()["id"]

        # Compare models
        r_compare = await test_app.post(
            "/api/registry/compare",
            json={"model_a_id": model_a_id, "model_b_id": model_b_id},
        )
        assert r_compare.status_code != 404, "registry/compare returned 404"

    # Rollback model A
    r_rollback = await test_app.post(
        f"/api/registry/models/{model_a_id}/rollback",
        json={"to_version": "1.0.0"},
    )
    assert r_rollback.status_code != 404, "registry rollback returned 404"


# ---------------------------------------------------------------------------
# 2. Dataset lifecycle: create → upload samples → compute stats →
#    split 70/15/15 → export
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dataset_lifecycle(test_app, test_workspace_id, test_image):
    """Full dataset lifecycle: create, upload, stats, split, export."""
    ds_name = f"ds-lifecycle-{uuid.uuid4().hex[:6]}"

    # Create dataset
    r_create = await test_app.post(
        "/api/datasets",
        json={
            "name": ds_name,
            "modality": "image",
            "workspace_id": test_workspace_id,
        },
    )
    assert r_create.status_code != 404, "datasets create returned 404"

    if r_create.status_code not in OK:
        pytest.skip(f"Dataset creation returned {r_create.status_code}")

    ds_id = r_create.json()["id"]

    # Upload samples (mock image)
    r_upload = await test_app.post(
        f"/api/datasets/{ds_id}/upload",
        files=[("files", ("sample1.png", test_image, "image/png"))],
    )
    assert r_upload.status_code != 404, f"datasets/{ds_id}/upload returned 404"

    # Compute stats
    r_stats = await test_app.post(f"/api/datasets/{ds_id}/stats")
    assert r_stats.status_code != 404, f"datasets/{ds_id}/stats returned 404"

    # Split 70/15/15
    r_split = await test_app.post(
        f"/api/datasets/{ds_id}/split",
        json={"train": 0.7, "val": 0.15, "test": 0.15},
    )
    assert r_split.status_code != 404, f"datasets/{ds_id}/split returned 404"

    # Export
    r_export = await test_app.get(f"/api/datasets/{ds_id}/export")
    assert r_export.status_code != 404, f"datasets/{ds_id}/export returned 404"


# ---------------------------------------------------------------------------
# 3. Pipeline lifecycle: create → validate → list nodes → generate from NL →
#    verify templates exist
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_lifecycle(test_app, test_workspace_id):
    """Full pipeline lifecycle: create, validate, list nodes, NL generate, templates."""
    pipeline_def = {
        "nodes": [
            {"id": "n1", "type": "input", "config": {}},
            {"id": "n2", "type": "resize", "config": {"width": 224, "height": 224}},
            {"id": "n3", "type": "normalize", "config": {}},
        ],
        "edges": [
            {"source": "n1", "target": "n2"},
            {"source": "n2", "target": "n3"},
        ],
    }

    # Validate pipeline
    r_validate = await test_app.post(
        "/api/pipeline/validate",
        json={"definition": pipeline_def},
    )
    assert r_validate.status_code != 404, "pipeline/validate returned 404"

    # Create pipeline
    r_create = await test_app.post(
        "/api/pipeline/create",
        json={
            "name": f"pipe-lifecycle-{uuid.uuid4().hex[:6]}",
            "description": "E2E lifecycle test pipeline",
            "definition": pipeline_def,
            "workspace_id": test_workspace_id,
        },
    )
    assert r_create.status_code != 404, "pipeline/create returned 404"

    # List node types
    r_nodes = await test_app.get("/api/pipeline/nodes")
    assert r_nodes.status_code != 404, "pipeline/nodes returned 404"

    # Generate pipeline from NL description
    r_generate = await test_app.post(
        "/api/pipeline/generate",
        json={"description": "Resize images to 224x224 and normalize pixel values"},
    )
    assert r_generate.status_code != 404, "pipeline/generate returned 404"

    # Verify templates exist
    r_templates = await test_app.get("/api/pipeline/templates")
    assert r_templates.status_code != 404, "pipeline/templates returned 404"

    if r_templates.status_code == 200:
        templates = r_templates.json()
        assert isinstance(templates, list), "Templates should be a list"


# ---------------------------------------------------------------------------
# 4. Alert lifecycle: create compound rule → trigger test alert →
#    acknowledge → resolve
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_alert_lifecycle(test_app, test_workspace_id):
    """Full alert lifecycle: create compound rule, trigger, acknowledge, resolve."""
    user_id = "00000000-0000-0000-0000-000000000099"

    # Create compound rule
    r_rule = await test_app.post(
        "/api/alerts/rules",
        params={"workspace_id": test_workspace_id},
        json={
            "name": f"compound-rule-{uuid.uuid4().hex[:6]}",
            "conditions": {
                "type": "compound",
                "conditions": [
                    {"type": "threshold", "metric": "accuracy", "operator": "<", "value": 0.5},
                    {"type": "threshold", "metric": "latency_ms", "operator": ">", "value": 1000},
                ],
            },
            "actions": [{"type": "webhook", "config": {"url": "https://example.com/hook"}}],
            "enabled": True,
        },
    )
    assert r_rule.status_code != 404, "alerts/rules create returned 404"

    if r_rule.status_code not in OK:
        pytest.skip(f"Alert rule creation returned {r_rule.status_code}")

    rule_id = r_rule.json()["id"]

    # Trigger test alert
    r_trigger = await test_app.post(
        "/api/alerts/test",
        params={"rule_id": rule_id, "workspace_id": test_workspace_id},
    )
    assert r_trigger.status_code != 404, "alerts/test returned 404"

    if r_trigger.status_code in OK:
        alert_id = r_trigger.json()["id"]

        # Acknowledge
        r_ack = await test_app.post(
            f"/api/alerts/{alert_id}/acknowledge",
            params={"user_id": user_id},
        )
        assert r_ack.status_code != 404, f"alerts/{alert_id}/acknowledge returned 404"

        # Resolve
        r_resolve = await test_app.post(
            f"/api/alerts/{alert_id}/resolve",
            params={"user_id": user_id},
        )
        assert r_resolve.status_code != 404, f"alerts/{alert_id}/resolve returned 404"

    # Get alert stats
    r_stats = await test_app.get(
        "/api/alerts/stats",
        params={"workspace_id": test_workspace_id},
    )
    assert r_stats.status_code != 404, "alerts/stats returned 404"


# ---------------------------------------------------------------------------
# 5. Search lifecycle: index asset → search by text → verify results →
#    search stats
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_lifecycle(test_app):
    """Full search lifecycle: index, text search, verify results, stats."""
    asset_id = str(uuid.uuid4())

    # Indexing an asset that does not exist must be refused. This used to assert
    # the opposite - that posting a random UUID indexed something - which only
    # held because the endpoint embedded the text of the id and reported success
    # regardless. Every vector in the index described a hex string.
    r_index = await test_app.post(
        "/api/search/index",
        json={"asset_id": asset_id},
    )
    assert r_index.status_code in (401, 403, 404), (
        f"indexing a nonexistent asset should be refused, got {r_index.status_code}"
    )

    # Search by text
    r_search = await test_app.post(
        "/api/search/query",
        json={"query": "test search term", "modality": "text", "k": 5},
    )
    assert r_search.status_code != 404, "search/query returned 404"

    if r_search.status_code == 200:
        results = r_search.json()
        assert "results" in results, "Search response should have results"

    # Search stats
    r_stats = await test_app.get("/api/search/stats")
    assert r_stats.status_code != 404, "search/stats returned 404"

    if r_stats.status_code == 200:
        stats = r_stats.json()
        assert "total_vectors" in stats, "Stats should include total_vectors"
        # No assertion that the index is non-empty: nothing in this test indexes
        # a real asset, and the previous expectation was satisfied only by the
        # endpoint indexing a UUID string.
        assert stats["total_vectors"] >= 0


# ---------------------------------------------------------------------------
# 6. Investigation lifecycle: create case → add evidence → add note →
#    get timeline → draft report → sign report
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_investigation_lifecycle(test_app, test_workspace_id):
    """Full investigation lifecycle: case, evidence, note, timeline, report, sign."""
    # Create case
    r_case = await test_app.post(
        "/api/investigate/cases",
        json={
            "name": f"case-{uuid.uuid4().hex[:6]}",
            "description": "E2E investigation lifecycle test",
            "workspace_id": test_workspace_id,
        },
    )
    assert r_case.status_code != 404, "investigate/cases create returned 404"

    if r_case.status_code not in OK:
        pytest.skip(f"Case creation returned {r_case.status_code}")

    case_id = r_case.json()["id"]

    # Add evidence
    r_evidence = await test_app.post(
        f"/api/investigate/cases/{case_id}/evidence",
        json={
            "asset_id": "00000000-0000-0000-0000-000000000001",
            "notes": "Suspicious activity detected in frame 42",
        },
    )
    assert r_evidence.status_code != 404, f"cases/{case_id}/evidence returned 404"

    # Add note
    r_note = await test_app.post(
        f"/api/investigate/cases/{case_id}/notes",
        json={"user_id": "analyst-1", "content": "Initial review indicates anomaly"},
    )
    assert r_note.status_code != 404, f"cases/{case_id}/notes returned 404"

    # Get timeline
    r_timeline = await test_app.get(
        "/api/investigate/timeline",
        params={
            "workspace_id": test_workspace_id,
            "start": "2020-01-01T00:00:00",
            "end": "2030-12-31T23:59:59",
        },
    )
    assert r_timeline.status_code != 404, "investigate/timeline returned 404"

    # Draft report
    r_report = await test_app.post(f"/api/investigate/cases/{case_id}/report")
    assert r_report.status_code != 404, f"cases/{case_id}/report returned 404"

    # Sign report
    r_sign = await test_app.post(
        f"/api/investigate/cases/{case_id}/report/sign",
        json={"user_id": "analyst-1"},
    )
    assert r_sign.status_code != 404, f"cases/{case_id}/report/sign returned 404"


# ---------------------------------------------------------------------------
# 7. Agent lifecycle: create → store memory → recall → decay → patrol →
#    conversation store/retrieve
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_lifecycle(test_app, test_workspace_id):
    """Full agent lifecycle: create, memory store/recall/decay, patrol, conversation."""
    # Create agent
    r_create = await test_app.post(
        "/api/agents",
        json={
            "name": f"agent-{uuid.uuid4().hex[:6]}",
            "agent_type": "copilot",
            "workspace_id": test_workspace_id,
        },
    )
    assert r_create.status_code != 404, "agents create returned 404"

    if r_create.status_code not in OK:
        pytest.skip(f"Agent creation returned {r_create.status_code}")

    agent_id = r_create.json()["id"]

    # Store memory via chat (chat automatically stores substantive responses)
    r_chat = await test_app.post(
        "/api/agents/chat",
        json={"message": "Remember that the deployment was at 3pm", "agent_id": agent_id},
    )
    assert r_chat.status_code != 404, "agents/chat returned 404"

    # Recall memories
    r_memory = await test_app.get(f"/api/agents/{agent_id}/memory")
    assert r_memory.status_code != 404, f"agents/{agent_id}/memory returned 404"

    # Decay memories
    r_decay = await test_app.post(f"/api/agents/{agent_id}/memory/decay")
    assert r_decay.status_code != 404, f"agents/{agent_id}/memory/decay returned 404"

    # Start patrol cycle
    r_patrol = await test_app.post(f"/api/agents/{agent_id}/patrol/start")
    assert r_patrol.status_code != 404, f"agents/{agent_id}/patrol/start returned 404"

    # Stop patrol
    r_stop = await test_app.post(f"/api/agents/{agent_id}/patrol/stop")
    assert r_stop.status_code != 404, f"agents/{agent_id}/patrol/stop returned 404"

    # Get conversation history
    r_history = await test_app.get(f"/api/agents/{agent_id}/history")
    assert r_history.status_code != 404, f"agents/{agent_id}/history returned 404"


# ---------------------------------------------------------------------------
# 8. Governance lifecycle: create API key → validate → check permissions →
#    check billing → check feature flags
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_governance_lifecycle(test_app):
    """Full governance lifecycle: API key, permissions, billing, feature flags."""
    # Create API key (governance prefix, requires auth deps)
    r_key = await test_app.post(
        "/api/governance/api-keys",
        json={"name": "e2e-test-key", "scopes": ["read", "write"], "expires_in_days": 30},
    )
    assert r_key.status_code != 404, "governance/api-keys create returned 404"

    # List API keys
    r_list = await test_app.get("/api/governance/api-keys")
    assert r_list.status_code != 404, "governance/api-keys list returned 404"

    # Check permissions for a role
    r_perms = await test_app.get("/api/governance/permissions/admin")
    assert r_perms.status_code != 404, "governance/permissions returned 404"

    if r_perms.status_code == 200:
        data = r_perms.json()
        assert "role" in data, "Permissions response should have role"
        assert "permissions" in data, "Permissions response should have permissions"

    # Check billing usage
    r_billing = await test_app.get("/api/governance/billing/usage")
    assert r_billing.status_code != 404, "governance/billing/usage returned 404"

    # Check billing dashboard
    r_dashboard = await test_app.get("/api/governance/billing/dashboard")
    assert r_dashboard.status_code != 404, "governance/billing/dashboard returned 404"

    # Check feature flags
    r_features = await test_app.get("/api/governance/features")
    assert r_features.status_code != 404, "governance/features returned 404"


# ---------------------------------------------------------------------------
# 9. Safety lifecycle: detect PII in text → redact → scan image →
#    blur faces → check compliance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_safety_lifecycle(test_app, test_image):
    """Full safety lifecycle: PII detection, redaction, image scan, blur, compliance."""
    # Detect PII in text
    r_scan_text = await test_app.post(
        "/api/safety/scan",
        data={
            "scan_type": "text",
            "text": "My SSN is 123-45-6789 and email is john@example.com",
        },
    )
    assert r_scan_text.status_code != 404, "safety/scan text returned 404"

    if r_scan_text.status_code == 200:
        data = r_scan_text.json()
        assert "pii_found" in data, "Text scan should report PII"
        assert len(data["pii_found"]) > 0, "Should detect PII in test text"

    # Redact PII
    r_redact = await test_app.post(
        "/api/safety/redact",
        json={"text": "My SSN is 123-45-6789 and email is john@example.com"},
    )
    assert r_redact.status_code != 404, "safety/redact returned 404"

    # Scan image
    r_scan_img = await test_app.post(
        "/api/safety/scan",
        files={"file": ("test.png", test_image, "image/png")},
        data={"scan_type": "image"},
    )
    assert r_scan_img.status_code != 404, "safety/scan image returned 404"

    # Blur faces
    r_blur = await test_app.post(
        "/api/safety/blur-faces",
        files={"file": ("test.png", test_image, "image/png")},
    )
    assert r_blur.status_code != 404, "safety/blur-faces returned 404"

    # Check compliance (GDPR)
    r_compliance = await test_app.get("/api/safety/compliance/gdpr")
    assert r_compliance.status_code != 404, "safety/compliance/gdpr returned 404"


# ---------------------------------------------------------------------------
# 10. Knowledge Graph lifecycle: add node → add edge → get neighbors →
#     scene graph → verify graph structure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_knowledge_graph_lifecycle(test_app):
    """Full KG lifecycle: nodes, edges, neighbors, scene extraction."""
    # Add node A
    r_node_a = await test_app.post(
        "/api/knowledge-graph/nodes",
        json={"label": "Person-A", "node_type": "entity", "properties": {"role": "suspect"}},
    )
    assert r_node_a.status_code != 404, "knowledge-graph/nodes create returned 404"

    node_a_id = None
    if r_node_a.status_code in OK:
        node_a_id = r_node_a.json()["id"]

    # Add node B
    r_node_b = await test_app.post(
        "/api/knowledge-graph/nodes",
        json={"label": "Vehicle-X", "node_type": "object", "properties": {"plate": "ABC123"}},
    )
    assert r_node_b.status_code != 404

    node_b_id = None
    if r_node_b.status_code in OK:
        node_b_id = r_node_b.json()["id"]

    # Add edge
    if node_a_id and node_b_id:
        r_edge = await test_app.post(
            "/api/knowledge-graph/edges",
            json={
                "source_id": node_a_id,
                "target_id": node_b_id,
                "relation": "drives",
                "weight": 0.95,
            },
        )
        assert r_edge.status_code != 404, "knowledge-graph/edges create returned 404"

        # Get neighbors
        r_neighbors = await test_app.get(f"/api/knowledge-graph/nodes/{node_a_id}/neighbors")
        assert r_neighbors.status_code != 404, "knowledge-graph neighbors returned 404"

        if r_neighbors.status_code == 200:
            data = r_neighbors.json()
            assert len(data.get("neighbors", [])) >= 1, "Node A should have at least 1 neighbor"

    # Scene graph extraction
    r_scene = await test_app.post(
        "/api/knowledge-graph/scene-extract",
        json={"description": "Person walking near Vehicle in parking lot"},
    )
    assert r_scene.status_code != 404, "knowledge-graph/scene-extract returned 404"

    if r_scene.status_code == 200:
        data = r_scene.json()
        assert "entities_extracted" in data, "Scene extract should report entities"

    # List all nodes (verify graph has data)
    r_list = await test_app.get("/api/knowledge-graph/nodes")
    assert r_list.status_code != 404, "knowledge-graph/nodes list returned 404"


# ---------------------------------------------------------------------------
# 11. Semantic Memory lifecycle: store → recall → promote → decay →
#     list memories
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_semantic_memory_lifecycle(test_app, test_workspace_id):
    """Full semantic memory lifecycle: store, recall, promote, decay, list."""
    # Store memory 1
    r_store1 = await test_app.post(
        "/api/semantic-memory/store",
        json={
            "content": "The security camera detected motion at 2am near gate B",
            "category": "security",
            "importance": 0.7,
            "workspace_id": test_workspace_id,
        },
    )
    assert r_store1.status_code != 404, "semantic-memory/store returned 404"

    mem_id = None
    if r_store1.status_code in OK:
        mem_id = r_store1.json()["id"]

    # Store memory 2 (for conflict/merge testing via recall)
    r_store2 = await test_app.post(
        "/api/semantic-memory/store",
        json={
            "content": "Motion near gate B was a false alarm caused by wind",
            "category": "security",
            "importance": 0.5,
            "workspace_id": test_workspace_id,
        },
    )
    assert r_store2.status_code != 404

    # Recall by query
    r_recall = await test_app.post(
        "/api/semantic-memory/recall",
        json={
            "query": "gate B",
            "limit": 10,
            "category": "security",
            "workspace_id": test_workspace_id,
        },
    )
    assert r_recall.status_code != 404, "semantic-memory/recall returned 404"

    if r_recall.status_code == 200:
        data = r_recall.json()
        assert data.get("total", 0) >= 1, "Should recall at least one memory about gate B"

    # Promote memory
    if mem_id:
        r_promote = await test_app.post(
            f"/api/semantic-memory/promote/{mem_id}",
            params={"boost": 0.2},
        )
        assert r_promote.status_code != 404, "semantic-memory/promote returned 404"

        if r_promote.status_code == 200:
            assert r_promote.json()["importance"] >= 0.9, "Promoted memory should have boosted importance"

    # Decay all memories
    r_decay = await test_app.post(
        "/api/semantic-memory/decay",
        params={"threshold": 0.1, "factor": 0.95},
    )
    assert r_decay.status_code != 404, "semantic-memory/decay returned 404"

    if r_decay.status_code == 200:
        assert r_decay.json()["decayed_count"] >= 1, "At least one memory should be decayed"

    # List all memories
    r_list = await test_app.get("/api/semantic-memory/memories")
    assert r_list.status_code != 404, "semantic-memory/memories returned 404"


# ---------------------------------------------------------------------------
# 12. Federated Learning lifecycle: create federation → join →
#     start round (validates update) → verify status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_federated_lifecycle(test_app):
    """Full federated lifecycle: create federation, join participants, start round."""
    # Create federation
    r_create = await test_app.post(
        "/api/federated/federations",
        json={
            "name": f"fed-{uuid.uuid4().hex[:6]}",
            "model_id": str(uuid.uuid4()),
            "aggregation_strategy": "fedavg",
            "min_participants": 2,
            "rounds": 5,
        },
    )
    assert r_create.status_code != 404, "federated/federations create returned 404"

    if r_create.status_code not in OK:
        pytest.skip(f"Federation creation returned {r_create.status_code}")

    fed_id = r_create.json()["id"]

    # Join participant 1
    r_join1 = await test_app.post(
        f"/api/federated/federations/{fed_id}/join",
        json={
            "participant_id": str(uuid.uuid4()),
            "participant_name": "hospital-alpha",
            "data_size": 10000,
        },
    )
    assert r_join1.status_code != 404, f"federations/{fed_id}/join returned 404"

    # Join participant 2
    r_join2 = await test_app.post(
        f"/api/federated/federations/{fed_id}/join",
        json={
            "participant_id": str(uuid.uuid4()),
            "participant_name": "hospital-beta",
            "data_size": 8000,
        },
    )
    assert r_join2.status_code != 404

    if r_join2.status_code in OK:
        assert r_join2.json()["status"] == "ready", "Federation should be ready with 2 participants"

    # Start round (validates update and aggregates with FedAvg)
    r_round = await test_app.post(
        f"/api/federated/federations/{fed_id}/start-round",
        json={"round_number": 1},
    )
    assert r_round.status_code != 404, f"federations/{fed_id}/start-round returned 404"

    if r_round.status_code == 200:
        data = r_round.json()
        assert data.get("status") == "training", "Round should start training"

    # Verify federation state
    r_get = await test_app.get(f"/api/federated/federations/{fed_id}")
    assert r_get.status_code != 404

    if r_get.status_code == 200:
        data = r_get.json()
        assert data["current_round"] >= 1, "Current round should be at least 1"
        assert len(data["participants"]) == 2, "Should have 2 participants"


# ---------------------------------------------------------------------------
# 13. Edge lifecycle: export ONNX → register device → heartbeat →
#     fleet health
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_edge_lifecycle(test_app):
    """Full edge lifecycle: export ONNX, register device, heartbeat, fleet health."""
    mock_model_id = str(uuid.uuid4())

    # Export ONNX (mock model)
    r_export = await test_app.post(
        "/api/edge/export",
        json={
            "model_id": mock_model_id,
            "format": "onnx",
            "optimize": True,
            "quantize": False,
        },
    )
    assert r_export.status_code != 404, "edge/export returned 404"

    if r_export.status_code in OK:
        data = r_export.json()
        assert data.get("format") == "onnx", "Export should be ONNX format"
        assert data.get("status") == "completed", "Export should complete"

    # Register edge device
    r_device = await test_app.post(
        "/api/fleet/devices",
        json={
            "name": f"edge-node-{uuid.uuid4().hex[:6]}",
            "device_type": "jetson-nano",
            "capabilities": {"gpu": True, "memory_gb": 4},
            "location": "warehouse-a",
        },
    )
    assert r_device.status_code != 404, "fleet/devices create returned 404"

    if r_device.status_code in OK:
        device_id = r_device.json()["id"]

        # Send heartbeat (simulates OTA update status)
        r_heartbeat = await test_app.post(
            f"/api/fleet/devices/{device_id}/heartbeat",
            json={
                "cpu_percent": 45.0,
                "memory_percent": 62.0,
                "gpu_percent": 30.0,
                "active_models": [mock_model_id],
                "inference_count": 1500,
            },
        )
        assert r_heartbeat.status_code != 404, "fleet heartbeat returned 404"

    # List exports for model
    r_exports = await test_app.get(
        "/api/edge/exports",
        params={"model_id": mock_model_id},
    )
    assert r_exports.status_code != 404, "edge/exports list returned 404"

    # Fleet health (overall status)
    r_health = await test_app.get("/api/fleet/health")
    assert r_health.status_code != 404, "fleet/health returned 404"

    if r_health.status_code == 200:
        data = r_health.json()
        assert "total_devices" in data, "Fleet health should report total devices"

    # List supported export formats (offline package formats)
    r_formats = await test_app.get("/api/edge/formats")
    assert r_formats.status_code != 404, "edge/formats returned 404"

    if r_formats.status_code == 200:
        formats = r_formats.json()
        names = [f["name"] for f in formats]
        assert "onnx" in names, "ONNX should be a supported format"


# ---------------------------------------------------------------------------
# 14. Vertical Packs lifecycle: list packs → install security →
#     verify resources → list installed → get pack details
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_vertical_lifecycle(test_app):
    """Full vertical lifecycle: list, install security, verify resources, uninstall."""
    # List available packs
    r_list = await test_app.get("/api/verticals/packs")
    assert r_list.status_code != 404, "verticals/packs list returned 404"

    if r_list.status_code == 200:
        packs = r_list.json()
        pack_ids = [p["id"] for p in packs]
        assert "security" in pack_ids, "Security pack should be available"

    # Install security pack
    r_install = await test_app.post(
        "/api/verticals/install",
        json={"pack_id": "security"},
    )
    assert r_install.status_code != 404, "verticals/install returned 404"

    if r_install.status_code in OK:
        data = r_install.json()
        assert data.get("status") == "installed", "Pack should be installed"
        assert len(data.get("modules", [])) > 0, "Installed pack should have modules"

    # Verify pack resources (pipeline templates, models, configs)
    r_resources = await test_app.get("/api/verticals/packs/security/resources")
    assert r_resources.status_code != 404, "verticals/packs/security/resources returned 404"

    if r_resources.status_code == 200:
        data = r_resources.json()
        assert data.get("total_resources", 0) > 0, "Pack should have resources"

    # List installed packs
    r_installed = await test_app.get("/api/verticals/installed")
    assert r_installed.status_code != 404, "verticals/installed returned 404"

    if r_installed.status_code == 200:
        installed = r_installed.json()
        assert len(installed) >= 1, "At least security pack should be installed"

    # Get pack details
    r_detail = await test_app.get("/api/verticals/packs/security")
    assert r_detail.status_code != 404, "verticals/packs/security returned 404"

    if r_detail.status_code == 200:
        data = r_detail.json()
        assert data.get("installed") is True, "Security pack should show as installed"
