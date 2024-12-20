"""Adapters for the btmatouch library."""

from datetime import datetime, time, timedelta

from construct_typed import Adapter, Context

__all__: list[str] = []


class _MATemperature(Adapter[bytes, bytes, float, float]):
    """Adapter to encode and decode temperature data."""

    def _encode(self, obj: float, _ctx: Context, _path: str) -> bytes:
        return self.encode(obj)

    def _decode(self, obj: bytes, _ctx: Context, _path: str) -> float:
        return self.decode(obj)

    @classmethod
    def encode(cls, value: float) -> bytes:
        return int(str(int(round(value*2)/2*10)), 16).to_bytes(2, "little")

    @classmethod
    def decode(cls, value: bytes) -> float:
        return float(bytes(reversed(value)).hex())/10

