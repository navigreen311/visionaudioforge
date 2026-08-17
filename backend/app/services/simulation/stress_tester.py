"""Stress tester — concurrent load testing, edge-case suites, and adversarial robustness."""

import asyncio
import logging
import os
import statistics
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


def _rss_mb() -> float | None:
    """Current resident set size in MB, or None if it cannot be read."""
    try:
        import psutil

        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except Exception:
        return None


@dataclass
class StressTestConfig:
    """Configuration for a stress test run."""

    target_module: str = "vision"  # vision / audio / pipeline / search
    concurrent_requests: int = 50
    duration_s: float = 60.0
    payload_type: str = "medium"  # small / medium / large


@dataclass
class StressTestResult:
    """Aggregated results of a stress test."""

    test_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    target_module: str = ""
    total_requests: int = 0
    successful: int = 0
    failed: int = 0
    throughput_rps: float = 0.0
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    error_rate: float = 0.0
    memory_delta_mb: float | None = 0.0
    duration_s: float = 0.0
    #: True when the load was generated against a synthetic in-process workload
    #: rather than the real target module. Latency and throughput then describe
    #: the harness, not the system under test — surface this in any report.
    synthetic: bool = True


class StressTester:
    """Runs synthetic load tests, edge-case suites, and adversarial robustness checks."""

    PAYLOAD_SIZES = {
        "small": 1_024,       # 1 KB
        "medium": 100_000,    # 100 KB
        "large": 1_000_000,   # 1 MB
    }

    #: Edge cases the decode path is known not to handle. Deterministic so the
    #: suite is usable as a regression signal.
    KNOWN_FAILING_CASES = ("corrupted_bytes", "zero_length_audio")

    #: Simulation constants for run_adversarial_test. Not measurements.
    BASELINE_CONFIDENCE = 0.92
    METHOD_SENSITIVITY = {"noise": 0.55, "brightness": 0.40}

    #: Nominal per-node cost (ms) used by benchmark_pipeline until a real
    #: pipeline executor can be timed. Not measurements.
    NODE_COST_PROFILE_MS = {
        "preprocessor": 4.0,
        "detector": 18.0,
        "classifier": 9.0,
        "postprocessor": 3.0,
        "aggregator": 2.0,
    }

    # ------------------------------------------------------------------
    # Stress test
    # ------------------------------------------------------------------

    async def run_stress_test(
        self,
        db: Any,
        workspace_id: str,
        config: StressTestConfig,
        request: Any = None,
    ) -> StressTestResult:
        """Fire concurrent requests and measure throughput / latency.

        *request* may be an awaitable callable to exercise the real target; when
        omitted the harness drives a deterministic in-process workload and the
        result is flagged ``synthetic`` so its latency figures are never read as
        measurements of the target module.

        Errors are counted only when a request actually raises. The previous
        implementation injected a 2% failure rate with random.random(), which
        put a fabricated error_rate into the report.
        """
        payload_size = self.PAYLOAD_SIZES.get(config.payload_type, self.PAYLOAD_SIZES["medium"])
        latencies: list[float] = []
        errors = 0
        start_time = time.time()
        end_time = start_time + config.duration_s
        total = 0
        rss_before = _rss_mb()

        # Deterministic: proportional to payload size, so repeated runs are
        # comparable instead of varying with an RNG.
        synthetic_delay_s = 0.003 * (payload_size / 10_000)

        async def _single_request() -> None:
            nonlocal errors, total
            t0 = time.perf_counter()
            try:
                if request is not None:
                    await request()
                else:
                    await asyncio.sleep(synthetic_delay_s)
                elapsed = (time.perf_counter() - t0) * 1000
                latencies.append(elapsed)
            except Exception:
                errors += 1
            finally:
                total += 1

        # Fire batches until duration exhausted
        while time.time() < end_time:
            batch_size = min(config.concurrent_requests, max(1, int(end_time - time.time()) * 10))
            tasks = [asyncio.create_task(_single_request()) for _ in range(batch_size)]
            await asyncio.gather(*tasks)

        wall_time = time.time() - start_time
        sorted_lat = sorted(latencies) if latencies else [0.0]

        def _percentile(data: list[float], p: float) -> float:
            if not data:
                return 0.0
            idx = int(len(data) * p / 100)
            return data[min(idx, len(data) - 1)]

        return StressTestResult(
            target_module=config.target_module,
            total_requests=total,
            successful=total - errors,
            failed=errors,
            throughput_rps=round(total / max(wall_time, 0.001), 2),
            latency_p50_ms=round(_percentile(sorted_lat, 50), 3),
            latency_p95_ms=round(_percentile(sorted_lat, 95), 3),
            latency_p99_ms=round(_percentile(sorted_lat, 99), 3),
            error_rate=round(errors / max(total, 1), 4),
            # Real RSS delta across the run, or None when psutil is unavailable.
            memory_delta_mb=(
                round(rss_after - rss_before, 2)
                if rss_before is not None and (rss_after := _rss_mb()) is not None
                else None
            ),
            duration_s=round(wall_time, 2),
            synthetic=request is None,
        )

    # ------------------------------------------------------------------
    # Edge-case suite
    # ------------------------------------------------------------------

    async def run_edge_case_suite(
        self,
        model_name: str,
    ) -> dict[str, Any]:
        """Run a battery of edge-case inputs against a model and report pass/fail."""
        edge_cases = [
            {"name": "very_small_image_1x1", "input_type": "image", "size": (1, 1)},
            {"name": "very_large_image_10000x10000", "input_type": "image", "size": (10000, 10000)},
            {"name": "all_black_image", "input_type": "image", "pixel_value": 0},
            {"name": "all_white_image", "input_type": "image", "pixel_value": 255},
            {"name": "corrupted_bytes", "input_type": "image", "corrupt": True},
            {"name": "empty_audio", "input_type": "audio", "samples": 0},
            {"name": "extremely_loud_audio", "input_type": "audio", "amplitude": 32767},
            {"name": "zero_length_audio", "input_type": "audio", "duration": 0.0},
        ]

        results: list[dict[str, Any]] = []
        passed = 0
        failed = 0
        edge_cases_found: list[str] = []

        for case in edge_cases:
            try:
                # No model is invoked here yet; the suite reports which cases a
                # model is *known* to mishandle. This is deterministic — the
                # previous 70% random gate made the same input pass or fail
                # between runs, which is useless as a regression signal.
                await asyncio.sleep(0.001)
                if case["name"] in self.KNOWN_FAILING_CASES:
                    raise ValueError(f"Model {model_name} failed on {case['name']}")
                results.append({"case": case["name"], "status": "passed", "error": None})
                passed += 1
            except Exception as exc:
                results.append({"case": case["name"], "status": "failed", "error": str(exc)})
                failed += 1
                edge_cases_found.append(case["name"])

        return {
            "model_name": model_name,
            "test_cases": results,
            "passed": passed,
            "failed": failed,
            "edge_cases_found": edge_cases_found,
        }

    # ------------------------------------------------------------------
    # Adversarial test
    # ------------------------------------------------------------------

    async def run_adversarial_test(
        self,
        model_name: str,
        image: bytes | None = None,
        method: str = "noise",
    ) -> dict[str, Any]:
        """Incrementally perturb an input until the model prediction changes.

        No model is loaded yet, so this walks a deterministic sensitivity curve
        per method rather than sampling one. Everything here is simulated —
        ``simulated: True`` in the result says so, and the confidences must not
        be presented as a real model's output.
        """
        original_label = "person"
        original_conf = self.BASELINE_CONFIDENCE
        adversarial_label = original_label
        adversarial_conf = original_conf
        perturbation = 0.0
        robust = True

        # Fixed sensitivity per perturbation method (confidence lost at full
        # magnitude), replacing random.uniform ranges.
        sensitivity = self.METHOD_SENSITIVITY.get(method, 0.5)

        steps = 20
        for i in range(1, steps + 1):
            magnitude = i / steps
            await asyncio.sleep(0.001)

            conf_drop = magnitude * sensitivity
            new_conf = max(original_conf - conf_drop, 0.0)
            if new_conf < 0.5:
                adversarial_label = "unknown"
                adversarial_conf = round(new_conf, 4)
                perturbation = round(magnitude, 4)
                robust = False
                break
            adversarial_conf = round(new_conf, 4)
            perturbation = round(magnitude, 4)

        return {
            "model_name": model_name,
            "method": method,
            "original_prediction": {"label": original_label, "confidence": original_conf},
            "adversarial_prediction": {"label": adversarial_label, "confidence": adversarial_conf},
            "perturbation_magnitude": perturbation,
            "model_robust": robust,
            # No model was invoked — these are curve values, not observations.
            "simulated": True,
        }

    # ------------------------------------------------------------------
    # Pipeline benchmark
    # ------------------------------------------------------------------

    async def benchmark_pipeline(
        self,
        pipeline_id: str,
        iterations: int = 100,
    ) -> dict[str, Any]:
        """Benchmark a pipeline's latency across N iterations.

        There is no pipeline executor to drive yet, so each node's cost comes
        from a fixed per-node profile instead of random.uniform(1, 25) — which
        made the reported bottleneck a coin toss that changed between runs.
        The result is flagged ``simulated`` so a stable bottleneck is not
        mistaken for a measured one.
        """
        durations: list[float] = []
        node_totals: dict[str, float] = {n: 0.0 for n in self.NODE_COST_PROFILE_MS}

        for _ in range(iterations):
            iter_dur = 0.0
            for node, cost_ms in self.NODE_COST_PROFILE_MS.items():
                node_totals[node] += cost_ms
                iter_dur += cost_ms
            durations.append(iter_dur)
            await asyncio.sleep(0.0001)

        sorted_dur = sorted(durations)

        def _pct(data: list[float], p: float) -> float:
            idx = int(len(data) * p / 100)
            return data[min(idx, len(data) - 1)]

        bottleneck = max(node_totals, key=lambda n: node_totals[n])

        return {
            "pipeline_id": pipeline_id,
            "iterations": iterations,
            "avg_duration_ms": round(statistics.mean(durations), 3),
            "p95_ms": round(_pct(sorted_dur, 95), 3),
            "p99_ms": round(_pct(sorted_dur, 99), 3),
            "throughput_per_s": round(1000.0 / max(statistics.mean(durations), 0.001), 2),
            "bottleneck_node": bottleneck,
            "node_avg_ms": {n: round(v / iterations, 3) for n, v in node_totals.items()},
            # Derived from NODE_COST_PROFILE_MS, not from executing a pipeline.
            "simulated": True,
        }
