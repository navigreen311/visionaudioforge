from fastapi import WebSocket


class ConnectionManager:
    """WebSocket connection manager with channel-based routing."""

    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str) -> None:
        """Accept a WebSocket and add it to the specified channel."""
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = []
        self.active_connections[channel].append(websocket)

    def disconnect(self, websocket: WebSocket, channel: str) -> None:
        """Remove a WebSocket from the specified channel."""
        if channel in self.active_connections:
            self.active_connections[channel] = [
                conn
                for conn in self.active_connections[channel]
                if conn is not websocket
            ]
            if not self.active_connections[channel]:
                del self.active_connections[channel]

    async def broadcast(self, channel: str, message: dict) -> None:
        """Send a JSON message to all connections in a channel."""
        if channel not in self.active_connections:
            return
        dead: list[WebSocket] = []
        for connection in self.active_connections[channel]:
            try:
                await connection.send_json(message)
            except Exception:
                dead.append(connection)
        for conn in dead:
            self.disconnect(conn, channel)

    def get_connection_count(self, channel: str | None = None) -> int:
        """Return number of active connections, optionally filtered by channel."""
        if channel is not None:
            return len(self.active_connections.get(channel, []))
        return sum(len(conns) for conns in self.active_connections.values())


manager = ConnectionManager()
