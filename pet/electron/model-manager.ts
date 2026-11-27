import { spawn, execFile } from 'node:child_process';
import { freemem } from 'node:os';
import { promisify } from 'node:util';
import type { Settings, ModelSelection } from '../shared/types.js';
import { chooseModel, type ModelInspection, type ModelManagerStatus } from '../shared/models.js';
import { MicrophoneArbiter } from './core-resource.js';

const execute=promisify(execFile);
export interface TurnModels {
  inspect(message?:string,images?:boolean):Promise<ModelManagerStatus>;
  prepare(selection:ModelSelection,message:string,images:boolean):Promise<{id:string;reason:string}>;
  acquire():Promise<void>;
  release():void;
}
/** One metadata worker on demand. No downloads or inference during discovery. */
export class LocalModelManager implements TurnModels {
  private cached?:ModelManagerStatus;
  private catalogAt=0;
  private token?:string;
  private inspecting?:Promise<ModelManagerStatus>;
  private lastReason='Aún no se ha enviado una tarea.';
  constructor(private settings:()=>Settings,private endpoint:()=>string,
    private python:()=>string,private worker:string,private arbiter:MicrophoneArbiter){}

  async inspect(message='',images=false):Promise<ModelManagerStatus>{
    if(!message&&this.cached&&Date.now()-this.cached.checkedAt<15000)return {...this.cached,reason:this.lastReason};
    if(this.inspecting)await this.inspecting.catch(()=>{});
    const operation=this.readMetadata(message,images);this.inspecting=operation;
    try{return await operation;}finally{if(this.inspecting===operation)this.inspecting=undefined;}
  }
  private async readMetadata(message:string,images:boolean):Promise<ModelManagerStatus>{
    const settings=this.settings();
    const budget:ModelInspection['budget']={ram_available_bytes:freemem(),vram_available_bytes:null,vram_total_bytes:null};
    try{
      const {stdout}=await execute('nvidia-smi',['--query-gpu=memory.free,memory.total','--format=csv,noheader,nounits'],{timeout:2000,windowsHide:true,maxBuffer:4096});
      const [free,total]=stdout.trim().split('\n')[0].split(',').map(Number);
      if(Number.isFinite(free)&&Number.isFinite(total)&&free>=0&&total>0&&free<=total){budget.vram_available_bytes=free*1048576;budget.vram_total_bytes=total*1048576;}
    }catch{/* GPU unavailable: rank conservatively with host RAM. */}
    const profile=settings.resourceProfile==='performance'?'quality':settings.resourceProfile==='economy'?'economy':'balanced';
    const catalog=Date.now()-this.catalogAt<60000?this.cached?.catalog:undefined;
    const input={endpoint:this.endpoint(),profile,budget,message,images,catalog};
    const inspection=await new Promise<ModelInspection>((resolve,reject)=>{
      const child=spawn(this.python(),['-u',this.worker],{windowsHide:true,stdio:'pipe',env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}});
      let output='';let settled=false;
      const finish=(error?:Error,value?:ModelInspection)=>{if(settled)return;settled=true;clearTimeout(timer);if(error){child.kill();reject(error);}else resolve(value!);};
      const timer=setTimeout(()=>finish(new Error('Ollama tarda en responder. Revisa el servicio local.')),30000);
      child.on('error',()=>finish(new Error('No se pudo iniciar Python. Configura los recursos locales en Voz.')));
      child.stdin.on('error',()=>finish(new Error('Se cerró la consulta local de modelos.')));
      child.stderr.resume();
      child.stdout.on('data',data=>{output+=data.toString();if(output.length>262144)finish(new Error('Catálogo local demasiado grande.'));});
      child.on('close',code=>{try{const result=JSON.parse(output);if(code||result.error||!Array.isArray(result.catalog)||!result.rankings)throw new Error();finish(undefined,result);}catch{finish(new Error('No se pudo consultar Ollama. Comprueba el servicio y Python con requests.'));}});
      child.stdin.end(JSON.stringify(input));
    });
    if(!catalog)this.catalogAt=Date.now();
    this.cached={...inspection,reason:this.lastReason,checkedAt:Date.now()};return this.cached;
  }
  async prepare(selection:ModelSelection,message:string,images:boolean){
    const settings=this.settings();
    if(settings.mode!=='normal')throw new Error('Vuelve al modo Normal para iniciar una nueva inferencia. Los comandos locales siguen disponibles.');
    const inspection=await this.inspect(message,images);
    if(this.settings().mode!=='normal')throw new Error('El modo cambió durante la preparación. Vuelve a Normal.');
    const choice=chooseModel(inspection,selection.models.filter(m=>m.available).map(m=>m.id),
      settings.resourceProfile==='economy'&&settings.routingMode!=='manual'?'economy':settings.routingMode,
      selection.effective,selection.selected,images);
    this.lastReason=choice.reason;
    return choice;
  }
  async acquire(){
    if(this.settings().mode!=='normal')throw new Error('Vuelve al modo Normal antes de inferir.');
    if(this.token)throw new Error('Ya hay una inferencia de Karen en curso.');
    try{this.token=await this.arbiter.claim(0);}catch{throw new Error('Otra interfaz de Karen está usando la inferencia local. Espera a que termine.');}
  }
  release(){if(this.token){this.arbiter.release(0,this.token);this.token=undefined;}}
  dispose(){this.release();this.arbiter.close();}
}
