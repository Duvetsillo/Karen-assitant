/* Native HA conversation with Karen. No credentials or remote browser fetches. */
class KarenHomeCard extends HTMLElement {
  constructor() {
    super(); this.attachShadow({mode:'open'}); this._busy=false; this._conversationId=null;
    this.shadowRoot.innerHTML=`<style>
      :host{display:block;color:var(--primary-text-color,#f7fbff);font-family:var(--primary-font-family,"Segoe UI",sans-serif)}
      *{box-sizing:border-box}.shell{max-width:1740px;margin:18px auto;padding:0 clamp(18px,3.2vw,44px)}
      .grid{display:grid;grid-template-columns:1.6fr 1fr;gap:14px}section{padding:22px;border:1px solid var(--divider-color,#ffffff24);border-radius:16px;background:color-mix(in srgb,#10212d 94%,var(--ha-card-background,#10212d))}
      h2{font-size:28px;letter-spacing:-.025em;margin:0 0 8px;font-weight:550}p{line-height:1.65;margin:8px 0;overflow-wrap:anywhere}.muted{color:var(--secondary-text-color,#b6c7d1);font-size:14px}
      section:first-child{border-color:color-mix(in srgb,var(--primary-color,#8ae8ef) 24%,var(--divider-color,#ffffff24));background:color-mix(in srgb,#102b35 96%,var(--ha-card-background,#10212d))}
      .heading{display:flex;align-items:center;justify-content:space-between;gap:12px}.heading button{font-size:13px;margin:0}.identity{display:flex;align-items:center;gap:14px}.pet{width:68px;height:68px;object-fit:contain;margin:0}.pet.thinking{animation:karen-think 1.4s ease-in-out infinite alternate}@keyframes karen-think{to{transform:translateY(-4px)}}@media(prefers-reduced-motion:reduce){.pet.thinking{animation:none}}
      button{min-height:44px;padding:10px 16px;border:1px solid var(--divider-color,#ffffff35);border-radius:10px;background:transparent;color:var(--primary-text-color,#f7fbff);font:inherit;cursor:pointer;touch-action:manipulation}
      button:hover{background:var(--secondary-background-color,#ffffff12)}button:disabled{opacity:.5;cursor:default}#send{background:var(--primary-color,#8ae8ef);color:#06191f;border-color:transparent;min-width:88px;font-weight:650}#new{border:0;color:var(--secondary-text-color,#b6c7d1)}
      .voice-launch{margin:18px 0;--ha-card-box-shadow:none;--ha-card-border-width:0;--ha-card-background:transparent;--ha-card-border-radius:12px}.voice-launch[hidden]{display:none}.messages{max-width:72ch}
      button:focus-visible,textarea:focus-visible{outline:3px solid var(--primary-color,#8ae8ef);outline-offset:3px}
      label{display:block;font-size:14px;margin-bottom:8px}.input{display:flex;gap:10px;align-items:stretch}textarea{width:100%;resize:vertical;min-height:72px;padding:12px;border:1px solid var(--divider-color,#ffffff35);border-radius:10px;background:var(--primary-background-color,#0a161e);color:inherit;font:inherit;font-size:16px;line-height:1.5}
      .messages{max-height:300px;overflow:auto;margin:18px 0;scrollbar-color:var(--primary-color,#8ae8ef) transparent}.messages:empty{display:none}.message{white-space:pre-wrap;padding:8px 0}.message strong{display:block;font-size:13px;color:var(--secondary-text-color,#b6c7d1)}
      .title{font-size:18px}img{display:block;width:100%;max-height:210px;object-fit:contain;border-radius:10px;margin:12px 0}figure{margin:0}figcaption{font-size:12px;color:var(--secondary-text-color,#b6c7d1)}
      @media(max-width:700px){.grid{grid-template-columns:1fr}.shell{padding:0 14px}section{padding:18px}.input{flex-direction:column}.heading{align-items:flex-start}}
    </style><div class="shell"><div class="grid">
      <section aria-label="Karen"><div class="heading"><div class="identity"><img class="pet" src="/local/karen-pet.png" alt="Karen"><h2>Karen</h2></div><button id="new">Nueva conversación</button></div>
        <p class="muted" id="connection" role="status">Conectando con Karen…</p>
        <div class="voice-launch" hidden></div><div class="messages" role="log" aria-live="polite" aria-label="Conversación con Karen"></div>
        <form><label for="question">¿Qué hacemos hoy?</label><div class="input"><textarea id="question" rows="2" maxlength="4000" required placeholder="Escríbele a Karen…"></textarea><button id="send">Enviar</button></div></form>
      </section><section aria-label="Fire TV"><h2>Fire TV</h2><p id="media-state" class="muted" role="status"></p>
        <p class="title"></p><p id="media-detail" class="muted"></p><figure hidden><img alt="Imagen del Fire TV" loading="lazy"><figcaption>Última imagen informada por Home Assistant</figcaption></figure>
        <button id="media-info">Ver reproductor</button></section>
    </div></div>`;
    this.shadowRoot.querySelector('form').addEventListener('submit', event=>this.send(event));
    this.shadowRoot.querySelector('#new').addEventListener('click',()=>{this._conversationId=null;this._error='';this.shadowRoot.querySelector('.messages').replaceChildren();this.persist();this.render();});
    this.shadowRoot.querySelector('#media-info').addEventListener('click',()=>this.dispatchEvent(new CustomEvent('hass-more-info',{detail:{entityId:this._mediaEntity},bubbles:true,composed:true})));
  }
  setConfig(config) {
    const entities=config.media_entities||['media_player.fire_tv_de_dayver'];
    if(!Array.isArray(entities)||!entities.length||entities.some(id=>!/^media_player\.[a-z0-9_]+$/.test(id)))throw Error('Configura entidades válidas del mismo Fire TV.');
    if(config.agent_id&&!/^conversation\.[a-z0-9_]+$/.test(config.agent_id))throw Error('Configura un agente de conversación válido.');
    if(config.pipeline_id&&!/^[a-zA-Z0-9_-]{1,128}$/.test(config.pipeline_id))throw Error('Asistente de voz inválido.');
    this.config={entities:[...entities],agent:config.agent_id,pipeline:config.pipeline_id};this.render();
  }
  set hass(value) {
    this._hass=value;
    const owner=value.user?.id||'local';
    if(owner!==this._owner){if(this._owner){this.shadowRoot.querySelector('.messages').replaceChildren();this.shadowRoot.querySelector('textarea').value='';}this._owner=owner;try{this._conversationId=localStorage.getItem('karen-ha-conversation:'+owner);}catch{this._conversationId=null;}}
    this.render();
  }
  getCardSize(){return 6;}
  persist(){try{const key='karen-ha-conversation:'+this._owner;if(this._conversationId)localStorage.setItem(key,this._conversationId);else localStorage.removeItem(key);}catch{}}
  append(role,text){const row=document.createElement('p'),label=document.createElement('strong');row.className='message';label.textContent=role;row.append(label,document.createTextNode(text));const log=this.shadowRoot.querySelector('.messages');log.append(row);while(log.children.length>20)log.firstElementChild.remove();log.scrollTop=log.scrollHeight;}
  async send(event){
    event.preventDefault();const input=this.shadowRoot.querySelector('textarea'),text=input.value.trim();
    if(!text||this._busy||!this._agent)return;
    this._busy=true;input.value='';this.append('Tú',text);this.render();
    try{
      const result=await this._hass.callApi('POST','conversation/process',{text,agent_id:this._agent,conversation_id:this._conversationId||undefined,language:'es'});
      if(result.response?.response_type==='error')throw Error(result.response.data?.message||'Karen no pudo completar la consulta.');
      const answer=result.response?.speech?.plain?.speech;
      if(typeof answer!=='string'||!answer.trim())throw Error('Karen no devolvió una respuesta final.');
      this._conversationId=result.conversation_id;this.persist();this.append('Karen',answer);this._error='';
    }catch(error){this._error=error.message||'No se pudo conectar con Karen.';if(!input.value)input.value=text;}
    finally{this._busy=false;this.render();}
  }
  render(){
    if(!this.config||!this._hass)return;
    const root=this.shadowRoot,states=this._hass.states;
    this._agent=this.config.agent||Object.keys(states).find(id=>id.startsWith('conversation.')&&states[id].attributes?.friendly_name==='Karen');
    const connected=this._agent&&states[this._agent]&&states[this._agent].state!=='unavailable';
    const voice=root.querySelector('.voice-launch');voice.hidden=!this.config.pipeline;
    if(this._voiceCard)this._voiceCard.hass=this._hass;
    if(this.config.pipeline&&this._voiceId!==this.config.pipeline&&window.loadCardHelpers){
      this._voiceId=this.config.pipeline;const pipeline=this.config.pipeline;
      window.loadCardHelpers().then(helpers=>{if(this.config.pipeline!==pipeline)return;const action={action:'assist',pipeline_id:pipeline,start_listening:true};this._voiceCard=helpers.createCardElement({type:'tile',entity:this._agent,name:'Hablar con Karen',icon:'mdi:microphone',hide_state:true,vertical:false,tap_action:action,icon_tap_action:action});this._voiceCard.hass=this._hass;voice.replaceChildren(this._voiceCard);}).catch(()=>{voice.textContent='Abre Assist desde la barra superior para hablar con Karen.';});
    }
    root.querySelector('#send').disabled=this._busy||!connected;root.querySelector('#new').disabled=this._busy;
    root.querySelector('.pet').classList.toggle('thinking',this._busy);
    root.querySelector('#connection').textContent=this._busy?'Karen está respondiendo…':this._error|| (connected?(this.config.pipeline?'Aquí estoy. Puedes hablarme o escribir.':'Aquí estoy. ¿Qué hacemos hoy?'):'Karen aún no está conectada.');
    const available=this.config.entities.map(id=>states[id]).filter(e=>e&&!['unknown','unavailable'].includes(e.state));
    const primary=available.find(e=>['playing','paused'].includes(e.state))||available[0];
    const media=available.find(e=>['playing','paused'].includes(e.state)&&e.attributes?.media_title)||primary;
    const active=media&&['playing','paused'].includes(media.state),attributes=media?.attributes||{};
    root.querySelector('#media-state').textContent=primary?({playing:'Reproduciendo',paused:'En pausa',idle:'Sin reproducción',off:'Apagado',standby:'En espera'}[primary.state]||primary.state):'Sin datos de reproducción';
    root.querySelector('.title').textContent=active&&attributes.media_title||(primary?(active?'La app no informa el título.':'Sin contenido en reproducción.'):'Home Assistant no recibe una sesión de este reproductor.');
    const app=primary?.attributes?.app_name||primary?.attributes?.source||primary?.attributes?.app_id;
    root.querySelector('#media-detail').textContent=[app,attributes.media_series_title].filter(Boolean).join(' · ');
    this._mediaEntity=primary?.entity_id||this.config.entities[0];
    let picture='';try{const raw=primary?.attributes?.entity_picture,url=new URL(raw||'',window.location.href);if(raw&&url.origin===window.location.origin&&url.pathname.startsWith('/api/media_player_proxy/'))picture=url.href;}catch{}
    const image=root.querySelector('figure img');root.querySelector('figure').hidden=!picture;
    if(picture&&image.getAttribute('src')!==picture)image.src=picture;
    if(!picture)image.removeAttribute('src');
  }
}
if(!customElements.get('karen-home-card'))customElements.define('karen-home-card',KarenHomeCard);

class KarenLocationCard extends HTMLElement {
  constructor(){
    super();this.requests=new Map();this.attachShadow({mode:'open'});this.shadowRoot.innerHTML=`<style>
      :host{display:block;color:var(--primary-text-color,#f7fbff);font-family:var(--primary-font-family,"Segoe UI",sans-serif)}
      *{box-sizing:border-box}.shell{max-width:1740px;margin:18px auto;padding:0 clamp(18px,3.2vw,44px)}h2{font-size:23px;font-weight:550;margin:0 0 8px}.intro{margin:0 0 16px;color:var(--secondary-text-color,#b6c7d1);line-height:1.5}
      .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr));gap:14px}section{padding:20px;border:1px solid var(--divider-color,#ffffff24);border-radius:16px;background:color-mix(in srgb,#10212d 94%,var(--ha-card-background,#10212d))}
      h3{font-size:18px;margin:0 0 12px}p{line-height:1.5;margin:8px 0;overflow-wrap:anywhere}.muted{font-size:13px;color:var(--secondary-text-color,#b6c7d1)}.stale{color:var(--warning-color,#e9be75)}
      button{min-height:44px;padding:10px 16px;border:1px solid var(--divider-color,#ffffff35);border-radius:10px;background:transparent;color:inherit;font:inherit;cursor:pointer;touch-action:manipulation}button:disabled{opacity:.5}button:focus-visible{outline:3px solid var(--primary-color,#8ae8ef);outline-offset:3px}
      @media(max-width:700px){.shell{padding:0 14px}}
    </style><div class="shell"><h2>Ubicación de los dispositivos</h2><p class="intro">GPS compartido, precisión y fecha de la lectura. Una ubicación antigua no confirma dónde está ahora.</p><div class="grid primary"></div><details hidden><summary>Otros registros de dispositivos</summary><div class="grid secondary"></div></details></div>`;
  }
  setConfig(config){
    if(!Array.isArray(config.sources)||!config.sources.length||config.sources.length>20||config.sources.some(s=>!/^device_tracker\.[a-z0-9_]+$/.test(s.entity)||s.address&&!/^sensor\.[a-z0-9_]+$/.test(s.address)||s.notify&&!/^notify\.[a-z0-9_]+$/.test(s.notify)))throw Error('Configura fuentes GPS reales.');
    this.sources=config.sources.map(s=>({...s}));this.nodes=new Map();for(const grid of this.shadowRoot.querySelectorAll('.grid'))grid.replaceChildren();this.shadowRoot.querySelector('details').hidden=!this.sources.some(s=>s.secondary);
    for(const source of this.sources){const card=document.createElement('section');card.innerHTML='<h3></h3><p class="place"></p><p class="address"></p><p class="coords muted"></p><p class="accuracy muted"></p><p class="age muted"></p><button class="map">Ver ubicación</button> <button class="refresh">Pedir actualización</button><p class="request muted" role="status"></p>';card.querySelector('.map').onclick=()=>this.dispatchEvent(new CustomEvent('hass-more-info',{detail:{entityId:source.entity},bubbles:true,composed:true}));card.querySelector('.refresh').hidden=!source.notify;card.querySelector('.refresh').onclick=()=>this.refresh(source,card);this.nodes.set(source.entity,card);this.shadowRoot.querySelector(source.secondary?'.secondary':'.primary').append(card);}this.render();
  }
  set hass(value){this._hass=value;this.render();}
  connectedCallback(){this.timer=setInterval(()=>this.render(),60000);}
  disconnectedCallback(){clearInterval(this.timer);}
  getCardSize(){return 6;}
  async refresh(source,card){
    const previous=this.requests.get(source.entity)||0;if(Date.now()-previous<60000)return;
    this.requests.set(source.entity,Date.now());this.render();
    try{await this._hass.callApi('POST','services/notify/send_message',{entity_id:source.notify,message:'request_location_update'});card.querySelector('.request').textContent='Solicitud enviada. La ubicación cambiará cuando el dispositivo envíe un reporte GPS.';}
    catch{card.querySelector('.request').textContent='No se pudo pedir la actualización. Comprueba la conexión de la app del dispositivo.';}
    setTimeout(()=>this.render(),60000);
  }
  render(){
    if(!this._hass||!this.sources)return;
    const states=this._hass.states,now=Date.now();
    const reports=new Map(Object.values(states).filter(s=>s.entity_id.startsWith('sensor.')&&s.attributes?.location_tracker).map(s=>[s.attributes.location_tracker,s]));
    for(const source of this.sources){
      const state=states[source.entity],attrs=state?.attributes||{},card=this.nodes.get(source.entity);
      const lat=attrs.latitude,lon=attrs.longitude,valid=Number.isFinite(lat)&&Number.isFinite(lon)&&Math.abs(lat)<=90&&Math.abs(lon)<=180;
      const report=reports.get(source.entity);
      const stamp=Date.parse(report?.state||''),minutes=Number.isFinite(stamp)?Math.max(0,(now-stamp)/60000):null;
      const fresh=valid&&!['unknown','unavailable'].includes(state?.state)&&minutes!==null&&minutes<=30&&stamp<=now+60000;
      card.querySelector('h3').textContent=source.name||attrs.friendly_name||source.entity;
      const zone=state?.state==='home'?'Casa':state?.state==='not_home'?'Fuera de las zonas guardadas':state?.state;
      card.querySelector('.place').textContent=valid?(fresh?'Zona informada: '+zone:'Última ubicación conocida; posición actual sin confirmar.'):'El dispositivo no comparte coordenadas disponibles.';
      card.querySelector('.place').classList.toggle('stale',!fresh);
      const address=states[source.address],addressTime=Date.parse(address?.last_updated||'');
      const goodAddress=fresh&&address&&!['unknown','unavailable',''].includes(address.state)&&Math.abs(addressTime-stamp)<=300000;
      card.querySelector('.address').textContent=goodAddress?address.state:'Dirección actual no compartida por este dispositivo.';
      card.querySelector('.coords').textContent=valid?'GPS: '+lat.toFixed(5)+', '+lon.toFixed(5):'GPS no disponible';
      card.querySelector('.accuracy').textContent=valid&&Number.isFinite(attrs.gps_accuracy)&&attrs.gps_accuracy>0?'Precisión informada: ±'+Math.ceil(attrs.gps_accuracy)+' m':'Precisión no informada';
      card.querySelector('.age').textContent=minutes!==null?'Reporte GPS: '+new Date(stamp).toLocaleString('es-BO')+' · '+Math.floor(minutes)+' min atrás':'Fecha de la última lectura GPS aún sin confirmar.';
      card.querySelector('.map').disabled=!valid;
      const requested=this.requests.get(source.entity)||0;card.querySelector('.refresh').disabled=now-requested<60000;
      if(requested&&stamp>requested)card.querySelector('.request').textContent='Reporte GPS recibido.';
    }
  }
}
if(!customElements.get('karen-location-card'))customElements.define('karen-location-card',KarenLocationCard);
