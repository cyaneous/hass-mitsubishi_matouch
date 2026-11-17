"""Recognizing an MA Touch controller from its Bluetooth advertisement.

The controller advertises its local name and nothing else: no manufacturer data and
no service UUID. The name is user-configurable, so a renamed controller is recognized
by the `M/R_` prefix it keeps together with its Bluetooth address block.

This module imports nothing from Home Assistant.
"""

from __future__ import annotations

from collections.abc import Iterable

# Factory-named units advertise as "M/R_CT01MAU_<machex>" (and
# "M/R_CT01MA_<machex>" on some), so match the model designation as a substring.
MA_TOUCH_NAME_MATCH = "CT01MA"

# A renamed controller advertises as "M/R_<name>".
MA_TOUCH_RENAMED_NAME_PREFIX = "M/R_"

# Mitsubishi Electric address blocks seen on MA Touch controllers: 58:52:8A on the
# PAR-CT01MAU and 28:E9:8E on the TAR-CT01MAU (the PAR-CT01MAU as sold by Trane).
MA_TOUCH_ADDRESS_PREFIXES = (
    "28:E9:8E:",
    "58:52:8A:",
)

# A GATT service of the controller. Controllers do not advertise it; a scanner that
# has connected before can still report it.
MA_TOUCH_SERVICE_UUID = "0277df18-e796-11e6-bf01-fe55135034f3"


def is_matouch(name: str | None, address: str, service_uuids: Iterable[str] | None) -> bool:
    """Return whether an advertisement comes from an MA Touch controller."""

    if MA_TOUCH_SERVICE_UUID in (service_uuids or ()):
        return True

    name = (name or "").upper()
    if MA_TOUCH_NAME_MATCH in name:
        return True

    return name.startswith(MA_TOUCH_RENAMED_NAME_PREFIX) and address.upper().startswith(
        MA_TOUCH_ADDRESS_PREFIXES
    )
