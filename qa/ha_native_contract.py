"""Opt-in contract check inside an installed HA container; synthetic audio, no inference."""

import asyncio,sys
from types import SimpleNamespace
sys.path.insert(0,'/config')
from homeassistant.core import Context
from homeassistant.exceptions import HomeAssistantError
from homeassistant.components import conversation
from custom_components.karen.conversation import KarenConversation
from custom_components.karen.client import KarenClient
from custom_components.karen.sensor import KarenLocationReport
from custom_components.karen.stt import KarenSTT
from custom_components.karen.tts import KarenTTS
from aiohttp import web,ClientSession

async def main():
 app=web.Application()
 async def status(request):
  assert request.headers['Authorization']=='Bearer synthetic-qa-only'
  return web.json_response({'name':'Karen','core':True,'scope':'conversation'})
 app.router.add_get('/api/ha/status',status)
 runner=web.AppRunner(app);await runner.setup()
 site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
 port=site._server.sockets[0].getsockname()[1]
 try:
  async with ClientSession() as session:
   assert (await KarenClient(session,f'http://127.0.0.1:{port}','synthetic-qa-only').request('status'))['name']=='Karen'
 finally:await runner.cleanup()
 class FakeClient:
  async def request(self,route,data=None,**kwargs):
   if route=='stt':return {'text':'voz de prueba'}
   if route=='tts':return b'RIFF'+b'0'*40
   assert route=='conversation' and data['user_id']=='qa-user'
   return {'answer':'Respuesta sintetica verificada'}
 entry=SimpleNamespace(entry_id='qa-entry',runtime_data=FakeClient())
 agent=KarenConversation(entry)
 received=[]
 log=SimpleNamespace(conversation_id='qa-conversation',async_add_assistant_content_without_tools=received.append)
 user=SimpleNamespace(language='es',text='Hola de QA',context=Context(user_id='qa-user'),agent_id='conversation.karen')
 result=await agent._async_handle_message(user,log)
 assert result.conversation_id=='qa-conversation'
 assert 'Respuesta sintetica verificada' in str(result.as_dict())
 assert received[0].content=='Respuesta sintetica verificada'
 assert not agent.supported_features & conversation.ConversationEntityFeature.CONTROL
 class FakeStore:
  def async_delay_save(self,callback,delay):self.saved=callback()
 store=FakeStore();reports={}
 sensor=KarenLocationReport('device_tracker.qa','mobile-qa','QA',reports,store)
 sensor.async_write_ha_state=lambda:None
 assert sensor.native_value is None
 sensor.report({'battery':50})
 assert not reports
 sensor.report({'gps':[float('nan'),0]})
 assert not reports
 sensor.report({'gps':[12.34,45.67]})
 assert sensor.native_value is not None
 assert list(store.saved)==['mobile-qa']
 assert '12.34' not in str(store.saved) and '45.67' not in str(store.saved)
 restored=KarenLocationReport('device_tracker.qa','mobile-qa','QA',dict(store.saved),store)
 assert restored.native_value==sensor.native_value
 async def audio():yield b'\0\0'*160
 speech=await KarenSTT(entry).async_process_audio_stream(None,audio())
 assert speech.text=='voz de prueba'
 fmt,output=await KarenTTS(entry).async_get_tts_audio('Prueba','es',{})
 assert fmt=='wav' and output.startswith(b'RIFF')
 print('HA native client HTTP and ConversationEntity contract: OK')
 print('GPS freshness persistence without coordinates: OK')
 print('Native STT/TTS provider contract: OK (synthetic transport, no GPU model loaded)')
asyncio.run(main())
