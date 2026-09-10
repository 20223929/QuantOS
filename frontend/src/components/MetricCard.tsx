export function MetricCard({title, value}:{title:string,value:string}) {
  return <div className="rounded-2xl p-4 shadow-sm"><div>{title}</div><strong>{value}</strong></div>
}
