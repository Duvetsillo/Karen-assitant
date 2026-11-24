const $=id=>document.getElementById(id);
let plan=null,chat=null,running=false;
let connected=false,ollamaReady=false,activeJobs=0,remoteBusy=false,speaking=false,preparingVoice=false,voiceAnalyser=null;
const activityKeys=new Set();
function activity(text,key){
  if(key&&activityKeys.has(key))return;
  if(key)activityKeys.add(key);
  if(activityKeys.size>200)activityKeys.delete(activityKeys.values().next().value);
  const list=$('activity');
  if(!list.dataset.started){list.replaceChildren();list.dataset.started='true';}
  const item=document.createElement('li'),time=document.createElement('time');
  time.textContent=new Intl.DateTimeFormat('es-BO',{timeZone:'America/La_Paz',hour:'2-digit',minute:'2-digit',second:'2-digit'}).format(new Date());
  item.append(time,document.createTextNode(text));list.prepend(item);
  while(list.children.length>20)list.lastElementChild.remove();
}
function coreState(){
  const busy=activeJobs>0||remoteBusy||preparingVoice;
  document.body.dataset.state=!connected?'offline':speaking?'speaking':busy?'busy':'ready';
  $('core-mode').textContent=!connected?'Sin conexión':speaking?'Hablando':busy?'Procesando':ollamaReady?'Disponible':'Núcleo conectado';
  $('core-detail').textContent=!connected?'Revisa el servidor de Karen en este PC.':speaking?'Reproduciendo la voz local de Karen.':busy?'Hay una solicitud en curso. Consulta su estado y resultado.':ollamaReady?'Ollama local listo. Tú decides el siguiente paso.':'Consultando disponibilidad de Ollama local.';
}
async function working(label,work){
  activeJobs++;coreState();activity(label);
  try{return await work();}finally{activeJobs--;coreState();}
}
function clock(){
  if(document.hidden)return;
  const now=new Date();
  $('clock').textContent=new Intl.DateTimeFormat('es-BO',{timeZone:'America/La_Paz',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}).format(now);
  $('date').textContent=new Intl.DateTimeFormat('es-BO',{timeZone:'America/La_Paz',weekday:'short',day:'2-digit',month:'short',year:'numeric'}).format(now)+' · La Paz';
}
function preference(key,fallback){try{return localStorage.getItem(key)??fallback;}catch{return fallback;}}
function savePreference(key,value){try{localStorage.setItem(key,value);}catch{}}
function motion(value){document.body.dataset.motion=String(value);$('motion').setAttribute('aria-pressed',String(value));$('motion').textContent='Animación: '+(value?'activa':'pausada');}
function palette(value){document.body.dataset.palette=value;$('palette').setAttribute('aria-pressed',String(value==='green'));$('palette').textContent='Color: '+(value==='green'?'verde':'cian');}
$('motion').onclick=()=>{const enabled=document.body.dataset.motion!=='true';motion(enabled);savePreference('karen-hud-motion',String(enabled));};
$('palette').onclick=()=>{const value=document.body.dataset.palette==='green'?'cyan':'green';palette(value);savePreference('karen-hud-palette',value);};
function particleForm(value){document.body.dataset.form=value;$('form-toggle').setAttribute('aria-pressed',String(value==='organic'));$('form-toggle').textContent='Forma: '+(value==='organic'?'orgánica':'esfera');}
$('form-toggle').onclick=()=>{const value=document.body.dataset.form==='organic'?'sphere':'organic';particleForm(value);savePreference('karen-particle-form',value);};
particleForm(preference('karen-particle-form','organic')==='sphere'?'sphere':'organic');
motion(preference('karen-hud-motion','true')==='true');palette(preference('karen-hud-palette','cyan')==='green'?'green':'cyan');
document.addEventListener('visibilitychange',()=>{document.body.dataset.hidden=String(document.hidden);clock();});
clock();setInterval(clock,1000);
const states={pending:'Pendiente',running:'En ejecución',completed:'Verificado',awaiting_approval:'Espera aprobación en escritorio',interrupted:'Interrumpido; puede reanudarse',uncertain:'Resultado incierto; revisar antes de repetir',canceled:'Cancelado',failed:'Falló',denied:'No autorizado',blocked:'Dependencias pendientes'};
let noticeTimer;
function notify(text){clearTimeout(noticeTimer);$('notice').textContent=text;$('notice').hidden=false;activity(text);noticeTimer=setTimeout(()=>{$('notice').hidden=true;},12000);}
async function api(path,data){let response;try{response=await fetch('/api/'+path,{method:data===undefined?'GET':'POST',headers:data===undefined?{}:{'Content-Type':'application/json'},body:data===undefined?undefined:JSON.stringify(data),credentials:'same-origin',cache:'no-store'});}catch{throw Error('No hay conexión con Karen. Revisa el PC y Tailscale.');}const result=await response.json();if(response.status===401){connected=false;ollamaReady=false;coreState();$('login').hidden=false;$('workbench').hidden=true;}if(!response.ok)throw Error(result.error||'No se pudo completar la operación.');return result;}
function gib(value){return Number.isFinite(value)?(value/1024**3).toFixed(1)+' GiB':'Sin muestra';}
async function refresh(){try{const status=await api('core2/status');connected=true;remoteBusy=Boolean(status.models.active_model);coreState();$('connection').textContent='Core 2 conectado · IA local';const hardware=status.models.hardware,latest=status.diagnostics.latest;$('ram').textContent=gib(hardware.ram_available_bytes);$('vram').textContent=gib(hardware.vram_available_bytes);const last=status.models.latency.at(-1);$('model').textContent=status.models.active_model?status.models.active_model+(status.models.active_device?' · '+status.models.active_device.toUpperCase():''):(last?last.model+(last.device?' · '+last.device.toUpperCase():'')+' · última respuesta':'En reposo');const cpu=latest?.cpu_percent;$('cpu').textContent=Number.isFinite(cpu)?cpu.toFixed(0)+'%':'—';$('cpu-ring').style.strokeDasharray=(Number.isFinite(cpu)?Math.max(0,Math.min(100,cpu)):0)+' 100';$('diagnostics').textContent=status.diagnostics.recommendations.join(' ')|| (status.diagnostics.samples?status.diagnostics.samples+(status.diagnostics.samples===1?' muestra.':' muestras.')+' No hay tendencias suficientes para recomendar cambios.':'Prepara un diagnóstico para obtener muestras.');if(status.diagnostics.stale)$('diagnostics').textContent='Muestra anterior (más de 5 minutos). Prepara otro diagnóstico para medir el estado actual.';$('vision-state').textContent=status.vision.capturing?'Capturando por solicitud':status.vision.paused?'Pausada. Sin captura continua.':'Habilitada solo bajo demanda.';}catch(e){connected=false;coreState();$('connection').textContent='Core 2 no disponible';notify(e.message);}}
function showPlan(value){plan=value;activity('Plan: '+(states[value.status]||value.status),value.id+':'+value.status);$('plan-state').textContent=states[value.status]||value.status;const host=$('plan-steps');host.replaceChildren();const titles=Object.fromEntries(value.steps.map(step=>[step.step_id,step.label]));for(const step of value.steps){if(step.status==='completed')activity('Verificado: '+step.tool,value.id+':'+step.step_id+':completed');const item=document.createElement('article');item.className='step';const heading=document.createElement('div');heading.className='step-heading';const title=document.createElement('h3');title.textContent=step.label;const status=document.createElement('small');status.textContent=states[step.status]||step.status;heading.append(title,status);const info=document.createElement('p');info.textContent=step.agent+' · '+step.tool+' · '+({read:'Lectura',reversible:'Cambio reversible',sensitive:'Requiere aprobación',destructive:'Confirmación explícita'}[step.permission]||step.permission);item.append(heading,info);if(step.depends?.length){const dependencies=document.createElement('p');dependencies.textContent='Después de: '+step.depends.map(id=>titles[id]||id).join('; ');item.append(dependencies);}if(step.error){const error=document.createElement('p');error.textContent='Resultado: '+step.error;item.append(error);}if('result'in step){const evidence=document.createElement('pre');evidence.textContent=JSON.stringify(step.result,null,2);const details=document.createElement('details');const summary=document.createElement('summary');summary.textContent='Ver resultado verificado';details.append(summary,evidence);item.append(details);}host.append(item);}$('run').disabled=running||!['pending','awaiting_approval'].includes(value.status);$('resume').disabled=running||value.status!=='interrupted';$('cancel').disabled=!['pending','running','awaiting_approval','interrupted'].includes(value.status);$('remember').disabled=value.status!=='completed';$('remember').hidden=value.status!=='completed';$('resume').hidden=value.status!=='interrupted';$('run').hidden=!['pending','awaiting_approval'].includes(value.status);$('cancel').hidden=!['pending','running','awaiting_approval','interrupted'].includes(value.status);}
$('plan-form').onsubmit=async e=>{e.preventDefault();$('prepare').disabled=true;try{showPlan(await working('Preparando plan; aún sin ejecutar.',()=>api('core2/plan',{goal:$('goal').value.trim()})));}catch(error){notify(error.message);}finally{$('prepare').disabled=false;}};
async function execute(resume=false){
  if(!plan||running)return;
  const identity=plan.id;running=true;showPlan(plan);$('prepare').disabled=true;
  const poll=setInterval(()=>api('core2/plans/'+identity).then(showPlan).catch(()=>{}),1800);
  try{
    showPlan(await working(resume?'Reanudando plan.':'Ejecutando lecturas autorizadas.',()=>api(resume?'core2/resume':'core2/run',{id:identity})));
    await refresh();
  }catch(e){notify(e.message);}finally{clearInterval(poll);running=false;$('prepare').disabled=false;showPlan(plan);}
}
$('run').onclick=()=>execute();$('resume').onclick=()=>execute(true);$('cancel').onclick=async()=>{if(plan)try{showPlan(await api('core2/cancel',{id:plan.id}));}catch(e){notify(e.message);}};
$('remember').onclick=async()=>{try{await api('core2/remember',{id:plan.id});notify('Procedimiento verificado guardado en la memoria de Karen.');}catch(e){notify(e.message);}};
$('refresh-plans').onclick=async()=>{try{const result=await api('core2/plans');$('saved-plans').replaceChildren();for(const item of result.plans){const button=document.createElement('button');button.className='quiet';button.textContent=item.goal+' · '+(states[item.status]||item.status);button.onclick=()=>{if(running){notify('Espera a que termine el plan activo o cancélalo.');return;}api('core2/plans/'+item.id).then(showPlan).catch(e=>notify(e.message));};$('saved-plans').append(button);}}catch(e){notify(e.message);}};
$('memory-form').onsubmit=async e=>{e.preventDefault();try{const result=await api('core2/memory?project='+encodeURIComponent($('project').value.trim())+'&q='+encodeURIComponent($('query').value));$('memories').replaceChildren();for(const memory of result.memories){const p=document.createElement('p');p.className='memory';const type=document.createElement('small');type.textContent=memory.kind+' · '+memory.state;p.append(type,document.createTextNode(memory.content));$('memories').append(p);}if(!result.memories.length)$('memories').textContent='Sin recuerdos para esta consulta.';}catch(error){notify(error.message);}};
$('vision').onclick=async()=>{$('vision').disabled=true;$('vision-state').textContent='Analizando una captura de la ventana activa…';try{const result=await working('Analizando una captura bajo demanda.',()=>api('core2/vision',{scope:'window'}));$('vision-result').textContent=result.analysis;}catch(e){notify(e.message);}finally{$('vision').disabled=false;refresh();}};
$('pause-vision').onclick=async()=>{try{await api('core2/vision/pause',{});refresh();}catch(e){notify(e.message);}};
function message(role,text){setConversation(true);const item=document.createElement('p');item.className='message '+role;const name=document.createElement('strong');name.textContent=role==='user'?'Tú':'Karen';item.append(name,document.createTextNode(text));if(role==='assistant'){const listen=document.createElement('button');listen.className='quiet listen-response';listen.textContent='Escuchar';listen.onclick=()=>readVoice(text);item.append(listen);}$('messages').querySelector('.welcome')?.remove();$('messages').append(item);$('messages').scrollTop=$('messages').scrollHeight;}
$('chat-form').onsubmit=async e=>{
  e.preventDefault();const text=$('message').value.trim();if(!text)return;
  stopVoice();if(voiceEnabled)unlockVoice();
  $('send').disabled=true;$('chat-state').textContent='Karen está preparando la respuesta en tu PC…';
  try{
    if(!chat)chat=(await api('chats',{})).id;
    message('user',text);
    const result=await working('Solicitud de conversación enviada al núcleo local.',()=>api('message',{chat_id:chat,message:text}));
    message('assistant',result.answer);$('message').value='';activity('Respuesta recibida.');
    $('chat-state').textContent='Respuesta recibida desde Karen.';refresh();if(voiceEnabled)readVoice(result.answer);
  }catch(error){notify(error.message);$('chat-state').textContent='No se recibió respuesta. Puedes volver a intentarlo.';}
  finally{$('send').disabled=false;}
};
async function init(){await api('session');connected=true;coreState();activity('Conectado con Core 2.','connected');$('login').hidden=true;$('workbench').hidden=false;$('notice').hidden=true;await refresh();api('core2/models').then(result=>{ollamaReady=result.models.length>0;coreState();$('connection').textContent=result.models.length?'Ollama conectado · '+result.models.length+' modelos locales':'Ollama conectado · sin modelos locales compatibles';}).catch(e=>{ollamaReady=false;coreState();$('core-detail').textContent='Ollama no está disponible; revisa su servicio local.';$('connection').textContent='Ollama no disponible';notify(e.message);});}
$('login').onsubmit=async e=>{e.preventDefault();try{await api('login',{code:$('code').value.trim()});$('code').value='';await init();}catch(error){notify(error.message);}};
$('refresh').onclick=refresh;init().catch(e=>notify(e.message));

// Panels remain available without occupying the particle stage by default.
function setConversation(open){$('conversation-panel').hidden=!open;$('conversation-toggle').setAttribute('aria-expanded',String(open));}
$('conversation-toggle').onclick=()=>setConversation($('conversation-panel').hidden);
$('tools-toggle').onclick=()=>{const open=$('tools').hidden;$('tools').hidden=!open;$('tools-toggle').setAttribute('aria-expanded',String(open));if(open)$('tools').scrollIntoView({block:'start'});};


// Local 3D projection onto Canvas 2D. No WebGL context or inference resources.
(() => {
  const canvas=$('presence'),context=canvas.getContext('2d',{alpha:true});
  if(!context){canvas.hidden=true;return;}
  const reduce=matchMedia('(prefers-reduced-motion: reduce)');
  let width=0,height=0,points=[],edges=[],projected=[],frame=0,timer=0;
  let time=0,lastTime=0,lastDraw=0,visible=false,disposed=false;
  let voiceEnvelope=0;const voiceSamples=new Float32Array(512);
  let paletteName='',rgb='125,225,239',glow=null;
  const golden=Math.PI*(3-Math.sqrt(5));
  function build(count){
    points=[];edges=[];projected=[];
    for(let i=0;i<count;i++){
      const y=1-2*(i+.5)/count,ring=Math.sqrt(1-y*y),angle=i*golden;
      points.push({x:Math.cos(angle)*ring,y,z:Math.sin(angle)*ring,angle:Math.atan2(Math.sin(angle)*ring,Math.cos(angle)*ring),seed:Math.sin(i*127.1)*.5+.5});
      projected.push({x:0,y:0,z:0,scale:1});
    }
    // Fixed sparse surface neighbours: calculated once, never a per-frame all-pairs search.
    for(let i=0;i<count;i++){
      const near=[];const a=points[i];
      for(let j=i+1;j<count;j++){
        const b=points[j],distance=(a.x-b.x)**2+(a.y-b.y)**2+(a.z-b.z)**2;
        if(distance<.045)near.push([distance,j]);
      }
      near.sort((a,b)=>a[0]-b[0]);
      for(const pair of near.slice(0,2))edges.push([i,pair[1]]);
    }
    canvas.dataset.particles=String(count);
  }
  function resize(){
    const box=canvas.getBoundingClientRect();
    if(!box.width||!box.height)return;
    width=box.width;height=box.height;
    const density=Math.min(devicePixelRatio||1,1.5);
    canvas.width=Math.round(width*density);canvas.height=Math.round(height*density);
    context.setTransform(density,0,0,density,0,0);
    const count=width<720?680:1450;
    if(points.length!==count)build(count);
    draw();schedule();
  }
  function colors(){
    const value=document.body.dataset.palette;
    if(value===paletteName&&glow)return;
    paletteName=value;rgb=value==='green'?'112,239,178':'127,225,247';
    glow=document.createElement('canvas');glow.width=256;glow.height=256;
    const g=glow.getContext('2d'),gradient=g.createRadialGradient(128,128,0,128,128,128);
    gradient.addColorStop(0,'rgba('+rgb+',.52)');
    gradient.addColorStop(.18,'rgba('+rgb+',.16)');
    gradient.addColorStop(.6,'rgba('+rgb+',.024)');
    gradient.addColorStop(1,'rgba('+rgb+',0)');
    g.fillStyle=gradient;g.fillRect(0,0,256,256);
  }
  function draw(){
    if(!width||!height||!points.length)return;
    colors();context.clearRect(0,0,width,height);
    const busy=document.body.dataset.state==='busy',organic=document.body.dataset.form==='organic';
    let target=0;
    if(speaking&&voiceAnalyser&&canMove()){
      voiceAnalyser.getFloatTimeDomainData(voiceSamples);
      let energy=0;for(const value of voiceSamples)energy+=value*value;
      target=Math.min(1,Math.sqrt(energy/voiceSamples.length)*5);
    }
    // Attack/release smoothing follows the real signal without random or microphone input.
    voiceEnvelope+=(target-voiceEnvelope)*(target>voiceEnvelope?.55:.18);
    if(!speaking||!canMove())voiceEnvelope=0;
    const voice=voiceEnvelope;
    const radius=Math.min(width*.29,height*.20,295)*(1+voice*.22);
    const cx=width*.5,cy=height*.35;
    const rotation=time*.115,cr=Math.cos(rotation),sr=Math.sin(rotation);
    const tilt=.22+Math.sin(time*.16)*.13,ct=Math.cos(tilt),st=Math.sin(tilt);
    const breath=1+.018*Math.sin(time*.9);
    canvas.dataset.voiceLevel=voice.toFixed(3);
    canvas.dataset.voicePeak=Math.max(Number(canvas.dataset.voicePeak||0),voice).toFixed(3);
    context.globalCompositeOperation='lighter';
    context.globalAlpha=.65+voice*.35;
    context.drawImage(glow,cx-radius*1.65,cy-radius*1.65,radius*3.3,radius*3.3);context.globalAlpha=1;
    for(let i=0;i<points.length;i++){
      const p=points[i];
      const ripple=.1*Math.sin(p.y*5+Math.cos(p.angle*3)+time*.43)+.055*Math.sin(p.x*7-p.z*4-time*.6);
      const fold=.055*Math.sin(p.angle*3+time*.37)*(1-p.y*p.y);
      const r=breath*(1+(ripple+fold)*(organic?1.9:.6)+(busy?.065*Math.sin(p.y*8+time*1.7):0)+voice*.20*Math.sin(p.y*7+p.z*3+time*2));
      const x=p.x*r,y=p.y*r,z=p.z*r;
      const rx=x*cr+z*sr,rz=z*cr-x*sr;
      const ry=y*ct-rz*st,depth=y*st+rz*ct;
      const perspective=3.8/(3.8-depth);
      const output=projected[i];output.x=cx+rx*radius*perspective;output.y=cy+ry*radius*perspective;output.z=depth;output.scale=perspective;
    }
    // Depth batches keep fine filaments translucent and the far side perceptibly dimmer.
    for(let bucket=0;bucket<5;bucket++){
      context.beginPath();
      for(const [a,b] of edges){
        const p=projected[a],q=projected[b];
        const level=Math.min(4,Math.max(0,Math.floor(((p.z+q.z)*.25+.5)*5)));
        if(level!==bucket)continue;
        context.moveTo(p.x,p.y);context.lineTo(q.x,q.y);
      }
      context.strokeStyle='rgba('+rgb+','+(.018+bucket*.022)+')';
      context.lineWidth=.5+bucket*.075;context.stroke();
    }
    for(let bucket=0;bucket<5;bucket++){
      context.beginPath();
      for(let i=0;i<points.length;i++){
        const p=projected[i];
        const level=Math.min(4,Math.max(0,Math.floor((p.z*.5+.5)*5)));
        if(level!==bucket)continue;
        const size=(.35+points[i].seed*.65)*p.scale;
        context.moveTo(p.x+size,p.y);context.arc(p.x,p.y,size,0,Math.PI*2);
      }
      context.fillStyle='rgba('+rgb+','+Math.min(1,.14+bucket*.15+voice*.22)+')';context.fill();
    }
    // Curving interior filaments break the surface into fluid, non-mechanical strands.
    for(let strand=0;strand<23;strand++){
      const angle=strand*golden+time*.075;
      context.beginPath();
      for(let j=0;j<62;j++){
        const u=j/61*Math.PI*2;
        const spiral=angle+u*.6;
        const deformation=.73+.15*Math.sin(u*3+time*.4+strand);
        const x=Math.cos(u)*Math.cos(spiral)*deformation;
        const y=Math.sin(u)*deformation;
        const z=Math.cos(u)*Math.sin(spiral)*deformation;
        const rx=x*cr+z*sr,rz=z*cr-x*sr;
        const perspective=3.8/(3.8-rz);
        const px=cx+rx*radius*perspective,py=cy+(y*ct-rz*st)*radius*perspective;
        if(j===0)context.moveTo(px,py);else context.lineTo(px,py);
      }
      context.strokeStyle='rgba('+rgb+','+(.085+voice*.09)+')';context.lineWidth=.7;context.stroke();
    }
    // Sparse drifting points remain near the sphere, rather than covering the workspace.
    context.fillStyle='rgba('+rgb+',.35)';
    for(let i=0;i<85;i++){
      const angle=i*golden+time*(.016+(i%3)*.003);
      const distance=radius*(1.18+.32*Math.sin(i*8.7)**2);
      const px=cx+Math.cos(angle)*distance,py=cy+Math.sin(angle)*distance*.85;
      context.fillRect(px,py,i%7===0?1.5:.7,i%7===0?1.5:.7);
    }
    context.globalCompositeOperation='source-over';
    canvas.dataset.frames=String(++frame);
  }
  // The intersection observer already pauses an offscreen canvas. Opening tools must
  // not freeze a still-visible sphere while the user writes or waits for a reply.
  function canMove(){return !disposed&&visible&&!document.hidden&&!$('workbench').hidden&&document.body.dataset.motion==='true'&&!reduce.matches;}
  function tick(now){
    timer=0;if(!canMove()){lastTime=0;return;}
    const interval=(document.body.dataset.state==='busy'||speaking)?1000/30:1000/24;
    if(now-lastDraw>=interval){
      if(lastTime)time+=Math.min((now-lastTime)/1000,.12);
      lastTime=now;lastDraw=now;draw();
    }
    timer=requestAnimationFrame(tick);
  }
  function schedule(){
    if(!canMove()){if(timer)cancelAnimationFrame(timer);timer=0;lastTime=0;draw();return;}
    if(!timer)timer=requestAnimationFrame(tick);
  }
  const sizeObserver=new ResizeObserver(resize);sizeObserver.observe(canvas);
  const visibility=new IntersectionObserver(entries=>{visible=entries[0].isIntersecting&&entries[0].intersectionRatio>0;schedule();});visibility.observe(canvas);
  const preferences=new MutationObserver(()=>{draw();schedule();});
  preferences.observe(document.body,{attributes:true,attributeFilter:['data-motion','data-state','data-palette','data-form']});
  preferences.observe($('workbench'),{attributes:true,attributeFilter:['hidden']});
  preferences.observe($('tools'),{attributes:true,attributeFilter:['hidden']});
  document.addEventListener('visibilitychange',schedule);
  reduce.addEventListener('change',schedule);
  window.addEventListener('pagehide',event=>{if(timer)cancelAnimationFrame(timer);timer=0;if(event.persisted)return;disposed=true;sizeObserver.disconnect();visibility.disconnect();preferences.disconnect();});
  window.addEventListener('pageshow',event=>{if(event.persisted){resize();schedule();}});
  resize();
})();


// Playback belongs to this browser, synthesis to the existing pinned voice on the PC.
let voiceEnabled=preference('karen-local-voice','true')==='true';
let voiceContext=null,voiceController=null,voiceSource=null,voiceIdentity=null,voiceEpoch=0,voiceResolve=null;
function voiceSetting(){
  $('voice-toggle').setAttribute('aria-pressed',String(voiceEnabled));
  $('voice-toggle').textContent='Voz: '+(voiceEnabled?'activa':'silenciada');
}
function unlockVoice(){
  try{
    const AudioEngine=window.AudioContext||window.webkitAudioContext;
    if(!AudioEngine)throw Error('Este navegador no puede reproducir el audio local.');
    voiceContext=voiceContext||new AudioEngine();
    // Called directly within a click/submit gesture; enables later WAV playback on Safari.
    return voiceContext.resume().catch(()=>{});
  }catch(error){$('voice-state').textContent=error.message;return Promise.resolve();}
}
function stopVoice(){
  voiceEpoch++;
  if(voiceSource){voiceSource.onended=null;try{voiceSource.stop();}catch{}voiceSource.disconnect();voiceSource=null;}
  if(voiceAnalyser){voiceAnalyser.disconnect();voiceAnalyser=null;}
  if(voiceResolve){voiceResolve();voiceResolve=null;}
  if(voiceController)voiceController.abort();voiceController=null;
  const id=voiceIdentity;voiceIdentity=null;
  if(id)fetch('/api/speech/cancel',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({id}),keepalive:true}).then(()=>releaseVoiceWeights()).catch(()=>{});
  speaking=false;preparingVoice=false;coreState();$('voice-stop').disabled=true;
  $('voice-state').textContent=voiceEnabled?'Femenina · serena · local':'Lectura automática silenciada';
}
function voiceId(){const bytes=new Uint8Array(16);crypto.getRandomValues(bytes);return Array.from(bytes,v=>v.toString(16).padStart(2,'0')).join('');}
function voiceChunks(text){
  // Short requests reduce initial latency and bound each synthesis; no browser/cloud fallback.
  const clean=String(text).replace(/```[\s\S]*?```/g,' Fragmento de código disponible en el chat. ').replace(/\[([^\]]+)\]\([^)]*\)/g,'$1').replace(/[#*_`]/g,'').trim();
  const chunks=[];let rest=clean;
  while(rest.length){let end=Math.min(rest.length,280);if(end<rest.length){const boundary=Math.max(rest.lastIndexOf('. ',end),rest.lastIndexOf('? ',end),rest.lastIndexOf('! ',end));if(boundary>60)end=boundary+1;else{const space=rest.lastIndexOf(' ',end);if(space>0)end=space;}}chunks.push(rest.slice(0,end).trim());rest=rest.slice(end).trim();}
  return chunks.filter(Boolean);
}
function releaseVoiceWeights(){return fetch('/api/speech/release',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:'{}',keepalive:true}).catch(()=>{});}
async function readVoice(text){
  stopVoice();const epoch=voiceEpoch;await unlockVoice();
  if(!voiceContext||voiceContext.state!=='running'){
    $('voice-state').textContent='Pulsa Escuchar o Probar voz para habilitar el sonido.';return;
  }
  $('voice-stop').disabled=false;
  try{
    for(const chunk of voiceChunks(text)){
      if(epoch!==voiceEpoch)return;
      voiceIdentity=voiceId();voiceController=new AbortController();
      preparingVoice=true;coreState();$('voice-state').textContent='Preparando voz local…';
      const response=await fetch('/api/speech',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',cache:'no-store',signal:voiceController.signal,body:JSON.stringify({id:voiceIdentity,text:chunk})});
      if(!response.ok){const value=await response.json();throw Error(value.error||'La voz local no respondió.');}
      if(!response.headers.get('Content-Type')?.startsWith('audio/wav'))throw Error('El servidor no devolvió audio WAV.');
      const encoded=await response.arrayBuffer();
      if(epoch!==voiceEpoch)return;
      const decoded=await voiceContext.decodeAudioData(encoded);
      if(epoch!==voiceEpoch)return;
      if(voiceContext.state!=='running')throw Error('El navegador pausó el sonido. Pulsa Escuchar para volver a intentarlo.');
      voiceSource=voiceContext.createBufferSource();voiceSource.buffer=decoded;
      voiceAnalyser=voiceContext.createAnalyser();voiceAnalyser.fftSize=512;
      $('presence').dataset.voicePeak='0';
      voiceSource.connect(voiceAnalyser);voiceAnalyser.connect(voiceContext.destination);
      preparingVoice=false;speaking=true;coreState();$('voice-state').textContent='Karen está hablando · voz serena';
      await new Promise(resolve=>{voiceResolve=resolve;voiceSource.onended=resolve;voiceSource.start();});
      voiceResolve=null;
      if(epoch!==voiceEpoch)return;
      voiceSource.disconnect();voiceSource=null;voiceAnalyser.disconnect();voiceAnalyser=null;voiceIdentity=null;
      speaking=false;coreState();
    }
    $('voice-state').textContent='Lectura terminada · voz local';
  }catch(error){
    if(epoch!==voiceEpoch||error.name==='AbortError')return;
    $('voice-state').textContent=error.message;notify(error.message);
  }finally{
    if(epoch===voiceEpoch){if(voiceSource){voiceSource.onended=null;try{voiceSource.stop();}catch{}voiceSource.disconnect();voiceSource=null;}if(voiceAnalyser){voiceAnalyser.disconnect();voiceAnalyser=null;}speaking=false;preparingVoice=false;coreState();voiceIdentity=null;voiceController=null;$('voice-stop').disabled=true;releaseVoiceWeights();}
  }
}
$('voice-toggle').onclick=()=>{voiceEnabled=!voiceEnabled;savePreference('karen-local-voice',String(voiceEnabled));voiceSetting();if(voiceEnabled)readVoice('Hola. Estoy aquí contigo.');else stopVoice();};
$('voice-test').onclick=()=>readVoice('Hola. Estoy aquí contigo.');
$('voice-stop').onclick=stopVoice;
window.addEventListener('pagehide',stopVoice);
voiceSetting();
