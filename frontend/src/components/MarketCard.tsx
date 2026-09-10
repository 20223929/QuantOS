import type { MarketTick } from '../hooks/useMarketSocket';

export default function MarketCard({ tick }: { tick: MarketTick | null }) {
  return (
    <section>
      <h2>Market</h2>
      <div>Symbol: {tick?.symbol ?? '--'}</div>
      <div>Price: {tick?.price ?? '--'}</div>
      <div>Source: {tick?.source ?? '--'}</div>
    </section>
  );
}
