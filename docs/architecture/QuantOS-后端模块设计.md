# QuantOS Next 后端模块设计

## 1. 后端技术架构

Backend 使用 Python FastAPI 构建。

分层：

```
API Layer
   |
Service Layer
   |
Engine Layer
   |
Adapter Layer
   |
Storage Layer
```

---

# 2. 模块划分

## app/api

提供 REST API 与 WebSocket 接口。

包含：

- market.py 行情接口
- strategy.py 策略接口
- backtest.py 回测接口
- account.py 账户接口

---

## engine

核心业务引擎。

### Market Engine

职责：

- 行情订阅
- Tick处理
- Bar聚合
- 实时推送

### Strategy Engine

职责：

- 策略加载
- 生命周期管理
- 信号计算
- 委托生成

### Backtest Engine

职责：

- 历史数据回放
- 模拟成交
- 收益统计

---

# 3. Adapter设计

核心系统不直接依赖第三方接口。

```
Strategy
   |
Interface
   |
TqSdk Adapter
```

未来支持：

- CTP
- IB
- Binance

---

# 4. 异步设计

采用 asyncio：

- 行情异步接收
- 策略异步计算
- WebSocket实时推送

---

# 5. 测试要求

所有核心模块必须具备 pytest 测试。

覆盖：

- 行情模拟
- 策略生命周期
- 回测结果
- 风控规则
