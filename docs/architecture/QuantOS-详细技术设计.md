# QuantOS Next 详细技术设计

## 1. 系统分层

```
API Layer
    |
Service Layer
    |
Engine Layer
    |
Adapter Layer
    |
Infrastructure
```

## 2. 通信设计

前端通过 REST 获取配置，通过 WebSocket 接收实时行情、订单和策略状态。

## 3. 服务模块

- 用户服务
- 行情服务
- 策略服务
- 回测服务
- 交易服务
- 风控服务

## 4. 异步模型

核心采用 asyncio 事件驱动模型，避免行情阻塞策略计算。

## 5. 扩展原则

所有外部依赖通过 Adapter 隔离，支持未来接入 CTP、IB 等交易接口。
