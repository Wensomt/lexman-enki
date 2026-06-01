"""Config flow for Lexman BLE Light."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import bluetooth
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_ADDRESS, CONF_HUE_OFFSET, CONF_NAME, DEFAULT_NAME, DOMAIN, SERVICE_UUID

_LOGGER = logging.getLogger(__name__)

MANUAL = "__manual__"


def _clean_address(address: str) -> str:
    return address.strip().upper()


class LexmanBleConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Lexman BLE Light."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery_info: bluetooth.BluetoothServiceInfoBleak | None = None

    async def async_step_bluetooth(
        self, discovery_info: bluetooth.BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle Bluetooth discovery."""
        self._discovery_info = discovery_info
        address = _clean_address(discovery_info.address)
        await self.async_set_unique_id(address)
        self._abort_if_unique_id_configured()
        self.context["title_placeholders"] = {
            "name": discovery_info.name or DEFAULT_NAME,
            "address": address,
        }
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Confirm Bluetooth discovery."""
        assert self._discovery_info is not None
        address = _clean_address(self._discovery_info.address)
        name = self._discovery_info.name or DEFAULT_NAME

        if user_input is not None:
            return self.async_create_entry(
                title=user_input.get(CONF_NAME, name),
                data={
                    CONF_ADDRESS: address,
                    CONF_NAME: user_input.get(CONF_NAME, name),
                    CONF_HUE_OFFSET: int(user_input.get(CONF_HUE_OFFSET, 0)),
                },
            )

        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": name, "address": address},
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=name): str,
                    vol.Optional(CONF_HUE_OFFSET, default=0): vol.All(int, vol.Range(min=-180, max=180)),
                }
            ),
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle manual setup from UI."""
        errors: dict[str, str] = {}

        if user_input is not None:
            selected = user_input.get("device")
            if selected == MANUAL:
                return await self.async_step_manual()

            address = _clean_address(selected or user_input.get(CONF_ADDRESS, ""))
            if not address:
                errors[CONF_ADDRESS] = "required"
            else:
                await self.async_set_unique_id(address)
                self._abort_if_unique_id_configured()
                name = user_input.get(CONF_NAME) or self._name_for_address(address) or DEFAULT_NAME
                return self.async_create_entry(
                    title=name,
                    data={
                        CONF_ADDRESS: address,
                        CONF_NAME: name,
                        CONF_HUE_OFFSET: int(user_input.get(CONF_HUE_OFFSET, 0)),
                    },
                )

        devices = self._discovered_devices()
        if devices:
            device_options = {MANUAL: "Wpisz adres ręcznie", **devices}
            schema = vol.Schema(
                {
                    vol.Required("device", default=next(iter(devices))): vol.In(device_options),
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                    vol.Optional(CONF_HUE_OFFSET, default=0): vol.All(int, vol.Range(min=-180, max=180)),
                }
            )
        else:
            schema = vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): str,
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                    vol.Optional(CONF_HUE_OFFSET, default=0): vol.All(int, vol.Range(min=-180, max=180)),
                }
            )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_manual(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manual address entry."""
        errors: dict[str, str] = {}
        if user_input is not None:
            address = _clean_address(user_input[CONF_ADDRESS])
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            name = user_input.get(CONF_NAME) or DEFAULT_NAME
            return self.async_create_entry(
                title=name,
                data={
                    CONF_ADDRESS: address,
                    CONF_NAME: name,
                    CONF_HUE_OFFSET: int(user_input.get(CONF_HUE_OFFSET, 0)),
                },
            )

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): str,
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                    vol.Optional(CONF_HUE_OFFSET, default=0): vol.All(int, vol.Range(min=-180, max=180)),
                }
            ),
            errors=errors,
        )

    @callback
    def _discovered_devices(self) -> dict[str, str]:
        """Return discovered BLE devices that look relevant."""
        found: dict[str, str] = {}
        for info in bluetooth.async_discovered_service_info(self.hass, connectable=True):
            name = info.name or ""
            service_uuids = {uuid.lower() for uuid in info.service_uuids or []}
            looks_like_bulb = (
                "rgb smart bulb" in name.lower()
                or SERVICE_UUID.lower() in service_uuids
                or "bulb" in name.lower()
            )
            if not looks_like_bulb:
                continue
            address = _clean_address(info.address)
            found[address] = f"{name or 'BLE device'} ({address}) RSSI {info.rssi}"
        return found

    @callback
    def _name_for_address(self, address: str) -> str | None:
        """Find discovered name for address."""
        for info in bluetooth.async_discovered_service_info(self.hass, connectable=True):
            if _clean_address(info.address) == address:
                return info.name
        return None
