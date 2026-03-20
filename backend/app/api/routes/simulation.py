"""API routes for the Simulation Lab — scenario generation, stress testing, adversarial robustness."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.services.simulation.scenario_generator import ScenarioGenerator
from app.services.simulation.stress_tester import StressTester, StressTestConfig
from app.services.simulation.runner import SimulationRunner

router = APIRouter(prefix="/api/simulation", tags=["simulation"])

_generator = ScenarioGenerator()
_tester = StressTester()
_runner = SimulationRunner()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class ScenarioRequest(BaseModel):
    type: str
    params: dict[str, Any] | None = None


class ScenarioOut(BaseModel):
    scenario_id: str
    type: str
    events: list[dict[str, Any]]
    duration_s: float
    description: str


class SimulationRunRequest(BaseModel):
    workspace_id: str
    scenario: dict[str, Any]


class SimulationRunOut(BaseModel):
    simulation_id: str
    events_injected: int
    alerts_triggered: int
    duration_s: float
    timeline: list[dict[str, Any]]


class StressTestRequest(BaseModel):
    target_module: str = "vision"
    concurrent_requests: int = Field(default=50, ge=10, le=1000)
    duration_s: float = Field(default=60.0, ge=30, le=300)
    payload_type: str = "medium"


class StressTestOut(BaseModel):
    test_id: str
    target_module: str
    total_requests: int
    successful: int
    failed: int
    throughput_rps: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    error_rate: float
    memory_delta_mb: float
    duration_s: float


class EdgeCaseRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    model_name: str


class EdgeCaseOut(BaseModel):
    model_config = {"protected_namespaces": ()}
    model_name: str
    test_cases: list[dict[str, Any]]
    passed: int
    failed: int
    edge_cases_found: list[str]


class AdversarialOut(BaseModel):
    model_config = {"protected_namespaces": ()}
    model_name: str
    method: str
    original_prediction: dict[str, Any]
    adversarial_prediction: dict[str, Any]
    perturbation_magnitude: float
    model_robust: bool


class BenchmarkRequest(BaseModel):
    pipeline_id: str
    iterations: int = Field(default=100, ge=1, le=10000)


class BenchmarkOut(BaseModel):
    pipeline_id: str
    iterations: int
    avg_duration_ms: float
    p95_ms: float
    p99_ms: float
    throughput_per_s: float
    bottleneck_node: str
    node_avg_ms: dict[str, float]


class CompareRequest(BaseModel):
    simulation_ids: list[str]


class CompareOut(BaseModel):
    comparison: list[dict[str, Any]]


class SimulationReportOut(BaseModel):
    simulation_id: str
    scenario: dict[str, Any]
    results: dict[str, Any]
    alerts: list[dict[str, Any]]
    missed_detections: list[str]
    false_alarms: list[str]
    recommendations: list[str]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/scenarios/generate", response_model=ScenarioOut)
async def generate_scenario(body: ScenarioRequest) -> ScenarioOut:
    """Generate a synthetic incident scenario."""
    try:
        result = _generator.generate_scenario(body.type, body.params)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ScenarioOut(**result)


@router.post("/run", response_model=SimulationRunOut)
async def run_simulation(
    body: SimulationRunRequest,
    db: AsyncSession = Depends(get_db),
) -> SimulationRunOut:
    """Run a simulation by injecting scenario events."""
    result = await _runner.run_simulation(db, body.workspace_id, body.scenario)
    return SimulationRunOut(**result)


@router.post("/stress-test", response_model=StressTestOut)
async def run_stress_test(
    body: StressTestRequest,
    db: AsyncSession = Depends(get_db),
) -> StressTestOut:
    """Run a concurrent stress test against a target module."""
    if body.target_module not in ("vision", "audio", "pipeline", "search"):
        raise HTTPException(status_code=400, detail="target_module must be one of: vision, audio, pipeline, search")
    config = StressTestConfig(
        target_module=body.target_module,
        concurrent_requests=body.concurrent_requests,
        duration_s=body.duration_s,
        payload_type=body.payload_type,
    )
    result = await _tester.run_stress_test(db, "default-workspace", config)
    return StressTestOut(
        test_id=result.test_id,
        target_module=result.target_module,
        total_requests=result.total_requests,
        successful=result.successful,
        failed=result.failed,
        throughput_rps=result.throughput_rps,
        latency_p50_ms=result.latency_p50_ms,
        latency_p95_ms=result.latency_p95_ms,
        latency_p99_ms=result.latency_p99_ms,
        error_rate=result.error_rate,
        memory_delta_mb=result.memory_delta_mb,
        duration_s=result.duration_s,
    )


@router.post("/edge-cases", response_model=EdgeCaseOut)
async def run_edge_cases(body: EdgeCaseRequest) -> EdgeCaseOut:
    """Run edge-case test suite against a model."""
    result = await _tester.run_edge_case_suite(body.model_name)
    return EdgeCaseOut(**result)


@router.post("/adversarial", response_model=AdversarialOut)
async def run_adversarial(
    model_name: str = Form(...),
    method: str = Form(default="noise"),
    file: UploadFile = File(None),
) -> AdversarialOut:
    """Run adversarial robustness test on an image."""
    image_bytes = await file.read() if file else None
    result = await _tester.run_adversarial_test(model_name, image_bytes, method)
    return AdversarialOut(**result)


@router.post("/benchmark", response_model=BenchmarkOut)
async def run_benchmark(body: BenchmarkRequest) -> BenchmarkOut:
    """Benchmark a pipeline's latency."""
    result = await _tester.benchmark_pipeline(body.pipeline_id, body.iterations)
    return BenchmarkOut(**result)


@router.get("/report/{simulation_id}", response_model=SimulationReportOut)
async def get_report(
    simulation_id: str,
    db: AsyncSession = Depends(get_db),
) -> SimulationReportOut:
    """Get a detailed simulation report."""
    try:
        result = await _runner.get_simulation_report(db, simulation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return SimulationReportOut(**result)


@router.post("/compare", response_model=CompareOut)
async def compare_simulations(
    body: CompareRequest,
    db: AsyncSession = Depends(get_db),
) -> CompareOut:
    """Compare multiple simulation runs."""
    if len(body.simulation_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 simulation IDs required")
    result = await _runner.compare_simulations(db, body.simulation_ids)
    return CompareOut(**result)
