import { useEffect, useRef, useCallback, useState } from "react";

export interface WSMessage {
  type: string;
  progress?: number;
  current_step?: number;
  total_steps?: number;
  status?: string;
  message?: string;
  data?: unknown;
}

export function useWebSocket(
  runId: string | null,
  onMessage?: (msg: WSMessage) => void
) {
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null);

  const connect = useCallback(
    (id: string) => {
      if (wsRef.current) {
        wsRef.current.close();
      }

      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = "localhost:8000";
      const url = `${protocol}//${host}/ws/simulation/${id}`;
      const ws = new WebSocket(url);

      ws.onopen = () => {
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const msg: WSMessage = JSON.parse(event.data);
          setLastMessage(msg);
          onMessage?.(msg);
        } catch {
          // ignore non-JSON messages
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
      };

      ws.onerror = () => {
        setIsConnected(false);
      };

      wsRef.current = ws;
    },
    [onMessage]
  );

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  useEffect(() => {
    if (runId) {
      connect(runId);
    } else {
      disconnect();
    }
    return () => disconnect();
  }, [runId, connect, disconnect]);

  return { isConnected, lastMessage, disconnect };
}
