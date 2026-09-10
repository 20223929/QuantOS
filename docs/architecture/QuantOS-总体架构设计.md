# QuantOS Next

## 轻量级期货量化交易平台总体架构设计

版本：v1.0.0

日期：2026-09

---

# 1. 项目定位

QuantOS Next 是面向个人量化研究员和小型交易团队的轻量级期货量化平台。

目标：打造类似 TradingView 的现代化体验，同时具备 TqSdk 行情接入、策略研发、历史回测、模拟交易和实盘交易能力。

核心能力：

- 实时行情
- K线展示
- 策略开发
- 策略回测
- 模拟交易
- 实盘交易
- 风险控制
- 交易分析

---

# 2. 总体设计原则

## 2.1 前后端分离

Frontend：React + TypeScript，负责 Apple 风格 UI、图表和交互。

Backend：Python FastAPI，负责行情、策略、回测、交易和风险控制。

## 2.2 策略统一模型

同一策略代码支持回测、模拟交易和实盘交易。

---

# 3. 系统总体架构

```
Browser
 |
React + TypeScript
 |
REST/WebSocket
 |
FastAPI Backend
 |
Market Engine / Strategy Engine / Backtest Engine
 |
Event Bus
 |
TqSdk / Data Layer / Risk Engine
 |
PostgreSQL + SQLite + Parquet
```

---

# 4. 技术选型

## 前端

- React
- TypeScript
- Vite
- TailwindCSS
- shadcn/ui
- ECharts
- TradingView Lightweight Charts

## 后端

- Python 3.12
- FastAPI
- asyncio
- SQLAlchemy
- pytest

## 数据

- PostgreSQL
- SQLite
- Parquet
- Redis

---

# 5. 核心模块

## Market Engine

负责行情订阅、Tick处理、Bar生成和实时推送。

## Strategy Engine

负责策略生命周期、信号计算和订单管理。

## Backtest Engine

负责历史回放、模拟成交和绩效分析。

## Risk Engine

负责仓位限制、亏损控制和紧急停止。

---

# 6. 演进路线

Phase 1：基础架构、前端UI、FastAPI、TqSdk行情、策略框架、回测框架。

Phase 2：实盘交易、风控、参数优化、交易报告。

Phase 3：AI策略助手、策略市场、云端运行。

---

QuantOS Next 的目标不是传统行情软件，而是轻量、现代、开发者友好的期货量化操作系统。
