import { FormEvent, useEffect, useState } from 'react'

type Strategy = { name: string; running: boolean }
type Result = Record<string, unknown>

const API = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) throw new Error(await response.text())
  return response.json() as Promise<T>
}

function App() {
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [positions, setPositions] = useState<Record<string, number>>({})
  const [orders, setOrders] = useState<Record<string, Result>>({})
  const [message, setMessage] = useState('Ready')
  const [symbol, setSymbol] = useState('SHFE.rb')
  const [side, setSide] = useState('BUY')
  const [volume, setVolume] = useState(1)
  const [price, setPrice] = useState(0)
  const [backtest, setBacktest] = useState<Result | null>(null)

  const refresh = async () => {
    try {
      const [strategyData, positionData, orderData] = await Promise.all([
        request<{ strategies: Strategy[] }>('/strategy/list'),
        request<{ positions: Record<string, number> }>('/trading/positions'),
        request<{ orders: Record<string, Result> }>('/trading/orders'),
      ])
      setStrategies(strategyData.strategies)
      setPositions(positionData.positions)
      setOrders(orderData.orders)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'API unavailable')
    }
  }

  useEffect(() => { void refresh() }, [])

  const submitOrder = async (event: FormEvent) => {
    event.preventDefault()
    try {
      const data = await request<{ order: Result; success: boolean; message: string }>('/trading/orders', {
        method: 'POST',
        body: JSON.stringify({ symbol, side, volume, price }),
      })
      setMessage(data.message)
      await refresh()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Order failed')
    }
  }

  const runBacktest = async () => {
    const values = [3200, 3198, 3202, 3205, 3210, 3214, 3217, 3215, 3212, 3207, 3202, 3197, 3193, 3198, 3203, 3208, 3214, 3220, 3224, 3228, 3223, 3218, 3212, 3206, 3200]
    try {
      const data = await request<Result>('/backtest/run', {
        method: 'POST',
        body: JSON.stringify({ bars: values.map(close => ({ close })), initial_capital: 100000 }),
      })
      setBacktest(data)
      setMessage('Backtest completed')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Backtest failed')
    }
  }

  const toggleStrategy = async (strategy: Strategy) => {
    try {
      const action = strategy.running ? 'stop' : 'start'
      await request(`/strategy/${action}/${strategy.name}`, { method: 'POST' })
      setMessage(`${strategy.name} ${action}ed`)
      await refresh()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Strategy action failed')
    }
  }

  return (
    <div className="shell">
      <header className="header">
        <div>
          <p className="eyebrow">QuantOS Next · futures quant platform</p>
          <h1>Trading Console</h1>
          <p className="subtitle">Market · Strategy · Risk · Execution · Backtest</p>
        </div>
        <div className="status">{message}</div>
      </header>

      <section className="grid">
        <article className="card">
          <h2>Strategies</h2>
          <div className="list">
            {strategies.length === 0 ? <span className="muted">No strategies registered</span> : strategies.map(strategy => (
              <div className="item" key={strategy.name}>
                <span>{strategy.name}</span>
                <button className="btn secondary" onClick={() => void toggleStrategy(strategy)}>
                  {strategy.running ? 'Stop' : 'Start'}
                </button>
              </div>
            ))}
          </div>
        </article>

        <article className="card">
          <h2>Live state</h2>
          <div className="row">
            <div><div className="metric">{Object.keys(positions).length}</div><div className="muted">symbols held</div></div>
            <div><div className="metric">{Object.keys(orders).length}</div><div className="muted">orders</div></div>
          </div>
          <pre>{JSON.stringify({ positions, orders }, null, 2)}</pre>
        </article>

        <article className="card wide">
          <h2>Paper order</h2>
          <form className="form" onSubmit={submitOrder}>
            <div className="field"><label>Symbol</label><input value={symbol} onChange={e => setSymbol(e.target.value)} /></div>
            <div className="field"><label>Side</label><select value={side} onChange={e => setSide(e.target.value)}><option>BUY</option><option>SELL</option></select></div>
            <div className="field"><label>Volume</label><input type="number" min="1" value={volume} onChange={e => setVolume(Number(e.target.value))} /></div>
            <div className="field"><label>Price · 0 = market</label><input type="number" step="0.01" value={price} onChange={e => setPrice(Number(e.target.value))} /></div>
            <div className="row"><button className="btn" type="submit">Submit order</button><button className="btn secondary" type="button" onClick={() => void refresh()}>Refresh</button></div>
          </form>
        </article>

        <article className="card wide">
          <div className="row" style={{ justifyContent: 'space-between' }}>
            <h2>Backtest</h2>
            <button className="btn" onClick={() => void runBacktest()}>Run sample MA cross</button>
          </div>
          {backtest ? <pre>{JSON.stringify(backtest, null, 2)}</pre> : <p className="muted">Run a sample dataset to verify the strategy → engine → metrics path.</p>}
        </article>
      </section>
    </div>
  )
}

export default App
