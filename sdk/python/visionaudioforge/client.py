"""Main VisionAudioForge client."""

from __future__ import annotations

from typing import Any

import httpx

from .exceptions import (
    AuthenticationError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    ServerError,
    VAFError,
    ValidationError,
)


_ERROR_MAP: dict[int, type[VAFError]] = {
    401: AuthenticationError,
    403: PermissionDeniedError,
    404: NotFoundError,
    422: ValidationError,
    429: RateLimitError,
    500: ServerError,
}


class VAFClient:
    """Async client for the VisionAudioForge REST API.

    Usage::

        async with VAFClient(base_url="http://localhost:8000", api_key="key") as client:
            result = await client.vision.analyze("photo.jpg", ["detect"])
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: str | None = None,
        token: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.token = token
        self._http = httpx.AsyncClient(base_url=self.base_url, timeout=timeout)

        # Lazy sub-client caches
        self._vision: VisionClient | None = None
        self._audio: AudioClient | None = None
        self._models: ModelClient | None = None
        self._search: SearchClient | None = None
        self._pipeline: PipelineClient | None = None
        self._agents: AgentClient | None = None
        self._datasets: DatasetClient | None = None
        self._alerts: AlertClient | None = None
        self._assets: AssetClient | None = None
        self._transform: TransformClient | None = None

    # -- Auth ----------------------------------------------------------------

    async def login(self, email: str, password: str) -> dict[str, Any]:
        """Authenticate with email/password and store the JWT token."""
        resp = await self._request(
            "POST", "/api/v1/auth/login", json={"email": email, "password": password}
        )
        self.token = resp.get("access_token") or resp.get("token")
        return resp

    # -- Health --------------------------------------------------------------

    async def health(self) -> dict[str, Any]:
        """Check API health."""
        return await self._request("GET", "/api/v1/health")

    # -- Core HTTP -----------------------------------------------------------

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Send an authenticated request and handle errors."""
        headers = kwargs.pop("headers", {})
        if self.token:
            headers.setdefault("Authorization", f"Bearer {self.token}")
        elif self.api_key:
            headers.setdefault("X-API-Key", self.api_key)

        response = await self._http.request(method, path, headers=headers, **kwargs)

        if response.status_code >= 400:
            detail = None
            try:
                detail = response.json()
            except Exception:
                detail = response.text
            exc_cls = _ERROR_MAP.get(response.status_code, VAFError)
            message = (
                detail.get("detail", str(detail))
                if isinstance(detail, dict)
                else str(detail)
            )
            raise exc_cls(message=message, detail=detail)

        if response.status_code == 204:
            return {}

        return response.json()

    # -- Lifecycle -----------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()

    async def __aenter__(self) -> VAFClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    # -- Sub-client properties (lazy) ----------------------------------------

    @property
    def vision(self) -> VisionClient:
        if self._vision is None:
            from .vision import VisionClient
            self._vision = VisionClient(self)
        return self._vision

    @property
    def audio(self) -> AudioClient:
        if self._audio is None:
            from .audio import AudioClient
            self._audio = AudioClient(self)
        return self._audio

    @property
    def models(self) -> ModelClient:
        if self._models is None:
            from .models import ModelClient
            self._models = ModelClient(self)
        return self._models

    @property
    def search(self) -> SearchClient:
        if self._search is None:
            from .search import SearchClient
            self._search = SearchClient(self)
        return self._search

    @property
    def pipeline(self) -> PipelineClient:
        if self._pipeline is None:
            from .pipeline import PipelineClient
            self._pipeline = PipelineClient(self)
        return self._pipeline

    @property
    def agents(self) -> AgentClient:
        if self._agents is None:
            from .agents import AgentClient
            self._agents = AgentClient(self)
        return self._agents

    @property
    def datasets(self) -> DatasetClient:
        if self._datasets is None:
            from .datasets import DatasetClient
            self._datasets = DatasetClient(self)
        return self._datasets

    @property
    def alerts(self) -> AlertClient:
        if self._alerts is None:
            from .alerts import AlertClient
            self._alerts = AlertClient(self)
        return self._alerts

    @property
    def assets(self) -> AssetClient:
        if self._assets is None:
            from .assets import AssetClient
            self._assets = AssetClient(self)
        return self._assets

    @property
    def transform(self) -> TransformClient:
        if self._transform is None:
            from .transform import TransformClient
            self._transform = TransformClient(self)
        return self._transform
