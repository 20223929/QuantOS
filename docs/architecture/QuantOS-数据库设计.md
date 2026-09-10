# QuantOS Next 数据库设计

## 1. 存储架构

- PostgreSQL：交易业务数据
- SQLite：本地配置
- Parquet：历史行情数据
- Redis：实时缓存

## 2. 核心数据表

### user

用户信息。

### strategy

策略定义和配置。

### backtest

回测任务和结果。

### order

订单记录。

### trade

成交记录。

### position

持仓记录。

## 3. 数据原则

交易数据不可修改，支持审计和复盘。