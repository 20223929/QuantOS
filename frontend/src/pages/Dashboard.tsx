import MarketCard from '../components/MarketCard'
import StrategyCard from '../components/StrategyCard'
import type { MarketTick } from '../hooks/useMarketSocket'

export default function Dashboard() {
  const tick: MarketTick | null = null

  return (
    <main className="dashboard">
      <h1>QuantOS</h1>
      <p>Lightweight Futures Quant Platform</p>
      <MarketCard tick={tick} />
      <StrategyCard />
    </main>
  )
}
