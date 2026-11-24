"""Connect the already-provisioned private Core; never asks for secrets in a card."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.exceptions import HomeAssistantError
from .client import async_client


class KarenConfigFlow(config_entries.ConfigFlow, domain='karen'):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id('karen-local-core')
            self._abort_if_unique_id_configured()
            try:
                client = await async_client(self.hass)
                try:
                    result = await client.request('status')
                finally:
                    await client.close()
                if result.get('name') != 'Karen' or result.get('core') is not True:
                    raise HomeAssistantError('Core no disponible.')
            except HomeAssistantError:
                errors['base'] = 'cannot_connect'
            else:
                return self.async_create_entry(title='Karen', data={'connection': 'local-core'})
        return self.async_show_form(step_id='user', data_schema=vol.Schema({}), errors=errors)
