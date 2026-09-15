import { useEffect, useRef, useState } from "react";
import { TradingEventSocket } from "../services/tradingEventSocket";

export interface TradingEvent {
  event_id: string;
  event_type: string;
  aggregate_id: string;
  payload: Record<string, unknown>;
}

export function useTradingEvents(url: string) {
  const [events, setEvents] = useState<TradingEvent[]>([]);
  const socketRef = useRef<TradingEventSocket | null>(null);

  useEffect(() => {
    const socket = new TradingEventSocket(url, (event: TradingEvent) => {
      setEvents((current) => [...current.slice(-99), event]);
    });

    socket.connect();
    socketRef.current = socket;

    return () => {
      socket.close();
      socketRef.current = null;
    };
  }, [url]);

  return {
    events,
    latestEvent: events[events.length - 1],
  };
}
