import { wsBaseUrl } from "@/lib/api";

import { io, Socket } from "socket.io-client";

let socket: Socket | null = null;

export function getSocket(): Socket {
  if (!socket) {
    socket = io(`${wsBaseUrl()}/ws`, {
      autoConnect: false,
      transports: ["websocket"],
    });
  }
  return socket;
}

export function disconnectSocket(): void {
  if (socket) {
    socket.disconnect();
    socket = null;
  }
}
