"""HA Assist speech input through Karen's existing offline Spanish recognizer."""
from homeassistant.components import stt
from homeassistant.exceptions import HomeAssistantError


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([KarenSTT(entry)])


class KarenSTT(stt.SpeechToTextEntity):
    _attr_name = 'Karen'

    def __init__(self, entry):
        self.client = entry.runtime_data
        self._attr_unique_id = entry.entry_id + '-stt'

    @property
    def supported_languages(self): return ['es']
    @property
    def supported_formats(self): return [stt.AudioFormats.WAV]
    @property
    def supported_codecs(self): return [stt.AudioCodecs.PCM]
    @property
    def supported_bit_rates(self): return [stt.AudioBitRates.BITRATE_16]
    @property
    def supported_sample_rates(self): return [stt.AudioSampleRates.SAMPLERATE_16000]
    @property
    def supported_channels(self): return [stt.AudioChannels.CHANNEL_MONO]

    async def async_process_audio_stream(self, metadata, stream):
        audio = bytearray()
        async for chunk in stream:
            audio.extend(chunk)
            if len(audio) > 1_920_044:
                return stt.SpeechResult(None, stt.SpeechResultState.ERROR)
        try:
            result = await self.client.request('stt', raw=bytes(audio))
            text = result.get('text')
            if not isinstance(text, str) or not text.strip():
                raise HomeAssistantError('No se reconoció voz.')
            return stt.SpeechResult(text, stt.SpeechResultState.SUCCESS)
        except HomeAssistantError:
            return stt.SpeechResult(None, stt.SpeechResultState.ERROR)
