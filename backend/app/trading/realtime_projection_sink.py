from __future__ import annotations

from app.trading.event_projection import TradingEventProjection
from app.trading.event_broadcast import trading_event_broadcaster


class RealtimeProjectionSink:
    """Publishes projected execution events to websocket subscribers."""

    def publish(self, event: TradingEventProjection | dict) -> int:
        payload = event.to_dict() if isinstance(event, TradingEventProjection) else event
        return trading_event_broadcaster.publish(payload)


realtime_projection_sink = RealtimeProjectionSink()
