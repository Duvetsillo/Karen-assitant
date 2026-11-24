"""HA Assist speech output using Karen's existing pinned local voice."""
from homeassistant.components import tts
from homeassistant.exceptions import HomeAssistantError


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([KarenTTS(entry)])


class KarenTTS(tts.TextToSpeechEntity):
    _attr_name = 'Karen'
    _attr_supported_languages = ['es']
    _attr_default_language = 'es'
    _attr_supported_options = []
    _attr_default_options = {}

    def __init__(self, entry):
        self.client = entry.runtime_data
        self._attr_unique_id = entry.entry_id + '-tts'

    async def async_get_tts_audio(self, message, language, options):
        try:
            return 'wav', await self.client.request('tts', {'text': message}, audio=True)
        except HomeAssistantError:
            return None, None
