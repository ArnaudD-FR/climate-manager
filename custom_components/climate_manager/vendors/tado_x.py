# SPDX-License-Identifier: MIT
"""Tado X (tado_x custom integration) vendor.

Tado X exposes one cloud climate entity per room (zone) and the physical
"Radiator Valve X" devices without a climate entity of their own. The
offset is set per valve with tado_x.set_temperature_offset (device_id,
one decimal) and read back from the valve's temperature_offset sensor.

The same valves can also be added to HA over Matter (local, sub-minute
readings). A Matter device carries the valve serial as its
("matter", "serial_<serial>") identifier, which pairs it with its valve.
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from ..trv import is_trv_entity
from .base import CalibrationTarget, TRVVendor

_DOMAIN = "tado_x"
_VALVE_MODEL = "Radiator Valve X"
_OFFSET_SERVICE = "set_temperature_offset"


class TadoX(TRVVendor):
    """Tado X valves, optionally paired with their Matter entities."""

    label = "Tado X"
    platform = _DOMAIN
    accessory_models = frozenset({_VALVE_MODEL})
    pairable = True

    def calibration_targets(
        self,
        hass: HomeAssistant,
        area_id: str,
        entity_ids: list[str],
        mappings: dict[str, list[str]],
    ) -> list[CalibrationTarget]:
        """One target per valve of the area, else one per zone entity.

        A valve is compared with its own Matter entity (same serial) when
        the room has one, else with the zone's first paired Matter entity,
        else with the zone entity (cloud readings).
        """
        trvs = [e for e in entity_ids if is_trv_entity(hass, e)]
        zones = [e for e in trvs if self.owns(hass, e)]
        valves = self._valves(hass, area_id)
        if not valves:
            return [
                CalibrationTarget(
                    vendor=self,
                    key=zone,
                    name=zone.split(".", 1)[-1],
                    temp_entity_id=(mappings.get(zone) or [zone])[0],
                    entity_id=zone,
                )
                for zone in zones
            ]

        if zones:
            zone_entity: str | None = zones[0]
            fallback: str | None = (mappings.get(zones[0]) or zones)[0]
        else:
            zone_entity = fallback = trvs[0] if trvs else None
        candidates = trvs + [
            eid for zone in zones for eid in mappings.get(zone, [])
        ]
        by_serial = _matter_entities_by_serial(hass, candidates)

        targets = []
        for valve in valves:
            temp_entity = (
                next(
                    (
                        by_serial[serial]
                        for serial in _valve_serials(valve)
                        if serial in by_serial
                    ),
                    None,
                )
                or fallback
            )
            if temp_entity is None:
                continue
            targets.append(
                CalibrationTarget(
                    vendor=self,
                    key=valve.id,
                    name=valve.name_by_user or valve.name or valve.id,
                    temp_entity_id=temp_entity,
                    entity_id=zone_entity,
                    device_id=valve.id,
                )
            )
        return targets

    def read_offset(
        self, hass: HomeAssistant, target: CalibrationTarget
    ) -> float | None:
        """Valve: its temperature_offset sensor. Zone: the attribute."""
        if target.device_id is None:
            state = hass.states.get(target.key)
            if state is None:
                return None
            return _to_float(state.attributes.get("temperature_offset"))
        entity_reg = er.async_get(hass)
        for entry in er.async_entries_for_device(entity_reg, target.device_id):
            if entry.platform != _DOMAIN or entry.domain != "sensor":
                continue
            if not entry.unique_id.endswith("_temperature_offset"):
                continue
            state = hass.states.get(entry.entity_id)
            return _to_float(state.state) if state else None
        return None

    async def write_offset(
        self, hass: HomeAssistant, target: CalibrationTarget, offset: float
    ) -> None:
        """Call tado_x.set_temperature_offset (device_id, else entity_id).

        Silently skipped when the service is not registered, or when a
        zone entity is unavailable.
        """
        if not hass.services.has_service(_DOMAIN, _OFFSET_SERVICE):
            return
        if target.device_id is not None:
            data = {"device_id": target.device_id}
        else:
            state = hass.states.get(target.key)
            if state is None or state.state in ("unavailable", "unknown"):
                return
            data = {"entity_id": target.key}
        await hass.services.async_call(
            _DOMAIN,
            _OFFSET_SERVICE,
            # The Tado X API requires exactly one decimal place.
            {**data, "offset": round(offset, 1)},
            blocking=True,
        )

    def suggest_mappings(self, hass: HomeAssistant) -> dict[str, list[str]]:
        """Pair each zone entity with the Matter entities of its valves.

        A zone's valves are the devices connected through the zone device
        (via_device_id); their tado_x identifier is the serial.
        """
        entity_reg = er.async_get(hass)
        device_reg = dr.async_get(hass)
        by_serial = _matter_entities_by_serial(hass, list(entity_reg.entities))
        mappings: dict[str, list[str]] = {}
        for entry in entity_reg.entities.values():
            if entry.domain != "climate" or entry.platform != _DOMAIN:
                continue
            matter_eids = [
                by_serial[serial]
                for valve in device_reg.devices
                if valve.via_device_id == entry.device_id
                for serial in _valve_serials(valve)
                if serial in by_serial
            ]
            if matter_eids:
                mappings[entry.entity_id] = matter_eids
        return mappings

    def poll_interval(self, hass: HomeAssistant) -> int | None:
        """Scan interval of the tado_x coordinator (hass.data)."""
        entries = hass.config_entries.async_entries(_DOMAIN)
        if not entries:
            return None
        coordinator = hass.data.get(_DOMAIN, {}).get(entries[0].entry_id)
        interval = getattr(coordinator, "_scan_interval", None)
        return int(interval) if interval is not None else None

    def _valves(
        self, hass: HomeAssistant, area_id: str
    ) -> list[dr.DeviceEntry]:
        """Radiator Valve X devices of the tado_x config entries in area."""
        entry_ids = {
            e.entry_id for e in hass.config_entries.async_entries(_DOMAIN)
        }
        if not entry_ids:
            return []
        return [
            device
            for device in dr.async_get(hass).devices
            if device.area_id == area_id
            and device.config_entry_id in entry_ids
            and device.model == _VALVE_MODEL
        ]


def _valve_serials(device: dr.DeviceEntry) -> list[str]:
    """Serials of a Tado X device (its tado_x identifiers)."""
    return [value for domain, value in device.identifiers if domain == _DOMAIN]


def _matter_entities_by_serial(
    hass: HomeAssistant, entity_ids: list[str]
) -> dict[str, str]:
    """{serial: entity_id} for the Matter climate entities in entity_ids."""
    entity_reg = er.async_get(hass)
    device_reg = dr.async_get(hass)
    result: dict[str, str] = {}
    for entity_id in entity_ids:
        entry = entity_reg.async_get(entity_id)
        if (
            entry is None
            or entry.domain != "climate"
            or entry.platform != "matter"
            or entry.device_id is None
        ):
            continue
        device = device_reg.async_get(entry.device_id)
        if device is None:
            continue
        for domain, value in device.identifiers:
            if domain == "matter" and value.startswith("serial_"):
                result[value.removeprefix("serial_")] = entity_id
    return result


def _to_float(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
