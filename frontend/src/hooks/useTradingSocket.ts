import { useEffect, useState } from "react";

export interface TradingEvent {
  event: string;
  [key: string]: unknown;
}

export function useTradingSocket(url = "/ws/trading") {
  const [events, setEvents] = useState<TradingEvent[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const socket = new WebSocket(url);

    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onmessage = (message) => {
      try {
        const data = JSON.parse(message.data) as TradingEvent;
        setEvents((items) => [...items.slice(-49), data]);
      } catch {
        // ignore invalid websocket messages
      }
    };

    return () => socket.close();
  }, [url]);

  return { events, connected };
}
