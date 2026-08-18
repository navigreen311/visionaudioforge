"""Simulation runs and their saved scenarios.

A simulation run is a result someone waited for: replay, comparison and the
report all read it back by id. Held in a module-level dict, every one of those
raised "Simulation not found" after a restart even though the run had
completed successfully.
"""

from sqlalchemy import Column, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID

from app.models.base import Base, TimestampMixin, UUIDMixin


class SimulationScenario(UUIDMixin, TimestampMixin, Base):
    """A saved scenario definition that runs are launched from."""

    __tablename__ = "simulation_scenarios"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True
    )
    name = Column(String(200), nullable=False, default="")
    scenario_type = Column(String(64), nullable=False, default="")
    definition = Column(JSON, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_simulation_scenarios_workspace", "workspace_id"),
    )


class SimulationRun(UUIDMixin, TimestampMixin, Base):
    """One executed simulation and its recorded outcome."""

    __tablename__ = "simulation_runs"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True
    )
    # The scenario as it was at run time. Stored on the run rather than
    # referenced, so replaying an old run reproduces what it actually ran,
    # not whatever the scenario has since been edited into.
    scenario = Column(JSON, nullable=False, default=dict)
    events_injected = Column(Integer, nullable=False, default=0)
    alerts_triggered = Column(Integer, nullable=False, default=0)
    duration_s = Column(Float, nullable=False, default=0.0)
    timeline = Column(JSON, nullable=False, default=list)

    # The /api/simulation routes record a richer, differently-shaped run than
    # SimulationRunner does. Rather than a second table, that whole record
    # lives here and the typed columns above stay the runner's summary.
    scenario_id = Column(UUID(as_uuid=True), nullable=True)
    label = Column(String(200), nullable=True)
    status = Column(String(32), nullable=False, default="completed")
    result = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_simulation_runs_workspace", "workspace_id"),
    )
