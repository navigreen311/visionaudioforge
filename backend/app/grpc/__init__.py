"""gRPC API layer for VisionAudioForge high-throughput inference and streaming."""

from app.grpc.server import VAFGRPCServer

__all__ = ["VAFGRPCServer"]
