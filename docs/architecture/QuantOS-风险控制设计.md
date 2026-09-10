# QuantOS Next 风险控制设计

## 1. 风控目标

保证策略运行安全，避免异常交易。

## 2. 风控模块

- 仓位限制
- 单品种限制
- 最大亏损限制
- 波动率控制
- Kill Switch

## 3. 风控流程

```
Strategy Signal
 |
Risk Check
 |
Order Gateway
 |
Exchange
```

## 4. 审计

记录策略、信号、订单、成交和风险事件。