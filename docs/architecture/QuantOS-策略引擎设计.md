# QuantOS Next 策略引擎设计

## 1. 设计目标

策略一次开发，支持：

- 回测
- 模拟交易
- 实盘交易

---

# 2. 生命周期

```
create
 |
init
 |
start
 |
on_tick
 |
on_bar
 |
on_order
 |
on_trade
 |
stop
```

---

# 3. 基础策略接口

```python
class Strategy:
    def init(self):
        pass

    def on_tick(self,tick):
        pass

    def on_bar(self,bar):
        pass

    def buy(self,symbol,volume):
        pass
```

---

# 4. 事件驱动

所有策略通过 Event Bus 接收：

- TickEvent
- BarEvent
- OrderEvent
- TradeEvent

---

# 5. 策略隔离

策略不得直接调用：

- TqSdk
- 数据库
- 网络接口

必须通过服务接口访问。
