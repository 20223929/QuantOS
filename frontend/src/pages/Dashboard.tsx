import MarketCard from '../components/MarketCard'
import StrategyCard from '../components/StrategyCard'

export default function Dashboard() {
  return (
    <main className="dashboard">
      <h1>QuantOS</h1>
      <p>Lightweight Futures Quant Platform</p>
      <MarketCard />
      <StrategyCard />
    </main>
  )
}
