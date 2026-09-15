import MarketCard from '../components/MarketCard'
import StrategyCard from '../components/StrategyCard'
import type { MarketTick } from '../hooks/useMarketSocket'
import { useTradingEvents } from '../hooks/useTradingEvents'

export default function Dashboard() {
  const tick: MarketTick | null = null
  const { events, latestEvent } = useTradingEvents('ws://localhost:8000/ws/trading/events')

  return (
    <main className="dashboard">
      <h1>QuantOS</h1>
      <p>Lightweight Futures Quant Platform</p>
      <MarketCard tick={tick} />
      <StrategyCard />

      <section className="trading-events">
        <h2>Realtime Trading Events</h2>
        {latestEvent && (
          <div>
            <strong>{latestEvent.event_type}</strong>
            <span>{latestEvent.aggregate_id}</span>
          </div>
        )}
        <ul>
          {events.map((event) => (
            <li key={event.event_id}>
              {event.event_type} - {event.aggregate_id}
            </li>
          ))}
        </ul>
      </section>
    </main>
  )
}
