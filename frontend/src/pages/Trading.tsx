import { useTradingSocket } from "../hooks/useTradingSocket";

export default function Trading() {
  const { events, connected } = useTradingSocket();

  return (
    <main>
      <h1>Trading Terminal</h1>

      <section>
        <h2>Connection</h2>
        <p>{connected ? "Connected" : "Disconnected"}</p>
      </section>

      <section>
        <h2>Realtime Events</h2>
        {events.length === 0 ? (
          <p>No events</p>
        ) : (
          events.map((event, index) => (
            <pre key={index}>{JSON.stringify(event, null, 2)}</pre>
          ))
        )}
      </section>
    </main>
  );
}
