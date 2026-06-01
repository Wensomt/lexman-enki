"""Constants for Lexman BLE Light."""

DOMAIN = "lexman_ble_light"
PLATFORMS = ["light"]

CONF_ADDRESS = "address"
CONF_NAME = "name"
CONF_HUE_OFFSET = "hue_offset"

DEFAULT_NAME = "Lexman BLE Light"

SERVICE_UUID = "0000a100-1115-1000-0001-617573746f6d"
WRITE_UUID = "0000a101-1115-1000-0001-617573746f6d"
NOTIFY_UUID = "0000a102-1115-1000-0001-617573746f6d"

# Commands captured from the Leroy/Enki app.
CMD_POWER_STATUS = bytes.fromhex("00001002")
CMD_BRIGHTNESS_STATUS = bytes.fromhex("00001102")
CMD_COLOR_STATUS = bytes.fromhex("00001308")
CMD_WHITE_STATUS = bytes.fromhex("00001202")

CMD_ON = bytes.fromhex("0000100103010000")
CMD_OFF = bytes.fromhex("0000100103000000")

BRIGHTNESS_MIN = 0x15
BRIGHTNESS_MAX = 0xEF

# White-temperature range observed in HCI logs. Used only when HA sends white/low-saturation color.
WHITE_MIN = 0x00A6
WHITE_MAX = 0x0138
