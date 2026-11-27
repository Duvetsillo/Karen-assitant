export interface EnvironmentSnapshot {
  fullscreen?:boolean|null;
  enabled:boolean; at:number; idleSeconds:number; onBattery:boolean;
  desktopProtected:boolean|null; category:'coding'|'browser'|'call'|'game'|'other'|'unknown';
}
export function interpretEnvironment(value:EnvironmentSnapshot|undefined,observe:boolean,adapt:boolean){
  const allowed=Boolean(observe&&adapt&&value?.enabled&&Date.now()-value.at<45000);
  return {quiet:allowed&&Boolean(value?.desktopProtected||value?.category==='call'||value?.category==='game'),
    focused:allowed&&value?.category==='coding'&&(value?.idleSeconds??Infinity)<90,
    conserve:allowed&&value?.onBattery===true};
}
