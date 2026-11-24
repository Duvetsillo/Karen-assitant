import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process';
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import type { VoiceStyle } from '../shared/types.js';

/** Bounded persistent CPU worker; audio and text stay in pipes. */
export class FastVoice {
  private child?: ChildProcessWithoutNullStreams;
  private root = '';
  private output = '';
  private pending?: {resolve(value:ArrayBuffer):void;reject(error:Error):void};
  private timer?: ReturnType<typeof setTimeout>;
  constructor(private worker:string) {}
  cancelActive() {if(this.pending)this.close();}
  close() {
    const child=this.child;this.child=undefined;
    clearTimeout(this.timer);
    this.pending?.reject(new Error('Voz rápida cancelada.'));
    this.pending=undefined;this.output='';child?.kill();
  }
  synthesize(root:string,text:string,style:VoiceStyle):Promise<ArrayBuffer> {
    if(this.pending)return Promise.reject(new Error('Ya hay una síntesis rápida en curso.'));
    if(this.root!==root)this.close();
    this.root=root;clearTimeout(this.timer);
    const python=join(root,'voice-runtime/Scripts/python.exe');
    if(![python,this.worker,join(root,'voice-models/kokoro-v1.0.onnx'),join(root,'voice-models/voices-v1.0.bin')].every(existsSync))
      return Promise.reject(new Error('Faltan los recursos opcionales de Kokoro en la carpeta de voz.'));
    return new Promise((resolve,reject)=>{
      this.pending={resolve,reject};
      if(!this.child){
        const child=spawn(python,['-u',this.worker,root],{cwd:root,windowsHide:true,stdio:['pipe','pipe','pipe'],env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}});
        this.child=child;
        const fail=()=>{if(this.child===child)this.close();};
        child.on('error',fail);child.on('exit',fail);child.stdin.on('error',fail);child.stderr.resume();
        child.stdout.on('data',(data:Buffer)=>{
          if(this.child!==child)return;
          this.output+=data.toString();
          if(this.output.length>32_000_000){fail();return;}
          const end=this.output.indexOf('\n');if(end<0)return;
          const line=this.output.slice(0,end);this.output=this.output.slice(end+1);
          try{
            const result=JSON.parse(line) as {audio?:string;error?:string};
            if(typeof result.audio!=='string')throw new Error('El motor rápido no pudo generar audio.');
            const bytes=Buffer.from(result.audio,'base64');
            if(bytes.length>24_000_000||bytes.subarray(0,4).toString()!=='RIFF')throw new Error('Audio rápido inválido.');
            const pending=this.pending;this.pending=undefined;clearTimeout(this.timer);
            this.timer=setTimeout(()=>this.close(),120000);this.timer.unref();
            pending?.resolve(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength));
          }catch(error){this.pending?.reject(error instanceof Error?error:new Error('Respuesta de voz inválida.'));this.pending=undefined;fail();}
        });
      }
      this.timer=setTimeout(()=>this.close(),60000);
      this.child!.stdin.write(JSON.stringify({text,style})+'\n');
    });
  }
}
