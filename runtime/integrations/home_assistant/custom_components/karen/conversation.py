"""HA Assist conversation entity, backed by the same local Karen Core and archive."""
from homeassistant.components import conversation
from homeassistant.components.conversation.chat_log import AssistantContent
from homeassistant.const import MATCH_ALL
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import intent
from homeassistant.auth.permissions.const import POLICY_READ
from .context import snapshot, direct_answer


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([KarenConversation(entry)])


class KarenConversation(conversation.ConversationEntity, conversation.AbstractConversationAgent):
    _attr_name = 'Karen'
    _attr_should_poll = False

    def __init__(self, entry):
        self.entry = entry
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = {'identifiers': {('karen', 'local-core')}, 'name': 'Karen', 'manufacturer': 'Karen', 'model': 'Core local'}

    @property
    def supported_languages(self):
        return MATCH_ALL

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        conversation.async_set_agent(self.hass, self.entry, self)

    async def async_will_remove_from_hass(self):
        conversation.async_unset_agent(self.hass, self.entry)
        await super().async_will_remove_from_hass()

    async def _async_handle_message(self, user_input, chat_log):
        response = intent.IntentResponse(language=user_input.language)
        try:
            states = []
            if self.hass is not None and user_input.context.user_id:
                user = await self.hass.auth.async_get_user(user_input.context.user_id)
                if user:
                    states = [s for s in self.hass.states.async_all() if user.permissions.check_entity(s.entity_id, POLICY_READ)]
            answer = direct_answer(states, user_input.text)
            result = {'answer': answer} if answer else await self.entry.runtime_data.request('conversation', {
                'text': user_input.text, 'conversation_id': chat_log.conversation_id,
                'user_id': user_input.context.user_id, 'home_context': snapshot(states, user_input.text),
            })
            answer = result.get('answer')
            if not isinstance(answer, str) or not answer.strip():
                raise HomeAssistantError('Karen no devolvió una respuesta final.')
        except HomeAssistantError as error:
            response.async_set_error(intent.IntentResponseErrorCode.FAILED_TO_HANDLE, str(error))
        else:
            chat_log.async_add_assistant_content_without_tools(AssistantContent(agent_id=user_input.agent_id, content=answer))
            response.async_set_speech(answer)
        return conversation.ConversationResult(response=response, conversation_id=chat_log.conversation_id)
