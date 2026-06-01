# Lexman BLE Light — custom component for Home Assistant

Lokalna integracja BLE dla żarówki Lexman/ADEO/Enki widocznej jako `RGB smart bulb`.

## Co obsługuje

- ON/OFF
- brightness
- color picker HS/RGB w Home Assistant
- biały kolor przez osobną komendę white, gdy saturacja z HA jest bardzo niska
- wybór urządzenia z listy Bluetooth albo ręczne wpisanie adresu BLE
- krótkie połączenia BLE z retry, bez trzymania stałego połączenia

## Instalacja

Skopiuj folder:

```text
custom_components/lexman_ble_light
```

do:

```text
/config/custom_components/lexman_ble_light
```

Potem:

```bash
ha core restart
```

W HA:

```text
Ustawienia → Urządzenia i usługi → Dodaj integrację → Lexman BLE Light
```

Jeśli nie widzisz żarówki, zamknij aplikację Enki/Leroy w telefonie, wyłącz Bluetooth w telefonie i zbliż żarówkę do adaptera Bluetooth HA.

## Korekta czerwonego / palety

W formularzu jest `hue_offset`. Jeśli czerwony wychodzi jako pomarańczowy, spróbuj np. `-15`, `-25`, `+15`, aż odcienie będą bliżej aplikacji.

## Uwaga

To jest wersja testowa pod jeden protokół BLE:

- write UUID: `0000a101-1115-1000-0001-617573746f6d`
- notify UUID: `0000a102-1115-1000-0001-617573746f6d`
