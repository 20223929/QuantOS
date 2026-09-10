export function connectMarketSocket(
  onMessage: (data: unknown) => void
) {
  const ws = new WebSocket("ws://localhost:8000/ws/market");

  ws.onmessage = (event) => {
    onMessage(JSON.parse(event.data));
  };

  return ws;
}
