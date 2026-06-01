"""BLE controller for Lexman RGB smart bulbs."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable

from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import (
    BRIGHTNESS_MAX,
    BRIGHTNESS_MIN,
    CMD_BRIGHTNESS_STATUS,
    CMD_COLOR_STATUS,
    CMD_OFF,
    CMD_ON,
    CMD_POWER_STATUS,
    CMD_WHITE_STATUS,
    WHITE_MAX,
    WHITE_MIN,
    WRITE_UUID,
)

_LOGGER = logging.getLogger(__name__)

INIT_COMMANDS = (
    CMD_POWER_STATUS,
    CMD_BRIGHTNESS_STATUS,
    CMD_COLOR_STATUS,
    CMD_WHITE_STATUS,
)


class LexmanBleController:
    """Small, short-lived BLE command sender.

    We intentionally do not keep a persistent BleakClient. Home Assistant's own
    Bluetooth docs recommend avoiding reused clients because BLE connections are
    fragile, especially on BlueZ and proxies.
    """

    def __init__(self, hass: HomeAssistant, address: str, name: str) -> None:
        self.hass = hass
        self.address = address.upper()
        self.name = name
        self._lock = asyncio.Lock()

    async def async_send(self, commands: Iterable[bytes], *, warmup: bool = True) -> None:
        """Send one or more commands to the bulb with retries and timeouts."""
        command_list = list(commands)
        if warmup:
            command_list = [*INIT_COMMANDS, *command_list]

        async with self._lock:
            last_error: Exception | None = None

            for attempt in range(1, 4):
                try:
                    await asyncio.wait_for(self._async_send_once(command_list), timeout=22)
                    return
                except (BleakError, OSError, TimeoutError, asyncio.TimeoutError) as err:
                    last_error = err
                    _LOGGER.warning(
                        "BLE command failed for %s attempt %s/3: %s: %s",
                        self.address,
                        attempt,
                        type(err).__name__,
                        err,
                    )
                    await asyncio.sleep(0.8)

            raise HomeAssistantError(
                f"Nie udało się wysłać komendy BLE do {self.name} ({self.address}): {last_error}"
            ) from last_error

    async def _async_send_once(self, commands: list[bytes]) -> None:
        """Connect, write, disconnect."""
        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if ble_device is None:
            raise HomeAssistantError(
                f"Nie widzę urządzenia BLE {self.address}. Obudź żarówkę, zbliż HA/BT i upewnij się, że aplikacja Enki jest zamknięta."
            )

        client: BleakClientWithServiceCache | None = None
        try:
            client = await establish_connection(
                BleakClientWithServiceCache,
                ble_device,
                self.name,
                self.address,
                timeout=15,
            )

            for cmd in commands:
                _LOGGER.debug("Lexman BLE write %s -> %s", self.address, cmd.hex())
                await client.write_gatt_char(WRITE_UUID, cmd, response=True)
                await asyncio.sleep(0.22)
        finally:
            if client is not None and client.is_connected:
                try:
                    await client.disconnect()
                except Exception as err:  # noqa: BLE001 - disconnect cleanup must not crash HA
                    _LOGGER.debug("Disconnect cleanup failed for %s: %s", self.address, err)


def cmd_power(on: bool) -> bytes:
    """Build ON/OFF command."""
    return CMD_ON if on else CMD_OFF


def cmd_brightness(ha_brightness: int) -> bytes:
    """Build brightness command from HA brightness 1..255."""
    value = max(1, min(255, int(ha_brightness)))
    raw = round(BRIGHTNESS_MIN + ((value - 1) * (BRIGHTNESS_MAX - BRIGHTNESS_MIN) / 254))
    raw = max(BRIGHTNESS_MIN, min(BRIGHTNESS_MAX, raw))
    return bytes([0x00, 0x00, 0x11, 0x01, 0x03, raw, 0x00, 0x00])


def cmd_hs(hue: float, saturation: float, *, hue_offset: int = 0) -> bytes:
    """Build color command.

    Captured format: 0000130704 HH SS 0000.
    HH behaves like hue around a color wheel. SS behaves like saturation.
    """
    hue = (float(hue) + hue_offset) % 360
    saturation = max(0.0, min(100.0, float(saturation)))

    hue_raw = round(hue / 360 * 255) & 0xFF
    sat_raw = round(saturation / 100 * 0xFE)
    sat_raw = max(0, min(0xFE, sat_raw))

    return bytes([0x00, 0x00, 0x13, 0x07, 0x04, hue_raw, sat_raw, 0x00, 0x00])


def cmd_white(percent: int = 50) -> bytes:
    """Build neutral white command from observed white-temperature range."""
    percent = max(0, min(100, int(percent)))
    raw = round(WHITE_MIN + (percent * (WHITE_MAX - WHITE_MIN) / 100))
    high = (raw >> 8) & 0xFF
    low = raw & 0xFF
    return bytes([0x00, 0x00, 0x12, 0x01, 0x04, high, low, 0x00, 0x00])
