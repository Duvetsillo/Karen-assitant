/* Native HA conversation with Karen. No credentials or remote browser fetches. */
class KarenHomeCard extends HTMLElement {
  constructor() {
    super(); this.attachShadow({mode:'open'}); this._busy=false; this._conversationId=null;
    this.shadowRoot.innerHTML=`<style>
      :host{display:block;color:var(--primary-text-color,#f7fbff);font-family:var(--primary-font-family,"Segoe UI",sans-serif)}
      *{box-sizing:border-box}.shell{max-width:1740px;margin:18px auto;padding:0 clamp(18px,3.2vw,44px)}
      .grid{display:grid;grid-template-columns:1.6fr 1fr;gap:14px}section{padding:22px;border:1px solid var(--divider-color,#ffffff24);border-radius:22px;background:var(--karen-glass,rgba(22,31,35,.82));backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);box-shadow:inset 0 1px #ffffff0d}
      h2{font-size:28px;letter-spacing:-.025em;margin:0 0 8px;font-weight:550}p{line-height:1.65;margin:8px 0;overflow-wrap:anywhere}.muted{color:var(--secondary-text-color,#b6c7d1);font-size:14px}
      section:first-child{border-color:color-mix(in srgb,var(--primary-color,#8ae8ef) 24%,var(--divider-color,#ffffff24));background:var(--karen-glass,rgba(22,31,35,.82));backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);box-shadow:inset 0 1px #ffffff0d}
      .heading{display:flex;align-items:center;justify-content:space-between;gap:12px}.heading button{font-size:13px;margin:0}.identity{display:flex;align-items:center;gap:14px}.pet{width:68px;height:68px;object-fit:contain;margin:0}.pet.thinking{animation:karen-think 1.4s ease-in-out infinite alternate}@keyframes karen-think{to{transform:translateY(-4px)}}@media(prefers-reduced-motion:reduce){.pet.thinking{animation:none}}
      button{min-height:44px;padding:10px 16px;border:1px solid var(--divider-color,#ffffff35);border-radius:10px;background:transparent;color:var(--primary-text-color,#f7fbff);font:inherit;cursor:pointer;touch-action:manipulation}
      button:hover{background:var(--secondary-background-color,#ffffff12)}button:disabled{opacity:.5;cursor:default}#send{background:var(--primary-color,#8ae8ef);color:var(--text-primary-color,#fff);border-color:transparent;min-width:88px;font-weight:650}#new{border:0;color:var(--secondary-text-color,#b6c7d1)}
      .voice-launch{margin:18px 0;--ha-card-box-shadow:none;--ha-card-border-width:0;--ha-card-background:transparent;--ha-card-border-radius:12px}.voice-launch[hidden]{display:none}.messages{max-width:72ch}
      button:focus-visible,textarea:focus-visible{outline:3px solid var(--primary-color,#8ae8ef);outline-offset:3px}
      label{display:block;font-size:14px;margin-bottom:8px}.input{display:flex;gap:10px;align-items:stretch}textarea{width:100%;resize:vertical;min-height:72px;padding:12px;border:1px solid var(--divider-color,#ffffff35);border-radius:10px;background:var(--primary-background-color,#0a161e);color:inherit;font:inherit;font-size:16px;line-height:1.5}
      .messages{max-height:300px;overflow:auto;margin:18px 0;scrollbar-color:var(--primary-color,#8ae8ef) transparent}.messages:empty{display:none}.message{white-space:pre-wrap;padding:8px 0}.message strong{display:block;font-size:13px;color:var(--secondary-text-color,#b6c7d1)}
      .title{font-size:18px}img{display:block;width:100%;max-height:210px;object-fit:contain;border-radius:10px;margin:12px 0}figure{margin:0}figcaption{font-size:12px;color:var(--secondary-text-color,#b6c7d1)}
      .chat-only .grid{grid-template-columns:1fr}.chat-only section:last-child{display:none}
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
    this.config={entities:[...entities],agent:config.agent_id,pipeline:config.pipeline_id};this.shadowRoot.querySelector('.shell').classList.toggle('chat-only',!!config.hide_media);this.render();
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
    root.querySelector('#connection').textContent=this._busy?'Karen está respondiendo…':this._error|| (connected?(this.config.pipeline?'Chat local · voz con Assist':'Chat local de Karen'):'Karen aún no está conectada.');
    const available=this.config.entities.map(id=>states[id]).filter(e=>e&&!['unknown','unavailable'].includes(e.state));
    const primary=available.find(e=>['playing','paused'].includes(e.state))||available[0];
    const media=available.find(e=>['playing','paused'].includes(e.state)&&e.attributes?.media_title)||primary;
    const active=media&&['playing','paused'].includes(media.state),attributes=media?.attributes||{};
    root.querySelector('#media-state').textContent=primary?({playing:'Reproduciendo',paused:'En pausa',idle:'Sin reproducción',off:'Apagado',standby:'En espera'}[primary.state]||primary.state):'Sin datos de reproducción';
    root.querySelector('.title').textContent=active&&attributes.media_title||(primary?(active?'La app no informa el título.':'Sin contenido en reproducción.'):'Home Assistant no recibe una sesión de este reproductor.');
    const app=primary?.attributes?.app_name||primary?.attributes?.source||primary?.attributes?.app_id;
    root.querySelector('#media-detail').textContent=[app,attributes.media_series_title].filter(Boolean).join(' · ');
    this._mediaEntity=primary?.entity_id||this.config.entities[0];
    let picture='';try{const raw=active&&primary?.attributes?.entity_picture,url=new URL(raw||'',window.location.href);if(raw&&url.origin===window.location.origin&&url.pathname.startsWith('/api/media_player_proxy/'))picture=url.href;}catch{}
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
      .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr));gap:14px}section{padding:20px;border:1px solid var(--divider-color,#ffffff24);border-radius:22px;background:var(--karen-glass,rgba(22,31,35,.82));backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);box-shadow:inset 0 1px #ffffff0d}
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


/* Minimal home shell. Native HA cards keep their original contracts and controls. */
class KarenHouseCard extends HTMLElement {
  constructor(){super();this.attachShadow({mode:'open'});this.cards=[];this.metrics=[];}
  setConfig(config){
    if(!Array.isArray(config.groups))throw Error('Configura las secciones de casa.');
    this.config=config;this.cards=[];this.metrics=[];
    this.shadowRoot.innerHTML=`<style>
      :host{display:block;--primary-text-color:#f3f5f5;--secondary-text-color:#c3cbce;--primary-color:#efbd70;--text-primary-color:#fff;--karen-glass:rgba(25,36,41,.78);--ha-card-background:var(--karen-glass);--card-background-color:var(--karen-glass);--state-active-color:#efbd70;--state-inactive-color:#bdc7cb;--state-light-active-color:#efbd70;--state-switch-active-color:#efbd70;--primary-background-color:#111b20;--secondary-background-color:#26343a;--divider-color:#ffffff24;--ha-card-border-color:#ffffff24;--ha-card-border-width:1px;--ha-card-border-radius:22px;--ha-card-box-shadow:none;--mdc-theme-primary:#efbd70;color:#f3f5f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
      *{box-sizing:border-box}.page{background:#111b20;min-height:calc(100dvh - 56px);padding:clamp(20px,4vw,54px)}.body{max-width:1280px;margin:auto}header{display:flex;justify-content:space-between;gap:24px;align-items:center;margin-bottom:28px}h1{font-size:clamp(30px,3vw,36px);line-height:1.1;letter-spacing:-.035em;font-weight:550;margin:0 0 10px}header p{margin:0;color:#c3cbce;line-height:1.5;max-width:65ch}.date{font-size:14px;color:#c3cbce;white-space:nowrap}
      nav{display:flex;gap:26px;overflow-x:auto;border-bottom:1px solid #ffffff24;margin-bottom:28px;scrollbar-width:thin}nav a{display:flex;align-items:center;gap:7px;min-height:48px;text-decoration:none;white-space:nowrap;color:#c3cbce;font-size:14px;border-bottom:2px solid transparent}nav a[aria-current=page]{color:#f3f5f5;border-bottom-color:#efbd70;font-weight:650}ha-icon{--mdc-icon-size:19px}.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:20px;margin:0 0 34px}.metric{background:none;border:0;border-bottom:1px solid #ffffff24;text-align:left;padding:0 0 14px;color:inherit;font:inherit;cursor:pointer;min-height:66px}.metric span{display:block;font-size:13px;color:#c3cbce;margin-bottom:7px}.metric strong{font-size:18px;font-weight:550;overflow-wrap:anywhere}
      .groups{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(0,1fr);gap:30px 24px;align-items:start}.group{min-width:0}.wide{grid-column:1/-1}h2,summary{font-size:20px;letter-spacing:-.015em;font-weight:550;margin:0 0 16px}summary{cursor:pointer;min-height:44px;padding:10px 0;border-top:1px solid #ffffff24}.items{display:grid;grid-template-columns:repeat(var(--columns,1),minmax(0,1fr));gap:12px}.items>*{min-width:0}.shortcut{min-height:80px;display:flex;align-items:center;gap:14px;padding:18px;color:#f3f5f5;background:#fff;border:1px solid #ffffff24;border-radius:22px;text-decoration:none;font-size:15px}.shortcut:hover{background:#26343a}.shortcut ha-icon{--mdc-icon-size:24px;color:#efbd70;flex:none}details{grid-column:1/-1}.notice{color:#8b451e;font-size:13px;line-height:1.5}.empty{padding:16px;border:1px dashed #ffffff24;color:#c3cbce}a:focus-visible,button:focus-visible,summary:focus-visible{outline:3px solid #efbd70;outline-offset:3px}footer{padding-top:32px;font-size:12px;color:#c3cbce}
      @media(max-width:850px){.groups{grid-template-columns:1fr}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.date{display:none}nav{gap:22px}}@media(max-width:480px){.items{--columns:1!important}.page{padding:22px 16px}.metrics{gap:16px}nav a{font-size:13px}.groups{gap:24px}}

      :host{color-scheme:dark;--text-primary-color:#182128;--secondary-text-color:#c3cbce;--primary-text-color:#f3f5f5;--primary-color:#efbd70;--ha-card-border-radius:22px;--ha-card-box-shadow:0 8px 24px rgba(3,10,14,.16)}
      .page{position:relative;isolation:isolate;background:transparent}.page::before{content:"";position:fixed;inset:0;z-index:-1;background:linear-gradient(rgba(7,16,22,.46),rgba(7,16,22,.70)),url('/local/karen-home-forest.png') center/cover no-repeat;pointer-events:none}
      nav{background:var(--karen-glass);backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);border:1px solid #ffffff24;border-radius:22px;padding:6px;gap:4px}nav a{border:0;border-radius:16px;padding:0 14px;min-height:44px}nav a[aria-current=page]{background:#ffffff18;color:#fff;border:0}
      .metric,.shortcut{background:var(--karen-glass);border:1px solid #ffffff24;border-radius:22px;box-shadow:inset 0 1px #ffffff0d;backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px)}.metric{padding:14px 16px}.shortcut{min-height:128px;align-items:flex-start;justify-content:space-between;flex-direction:column;font-size:15px;font-weight:600}.shortcut ha-icon{--mdc-icon-size:26px;color:#cbd3d6}.shortcut:hover{background:rgba(43,57,63,.88)}.shortcut:active,.metric:active{transform:scale(.98)}.shortcut,.metric{transition:transform 160ms ease,background 160ms ease}
      footer{color:#c3cbce}header p{color:#c3cbce}h2,summary{font-size:21px;font-weight:600}summary{border-color:#ffffff24}
      @supports not (backdrop-filter:blur(1px)){:host{--karen-glass:rgba(25,36,41,.96)}}
      @media(max-width:480px){.items{grid-template-columns:minmax(0,1fr)}.items.accessories{grid-template-columns:repeat(2,minmax(0,1fr))}.metrics{display:flex;overflow-x:auto;gap:8px;margin-bottom:26px}.metric{flex:0 0 144px}.page{padding:24px 16px}nav a{padding:0 12px}.groups{gap:26px}nav,.metric,.shortcut{backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px)}}
      @media(prefers-reduced-motion:reduce){.shortcut,.metric{transition:none}.shortcut:active,.metric:active{transform:none}}
    </style><div class="page"><main class="body"><header><div><h1></h1><p class="subtitle"></p></div><time class="date"></time></header><nav aria-label="Espacios de casa"></nav><div class="metrics"></div><div class="groups"></div><footer>Home Assistant · estados reales, control local</footer></main></div>`;
    const root=this.shadowRoot;root.querySelector('h1').textContent=(config.title||'Casa').replace(/^Tu casa\.$/,'Casa');root.querySelector('.subtitle').textContent=config.subtitle||'';root.querySelector('.subtitle').hidden=config.path==='panorama';
    const paths=[['panorama','Inicio','mdi:home-outline'],['casa','Habitación','mdi:bed-outline'],['sala-cocina','Sala','mdi:sofa-outline'],['familia','Familia','mdi:map-marker-outline'],['karen','Karen','mdi:creation'],['homelab','Home Lab','mdi:server-outline'],['diagnostico','Sistema','mdi:shield-check-outline']];
    for(const [path,name,icon] of paths){const link=document.createElement('a');link.href='/dashboard-casa/'+path;if(config.path===path)link.setAttribute('aria-current','page');const image=document.createElement('ha-icon');image.setAttribute('icon',icon);link.append(image,document.createTextNode(name));root.querySelector('nav').append(link);}
    for(const metric of config.metrics||[]){const button=document.createElement('button');button.className='metric';const label=document.createElement('span'),value=document.createElement('strong');label.textContent=metric.name;button.append(label,value);button.onclick=()=>this.dispatchEvent(new CustomEvent('hass-more-info',{detail:{entityId:metric.entity},bubbles:true,composed:true}));root.querySelector('.metrics').append(button);this.metrics.push({...metric,node:value});}
    window.loadCardHelpers().then(helpers=>{if(this.config!==config)return;for(const group of config.groups){const block=document.createElement(group.collapsed?'details':'section');block.className=group.wide?'group wide':'group';const heading=document.createElement(group.collapsed?'summary':'h2');heading.textContent=group.title;block.append(heading);const items=document.createElement('div');items.className='items';items.style.setProperty('--columns',String(group.columns||1));items.classList.toggle('accessories',(group.cards||[]).length>0&&(group.cards||[]).every(c=>c.type==='tile'||c.type==='button'));block.append(items);root.querySelector('.groups').append(block);let loaded=false;const mount=()=>{if(loaded)return;loaded=true;for(const specification of group.cards||[]){if(specification.type==='button'&&specification.tap_action?.action==='navigate'){const link=document.createElement('a');link.className='shortcut';link.href=specification.tap_action.navigation_path;const icon=document.createElement('ha-icon');icon.setAttribute('icon',specification.icon||'mdi:arrow-right');link.append(icon,document.createTextNode(specification.name||'Abrir'));items.append(link);continue;}const icons={'switch.dormitorio_luz_interruptor_1':'mdi:lightbulb-outline','switch.smart_switch_6231':'mdi:fan','switch.smart_switch_d557':'mdi:fridge-outline','switch.smart_switch_1a83':'mdi:toaster-oven'};const nativeSpecification=specification.type==='tile'&&icons[specification.entity]?{...specification,icon:icons[specification.entity]}:specification;const card=helpers.createCardElement(nativeSpecification);if(this._hass)card.hass=this._hass;this.cards.push(card);items.append(card);const polish=()=>{if(!card.shadowRoot)return;const style=document.createElement('style');style.textContent='ha-card{background:var(--karen-glass,rgba(25,36,41,.82))!important;color:#f3f5f5!important;box-shadow:0 8px 24px rgba(3,10,14,.16),inset 0 1px rgba(255,255,255,.06)!important;border:1px solid rgba(255,255,255,.14)!important;border-radius:22px!important;backdrop-filter:blur(18px) saturate(1.15)!important;-webkit-backdrop-filter:blur(18px) saturate(1.15)!important}ha-card::before,ha-card::after{content:none!important;display:none!important}ha-tile-info{width:100%}.primary{font-size:15px!important;line-height:1.3!important}ha-tile-info [slot=secondary]{font-size:13px!important}';card.shadowRoot.append(style);if(specification.type==='tile'){const container=card.shadowRoot.querySelector('ha-tile-container');if(container?.shadowRoot){const tileStyle=document.createElement('style');tileStyle.textContent='.content{flex-direction:column!important;align-items:flex-start!important;gap:18px!important}.container{padding:18px!important;box-sizing:border-box;min-height:142px}.background{border-radius:22px}';container.shadowRoot.append(tileStyle);}}};if(card.updateComplete)card.updateComplete.then(polish);else queueMicrotask(polish);}};if(group.collapsed)block.addEventListener('toggle',()=>{if(block.open)mount();});else mount();}this.render();}).catch(()=>{root.querySelector('.groups').textContent='No se pudieron cargar las tarjetas. Recarga Home Assistant.';});this.render();
  }
  set hass(value){this._hass=value;for(const card of this.cards)card.hass=value;this.render();}
  render(){if(!this.config||!this._hass)return;this.shadowRoot.querySelector('time').textContent=new Date().toLocaleDateString('es',{weekday:'long',day:'numeric',month:'long'});for(const metric of this.metrics){const state=this._hass.states[metric.entity];let value=state?.state;if(metric.states?.[value])value=metric.states[value];value=({on:'Activo',off:'Inactivo',home:'En casa',not_home:'Fuera de casa',unavailable:'Sin conexión',unknown:'Sin confirmar'}[value]||value||'Sin datos');if(state?.attributes?.unit_of_measurement&&!['unknown','unavailable'].includes(state.state))value+=' '+state.attributes.unit_of_measurement;metric.node.textContent=value;}}
  getCardSize(){return 12;}
}
if(!customElements.get('karen-house-card'))customElements.define('karen-house-card',KarenHouseCard);
