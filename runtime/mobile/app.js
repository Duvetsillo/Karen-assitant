const $ = id => document.getElementById(id);
const iconPaths = {
  plus:['M12 5v14','M5 12h14'],
  chat:['M20 11.5a7.5 7.5 0 0 1-7.5 7.5H7l-4 3v-7.5A7.5 7.5 0 0 1 10.5 7H12','M9 3h11v9'],
  history:['M4 5v5h5','M4.5 10a8 8 0 1 1 .5 6','M12 8v5l3 2'],
  grid:['M3 3h7v7H3z','M14 3h7v7h-7z','M3 14h7v7H3z','M14 14h7v7h-7z'],
  settings:['M9.5 3h5l.7 2.6 2.4 1.4 2.6-.6 2.5 4.3-1.9 2v2.6l1.9 2-2.5 4.3-2.6-.6-2.4 1.4-.7 2.6h-5l-.7-2.6L6.4 21l-2.6.6-2.5-4.3 1.9-2v-2.6l-1.9-2 2.5-4.3 2.6.6 2.4-1.4z','M15.5 13.5a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0'],
  calendar:['M4 5h16v16H4z','M8 3v4','M16 3v4','M4 10h16','M8 14h2','M14 14h2','M8 17h2'],
  idea:['M9 18h6','M9 21h6','M8 14a6 6 0 1 1 8 0l-1 3H9z'],
  book:['M12 5v16','M12 6C8 3 4 4 2 5v14c3-1 7-1 10 2 3-3 7-3 10-2V5c-2-1-6-2-10 1'],
  volume:['M4 9h4l5-4v14l-5-4H4z','M17 8a6 6 0 0 1 0 8','M20 5a10 10 0 0 1 0 14'],
  copy:['M9 9h12v12H9z','M15 6V3H3v12h3'],
  refresh:['M20 4v5h-5','M4 20v-5h5','M5 9a8 8 0 0 1 13-4l2 4','M19 15a8 8 0 0 1-13 4l-2-4']
};
function icon(name){const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox',name==='settings'?'0 0 25 27':'0 0 24 24');svg.setAttribute('aria-hidden','true');svg.setAttribute('focusable','false');svg.classList.add('ui-icon');for(const d of iconPaths[name]){const path=document.createElementNS(svg.namespaceURI,'path');path.setAttribute('d',d);svg.append(path);}return svg;}
for(const mark of document.querySelectorAll('.welcome-mark')){const img=document.createElement('img');img.src='/icon.svg';img.alt='';img.width=88;img.height=88;mark.replaceChildren(img);}
$('new-chat').replaceChildren(icon('plus'));
for(const [page,name] of Object.entries({chat:'chat',history:'history',consult:'grid',settings:'settings'})){const button=document.querySelector(`[data-page="${page}"]`);const label=button.lastChild.textContent;button.replaceChildren(icon(name),document.createTextNode(label));}
document.querySelectorAll('[data-prompt]').forEach((button,index)=>{const label=document.createElement('span');label.textContent=['Organizar mi día','Pensar una idea','Entender algo'][index];const plus=icon('plus');plus.classList.add('suggestion-add');button.replaceChildren(icon(['calendar','idea','book'][index]),label,plus);});
for(const id of ['refresh-history','refresh-resource'])$(id).prepend(icon('refresh'));
const state = {page:'chat', chat:null, busy:false, resource:'tasks', chats:[], model:'', resourceRequest:0};
let noticeTimer;
function notice(message) { clearTimeout(noticeTimer); $('notice').textContent=message; $('notice').hidden=!message; if(message) noticeTimer=setTimeout(()=>{$('notice').hidden=true;},16000); }
async function api(path, body) {
  let response;
  try { response=await fetch(path,{method:body===undefined?'GET':'POST',headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),credentials:'same-origin',cache:'no-store'}); }
  catch { throw new Error('No hay conexión con el PC. Comprueba Tailscale y que Karen móvil siga abierta. Si estabas enviando, revisa el historial antes de repetir.'); }
  const data=await response.json();
  if(response.status===401 && path!=='/api/login') showLogin();
  if(!response.ok) throw new Error(data.error||'No se pudo completar la consulta.');
  return data;
}
function showLogin(){ document.querySelectorAll('main>section').forEach(el=>el.hidden=true); $('login').hidden=false; $('nav').hidden=true; $('new-chat').hidden=true; $('connection').textContent='Conecta con tu PC'; window.speechSynthesis?.cancel(); }
function showPage(page){ state.page=page; document.querySelectorAll('main>section').forEach(el=>el.hidden=el.id!==page); document.querySelectorAll('nav button').forEach(el=>el.dataset.page===page?el.setAttribute('aria-current','page'):el.removeAttribute('aria-current')); if(page==='history') loadHistory().catch(e=>notice(e.message)); if(page==='consult') loadResource().catch(e=>notice(e.message)); }
function speak(text){ if(!window.speechSynthesis) return notice('Este navegador no tiene lectura de voz disponible.'); speechSynthesis.cancel(); const utterance=new SpeechSynthesisUtterance(text); utterance.lang='es-MX'; utterance.rate=.95; const voices=speechSynthesis.getVoices(); const voice=voices.find(v=>v.lang==='es-MX')||voices.find(v=>v.lang.startsWith('es')); if(voice)utterance.voice=voice; speechSynthesis.speak(utterance); }
function addMessage(role,text){ const item=document.createElement('article'); item.className='message '+role; const author=document.createElement('div');author.className='author';author.textContent=role==='user'?'Tú':'Karen';const p=document.createElement('p');p.textContent=text;item.append(author,p);if(role==='assistant'){const actions=document.createElement('div');actions.className='message-actions';const button=document.createElement('button');button.className='read-button';button.append(icon('volume'),document.createTextNode('Escuchar'));button.setAttribute('aria-label','Escuchar respuesta');button.onclick=()=>speak(text);const copy=document.createElement('button');copy.className='copy-button';copy.append(icon('copy'),document.createTextNode('Copiar'));copy.setAttribute('aria-label','Copiar respuesta');copy.onclick=async()=>{try{if(navigator.clipboard?.writeText){await navigator.clipboard.writeText(text);notice('Respuesta copiada.');}else{const range=document.createRange();range.selectNodeContents(p);const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);notice('Texto seleccionado. Mantén pulsado para copiar.');}}catch{notice('Mantén pulsada la respuesta para copiarla.');}};actions.append(button,copy);item.append(actions);} $('messages').append(item);$('welcome').hidden=true;$('messages').scrollTop=$('messages').scrollHeight;return item; }
function clearChat(){state.chat=null;$('messages').replaceChildren();$('welcome').hidden=false;$('message').value='';resizeInput();showPage('chat');}
function dateLabel(value){const date=new Date(value.includes('T')?value:value.replace(' ','T')+'Z');return Number.isNaN(date.getTime())?'':new Intl.DateTimeFormat('es',{dateStyle:'medium',timeStyle:'short'}).format(date);}
async function connect(){ const data=await api('/api/session'); state.model=data.model;$('model-name').textContent=data.model;$('connection').textContent='Conectada a tu PC';$('connection').dataset.connected='true';$('nav').hidden=false;$('new-chat').hidden=false;showPage('chat');}
$('login-form').onsubmit=async event=>{event.preventDefault();const button=event.submitter;button.disabled=true;try{await api('/api/login',{code:$('access-code').value.trim()});$('access-code').value='';await connect();notice('Ya estás con Karen.');}catch(e){notice(e.message);}finally{button.disabled=false;}};
$('new-chat').onclick=()=>{if(!state.busy)clearChat();};
document.querySelectorAll('[data-page]').forEach(el=>el.onclick=()=>showPage(el.dataset.page));
document.querySelectorAll('[data-prompt]').forEach(el=>el.onclick=()=>{$('message').value=el.dataset.prompt;resizeInput();$('message').focus();});
function resizeInput(){$('message').style.height='auto';$('message').style.height=Math.min($('message').scrollHeight,150)+'px';}
$('message').oninput=resizeInput;
$('composer').onsubmit=async event=>{event.preventDefault();const message=$('message').value.trim();if(!message||state.busy)return;state.busy=true;$('send').disabled=true;$('new-chat').disabled=true;$('generation-status').textContent='Karen está pensando… Puedes consultar otras secciones mientras esperas.';let pending;
  try{if(!state.chat){const data=await api('/api/chats',{});state.chat=data.id;}pending=addMessage('user',message);$('message').value='';resizeInput();const result=await api('/api/message',{chat_id:state.chat,message});addMessage('assistant',result.answer);if($('read-aloud').checked)speak(result.answer);}
  catch(e){if(pending)pending.remove();$('welcome').hidden=$('messages').children.length>0;$('message').value=message;resizeInput();notice(e.message);}
  finally{state.busy=false;$('send').disabled=false;$('new-chat').disabled=false;$('generation-status').textContent='Puedes usar el dictado del teclado del iPhone.';}
};
async function openChat(id){if(state.busy)return notice('Espera a que Karen termine antes de cambiar de conversación.');const result=await api('/api/v1/chats/'+encodeURIComponent(id)+'/exchanges');state.chat=id;$('messages').replaceChildren();$('welcome').hidden=result.exchanges.length>0;for(const turn of result.exchanges){addMessage('user',turn.prompt);addMessage('assistant',turn.answer);}showPage('chat');$('messages').scrollTop=$('messages').scrollHeight;}
function renderHistory(){const list=$('chat-list');list.replaceChildren();const query=$('search').value.toLocaleLowerCase();const chats=state.chats.filter(c=>c.title.toLocaleLowerCase().includes(query));if(!chats.length){list.append(empty(query?'No hay conversaciones con ese título.':'Tu próxima conversación empieza en Chat.'));return;}for(const chat of chats){const button=document.createElement('button');button.className='list-item';const title=document.createElement('h3');title.textContent=chat.title;const time=document.createElement('time');time.textContent=dateLabel(chat.updated);button.append(title,time);button.onclick=()=>openChat(chat.id).catch(e=>notice(e.message));list.append(button);}}
async function loadHistory(){const result=await api('/api/v1/chats');state.chats=result.chats;renderHistory();}
function empty(text){const p=document.createElement('p');p.className='empty';p.textContent=text;return p;}
$('search').oninput=renderHistory;$('refresh-history').onclick=()=>loadHistory().catch(e=>notice(e.message));
const statusNames={pending:'Pendiente',running:'En curso',completed:'Completada',failed:'Falló',cancelled:'Cancelada',interrupted:'Interrumpida',uncertain:'Requiere revisión',active:'Activa',resolved:'Resuelta',acknowledged:'Confirmada',confirmed:'Confirmado',inferred:'Inferido',normal:'Normal',high:'Alta',critical:'Crítica'};
async function loadResource(){const request=++state.resourceRequest;const resource=state.resource;const list=$('resource-list');list.replaceChildren(empty('Consultando tu PC…'));$('memory-form').hidden=resource!=='memories';let path='/api/v1/'+resource;if(resource==='memories')path+='?project='+encodeURIComponent($('project').value.trim());try{const result=await api(path);if(request!==state.resourceRequest)return;list.replaceChildren();const records=result[resource]||[];if(!records.length){list.append(empty({tasks:'Todavía no hay tareas registradas.',alerts:'No hay alertas guardadas.',memories:'No hay recuerdos públicos para este proyecto.'}[resource]));return;}for(const record of records){const item=document.createElement('article');item.className='list-item';const h=document.createElement('h3');h.textContent=resource==='memories'?record.content:resource==='alerts'?record.label:'Tarea '+record.id.slice(0,8);const p=document.createElement('p');p.textContent=statusNames[record.status]||record.status||'Sin estado';if(record.priority)p.textContent+=' · Prioridad '+(statusNames[record.priority]||record.priority);const time=document.createElement('time');time.textContent=dateLabel(record.updated_at||record.created_at||'');item.append(h,p,time);list.append(item);}}catch(e){if(request===state.resourceRequest)list.replaceChildren(empty(e.message));}}
document.querySelectorAll('[data-resource]').forEach(button=>button.onclick=()=>{state.resource=button.dataset.resource;document.querySelectorAll('[data-resource]').forEach(el=>el.setAttribute('aria-pressed',String(el===button)));loadResource();});
$('memory-form').onsubmit=event=>{event.preventDefault();loadResource();};$('refresh-resource').onclick=()=>loadResource();
try{$('read-aloud').checked=localStorage.getItem('karen-read')==='yes';}catch{}
$('read-aloud').onchange=()=>{try{localStorage.setItem('karen-read',$('read-aloud').checked?'yes':'no');}catch{}if($('read-aloud').checked)speak('Hola. Estoy aquí.');else window.speechSynthesis?.cancel();};
$('stop-speaking').onclick=()=>window.speechSynthesis?.cancel();
$('logout').onclick=async()=>{if(state.busy)return notice('Espera a que termine la respuesta antes de desconectar.');try{await api('/api/logout',{});state.chat=null;state.chats=[];$('messages').replaceChildren();$('chat-list').replaceChildren();$('resource-list').replaceChildren();$('welcome').hidden=false;$('message').value='';showLogin();}catch(e){notice(e.message);}};
window.addEventListener('offline',()=>{$('connection').textContent='Sin conexión';notice('Sin conexión. Tus chats siguen guardados en el PC.');});window.addEventListener('online',()=>{api('/api/session').then(()=>{$('connection').textContent='Conectada a tu PC';}).catch(e=>notice(e.message));});
if(window.visualViewport){const fit=()=>{document.querySelector('.app').style.height=window.visualViewport.height+'px';};window.visualViewport.addEventListener('resize',fit);fit();}
if('serviceWorker' in navigator)navigator.serviceWorker.register('/sw.js').catch(()=>{});
connect().catch(e=>{showLogin();if(!e.message.includes('código'))notice(e.message);});
