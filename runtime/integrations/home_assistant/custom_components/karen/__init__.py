"""Native Karen integration; no separate model, memory, or tool engine in HA."""
from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from .client import async_client

DOMAIN = 'karen'
PLATFORMS = [Platform.CONVERSATION, Platform.SENSOR, Platform.STT, Platform.TTS]


async def async_setup_entry(hass, entry):
    client = None
    try:
        client = await async_client(hass)
        status = await client.request('status')
        if status.get('name') != 'Karen' or status.get('scope') != 'conversation' or status.get('core') is not True:
            raise HomeAssistantError('Core de Karen no disponible.')
    except HomeAssistantError as error:
        if client:
            await client.close()
        raise ConfigEntryNotReady(str(error)) from None
    entry.runtime_data = client
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry):
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.close()
    return unloaded
