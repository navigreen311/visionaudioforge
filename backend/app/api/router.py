from fastapi import APIRouter

from app.api.routes import (
    agents,
    alerts,
    annotate_studio,
    annotations,
    assets,
    audio,
    auth,
    byom,
    capture,
    command_center,
    dashboard,
    datasets,
    developer,
    edge,
    edge_fleet,
    evaluation,
    experiments,
    federated,
    governance,
    health,
    help,
    integrations,
    investigation,
    investigation_mock,
    knowledge_graph,
    marketplace,
    marketplace_stubs,
    memory,
    metrics,
    mobile,
    notifications,
    observability,
    pipeline,
    plugins,
    profile,
    registry,
    reviewops,
    runtime,
    safety,
    search,
    security,
    semantic_memory,
    settings_api_keys,
    settings_audit,
    settings_billing,
    settings_data,
    settings_extra,
    settings_stubs,
    settings_users,
    simulation,
    transfer,
    transform,
    validation,
    verticals,
    vision,
    workspaces,
)
from app.api.routes.vaf_v1 import vaf_v1_router

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(metrics.router)
api_router.include_router(auth.router)
api_router.include_router(vision.router)
api_router.include_router(audio.router)
api_router.include_router(transform.router)
api_router.include_router(transfer.router)
api_router.include_router(experiments.router)
api_router.include_router(registry.router)
api_router.include_router(search.router)
api_router.include_router(pipeline.router)
api_router.include_router(alerts.router)
api_router.include_router(agents.router)
api_router.include_router(assets.router)
api_router.include_router(datasets.router)
api_router.include_router(safety.router)
api_router.include_router(validation.router)
api_router.include_router(workspaces.router)
api_router.include_router(capture.router)
api_router.include_router(evaluation.router)
api_router.include_router(investigation.router)
api_router.include_router(investigation_mock.router)
api_router.include_router(annotate_studio.router)
api_router.include_router(annotations.router)
api_router.include_router(governance.router)
api_router.include_router(integrations.router)
api_router.include_router(observability.router)
api_router.include_router(runtime.router)
api_router.include_router(knowledge_graph.router)
api_router.include_router(semantic_memory.router)
api_router.include_router(memory.router)
api_router.include_router(command_center.router)
api_router.include_router(simulation.router)
api_router.include_router(reviewops.router)
api_router.include_router(edge.router)
api_router.include_router(edge_fleet.router)
api_router.include_router(verticals.router)
api_router.include_router(federated.router)
api_router.include_router(mobile.router)
api_router.include_router(notifications.router)
api_router.include_router(plugins.router)
api_router.include_router(developer.router)
api_router.include_router(dashboard.router)
api_router.include_router(security.router)

# Settings tabs. settings_api_keys / settings_billing / settings_audit own the
# paths the console's Settings page actually calls; the *_stubs / *_extra /
# *_data modules carry the remaining tabs.
api_router.include_router(settings_api_keys.router)
api_router.include_router(settings_users.router)
api_router.include_router(settings_billing.router)
api_router.include_router(settings_audit.router)
api_router.include_router(settings_stubs.router)
api_router.include_router(settings_extra.router)
api_router.include_router(settings_data.router)

# Marketplace. byom and marketplace mount ahead of marketplace_stubs so the
# concrete /byom/* and /plugins/* handlers are matched before the catalogue
# stubs' broader patterns.
api_router.include_router(byom.router)
api_router.include_router(marketplace.router)
api_router.include_router(marketplace_stubs.router)

api_router.include_router(help.router)
api_router.include_router(profile.router)

# VAF v1 — PAF integration mock surface (WS10/WS11). All routes mount under /api/v1/.
api_router.include_router(vaf_v1_router)
