"""Light platform for Lexman BLE Light."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_HS_COLOR, ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ADDRESS, CONF_HUE_OFFSET, DEFAULT_NAME, DOMAIN
from .controller import LexmanBleController, cmd_brightness, cmd_hs, cmd_power, cmd_white

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up light entity."""
    async_add_entities([LexmanBleLight(hass, entry)])


class LexmanBleLight(LightEntity):
    """Lexman RGB smart bulb controlled locally by BLE."""

    _attr_has_entity_name = True
    _attr_supported_color_modes = {ColorMode.HS}

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._address: str = entry.data[CONF_ADDRESS].upper()
        self._name: str = entry.data.get(CONF_NAME, DEFAULT_NAME)
        self._hue_offset: int = int(entry.data.get(CONF_HUE_OFFSET, 0))
        self._controller = LexmanBleController(hass, self._address, self._name)

        self._attr_unique_id = f"{self._address.replace(':', '').lower()}_light"
        self._attr_name = self._name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._address)},
            connections={(CONNECTION_BLUETOOTH, self._address)},
            manufacturer="Lexman / ADEO / Enki",
            model="RGB smart bulb BLE",
            name=self._name,
        )

        self._is_on = False
        self._available = True
        self._brightness = 255
        self._hs_color: tuple[float, float] = (0.0, 100.0)
        self._color_mode = ColorMode.HS

    @property
    def available(self) -> bool:
        """Return availability."""
        return self._available

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self._is_on

    @property
    def brightness(self) -> int:
        """Return brightness."""
        return self._brightness

    @property
    def hs_color(self) -> tuple[float, float]:
        """Return HS color."""
        return self._hs_color

    @property
    def color_mode(self) -> ColorMode:
        """Return current color mode."""
        return self._color_mode

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        commands: list[bytes] = [cmd_power(True)]

        if ATTR_BRIGHTNESS in kwargs:
            self._brightness = int(kwargs[ATTR_BRIGHTNESS])
            commands.append(cmd_brightness(self._brightness))

        if ATTR_HS_COLOR in kwargs:
            hue, sat = kwargs[ATTR_HS_COLOR]
            self._hs_color = (float(hue), float(sat))
            self._color_mode = ColorMode.HS

            # HA sends white from the color picker as very low saturation.
            # The bulb has a separate white command, so use it instead of a nearly-white color.
            if sat <= 4:
                commands.append(cmd_white(50))
            else:
                commands.append(cmd_hs(hue, sat, hue_offset=self._hue_offset))

        try:
            await self._controller.async_send(commands)
        except Exception:
            self._available = False
            self.async_write_ha_state()
            raise

        self._is_on = True
        self._available = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        try:
            await self._controller.async_send([cmd_power(False)])
        except Exception:
            self._available = False
            self.async_write_ha_state()
            raise

        self._is_on = False
        self._available = True
        self.async_write_ha_state()
