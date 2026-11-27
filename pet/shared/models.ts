export const ROUTING_MODES = ['auto','manual','fast','balanced','reasoning','coding','vision','voice','economy','local','privacy'] as const;
export type RoutingMode = typeof ROUTING_MODES[number];
export const RESOURCE_PROFILES = ['performance','balanced','economy','work'] as const;
export type ResourceProfile = typeof RESOURCE_PROFILES[number];
export interface InstalledModel {name:string;size:number;capabilities:string[];quantization?:string;}
export interface ModelInspection {
  catalog: InstalledModel[];
  kind: string;
  rankings: Record<string,string[]>;
  budget: {ram_available_bytes:number;vram_available_bytes:number|null;vram_total_bytes:number|null};
}
export interface ModelManagerStatus extends ModelInspection { reason: string; checkedAt: number; }

/** Candidates must be installed, capable, within the estimated budget AND configured. */
export function chooseModel(inspection:ModelInspection, configured:string[], mode:RoutingMode,
  effective:string|null, selected:string|null, images:boolean):{id:string;reason:string} {
  const kind=images?'vision':mode==='coding'?'coding':mode==='reasoning'?'reasoning':mode==='vision'?'vision':inspection.kind;
  const eligible=(inspection.rankings[kind]??[]).filter(name=>configured.includes(`ollama/${name}`));
  if(mode==='manual') {
    const id=selected??effective;
    if(!id||!eligible.some(name=>`ollama/${name}`===id))throw new Error('El modelo manual no está instalado, no admite esta tarea o no cabe en el presupuesto estimado.');
    return {id,reason:`Selección manual · ${kind}`};
  }
  if(['fast','voice','economy'].includes(mode))eligible.sort((a,b)=>(inspection.catalog.find(m=>m.name===a)?.size??Infinity)-(inspection.catalog.find(m=>m.name===b)?.size??Infinity));
  if(!eligible.length)throw new Error('No hay un modelo instalado y configurado compatible con esta tarea y la memoria disponible. No se descargó ningún modelo.');
  return {id:`ollama/${eligible[0]}`,reason:`${kind} · ${mode} · instalado y compatible · presupuesto estimado`};
}
