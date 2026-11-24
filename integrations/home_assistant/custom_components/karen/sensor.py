"""Persist the time of actual mobile GPS reports, never coordinates or addresses.

HA restores mobile tracker coordinates on restart. Its new state timestamp is
not evidence of a fresh GPS fix; these sensors avoid presenting it as current.
"""
from datetime import datetime, timezone
import math
import time

from homeassistant.components.mobile_app.const import SIGNAL_LOCATION_UPDATE
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.storage import Store


async def async_setup_entry(hass, entry, async_add_entities):
    store = Store(hass, 1, 'karen_location_reports')
    reports = await store.async_load() or {}
    entities = []
    for record in er.async_get(hass).entities.values():
        if record.platform != 'mobile_app' or record.domain != 'device_tracker' or record.disabled:
            continue
        mobile_entry = hass.config_entries.async_get_entry(record.config_entry_id)
        if mobile_entry:
            name = mobile_entry.data.get('device_name', record.entity_id)
            entities.append(KarenLocationReport(record.entity_id, mobile_entry.entry_id, name, reports, store))
    async_add_entities(entities)


class KarenLocationReport(SensorEntity):
    _attr_should_poll = False
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, tracker, mobile_id, name, reports, store):
        self.tracker, self.mobile_id, self.reports, self.store = tracker, mobile_id, reports, store
        self._attr_name = 'Karen · ubicación · ' + name
        self._attr_unique_id = 'karen-location-' + mobile_id
        self._attr_extra_state_attributes = {'location_tracker': tracker}

    @property
    def native_value(self):
        stamp = self.reports.get(self.mobile_id)
        return datetime.fromtimestamp(stamp, timezone.utc) if isinstance(stamp, (int, float)) else None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_LOCATION_UPDATE.format(self.mobile_id), self.report))

    @callback
    def report(self, data):
        gps = data.get('gps') if isinstance(data, dict) else None
        if (not isinstance(gps, (tuple, list)) or len(gps) != 2 or
                any(type(v) not in (int, float) or not math.isfinite(v) for v in gps) or
                not -90 <= gps[0] <= 90 or not -180 <= gps[1] <= 180):
            return
        self.reports[self.mobile_id] = time.time()
        self.store.async_delay_save(lambda: self.reports, 1)
        self.async_write_ha_state()
