import { useEffect, useState } from 'react';

export interface MarketTick {
  symbol: string;
  price: number;
  source?: string;
}

export function useMarketSocket(symbol: string) {
  const [tick, setTick] = useState<MarketTick | null>(null);

  useEffect(() => {
    if (!symbol) return;

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const socket = new WebSocket(`${protocol}://${window.location.host}/ws/market/${symbol}`);

    socket.onmessage = (event) => {
      try {
        setTick(JSON.parse(event.data));
      } catch {
        // ignore invalid payload
      }
    };

    return () => socket.close();
  }, [symbol]);

  return tick;
}
