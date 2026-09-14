from __future__ import annotations

import os
from typing import Any

from app.broker.paper_broker import PaperBroker
from app.broker.tqsdk_broker import TqSdkBroker


class BrokerFactory:
    """Construct paper/live brokers without coupling the API to vendor SDK setup."""

    @staticmethod
    def create(mode: str | None = None, api: Any | None = None):
        selected = (mode or os.getenv("QUANTOS_BROKER", "paper")).strip().lower()
        if selected == "paper":
            return PaperBroker()
        if selected == "tqsdk":
            if api is None:
                raise RuntimeError("TqSdk broker requires an initialized TqApi instance")
            return TqSdkBroker(api=api)
        raise ValueError(f"unsupported broker mode: {selected}")
