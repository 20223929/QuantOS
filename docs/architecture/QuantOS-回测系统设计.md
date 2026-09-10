# QuantOS Next 回测系统设计

## 1. 核心思想

采用事件驱动回测模型。

```
Historical Data
      |
Event Engine
      |
Strategy
      |
Trade Simulator
      |
Performance Analyzer
```

## 2. 功能

- 历史行情加载
- Tick/Bar回放
- 模拟撮合
- 手续费计算
- 滑点模拟

## 3. 输出指标

- 收益率
- 年化收益
- Sharpe
- 最大回撤
- 胜率
- 盈亏比

## 4. 实盘一致性

回测、模拟、实盘共享策略接口。