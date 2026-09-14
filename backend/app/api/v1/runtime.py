from fastapi import APIRouter, HTTPException

from app.adapters.tqsdk_adapter import TqSdkAdapter
from app.engine.strategy_engine import StrategyEngine
from app.risk.controller import RiskController
from app.risk.limit import RiskLimit
from app.strategies.ma_cross import MACrossStrategy
from app.trading.execution_engine import TradingExecutionEngine
from app.broker.paper_broker import PaperBroker
from app.trading.runtime import StrategyRuntime

router = APIRouter(prefix="/runtime", tags=["runtime"])

market_adapter = TqSdkAdapter()
broker = PaperBroker()
risk_controller = RiskController(RiskLimit(max_position=100, max_drawdown=0.2))
execution_engine = TradingExecutionEngine(broker, risk_controller)
strategy_engine = StrategyEngine()
strategy_engine.register(MACrossStrategy())
runtimes: dict[str, StrategyRuntime] = {}


@router.post("/{name}/start")
async def start_runtime(name: str, symbol: str = "SHFE.rb", duration_seconds: int = 60):
    strategy = strategy_engine.strategies.get(name)
    if strategy is None:
        raise HTTPException(status_code=404, detail=f"strategy not found: {name}")
    runtime = runtimes.get(name)
    if runtime is None:
        runtime = StrategyRuntime(market_adapter, strategy, execution_engine, symbol, duration_seconds)
        runtimes[name] = runtime
    await runtime.start()
    return runtime.status()


@router.post("/{name}/stop")
async def stop_runtime(name: str):
    runtime = runtimes.get(name)
    if runtime is None:
        raise HTTPException(status_code=404, detail=f"runtime not found: {name}")
    await runtime.stop()
    return runtime.status()


@router.get("/{name}")
async def runtime_status(name: str):
    runtime = runtimes.get(name)
    if runtime is None:
        raise HTTPException(status_code=404, detail=f"runtime not found: {name}")
    return runtime.status()
