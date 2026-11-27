export const IDLE_CLIPS = {
  play:{label:'Jugar con una luz',duration:8500},stretch:{label:'Estirarse',duration:6500},stargaze:{label:'Mirar estrellas',duration:10000},
  drift:{label:'Flotar de un lado a otro',duration:8000},twirl:{label:'Dar una vuelta',duration:7000},peek:{label:'Mirar con curiosidad',duration:6500},
  shimmer:{label:'Seguir luciérnagas',duration:10000},meditate:{label:'Respirar en calma',duration:11000},yawn:{label:'Bostezar',duration:7000},
  wiggle:{label:'Bailar suavemente',duration:8500},orbit:{label:'Seguir una pequeña órbita',duration:9500},
} as const;
export type IdleClip=keyof typeof IDLE_CLIPS;
export function idlePose(kind:IdleClip|'none',progress:number){
  const p=Math.max(0,Math.min(1,progress)),e=Math.sin(Math.PI*p)**2,t=p*Math.PI*2;
  const pose={x:0,y:0,tilt:0,squash:0,eye:1,gazeX:0,gazeY:0,glow:0};
  switch(kind){
    case 'drift':pose.x=Math.sin(t)*e*22;pose.y=-e*9;pose.tilt=Math.sin(t)*e*.08;break;
    case 'twirl':pose.tilt=Math.sin(t)*e*.24;pose.squash=-e*.08;pose.y=-e*16;break;
    case 'peek':pose.gazeX=Math.sin(t*1.5)*e*12;pose.tilt=Math.sin(t*1.5)*e*.13;pose.eye=1+e*.16;break;
    case 'shimmer':pose.gazeX=Math.sin(t)*e*10;pose.gazeY=-e*9;pose.glow=e;break;
    case 'meditate':pose.eye=1-e*.8;pose.squash=Math.sin(t*2)*e*.025;pose.y=-e*11;pose.glow=e*.35;break;
    case 'yawn':pose.eye=1-e*.87;pose.squash=e*.06;pose.tilt=-e*.06;break;
    case 'wiggle':pose.tilt=Math.sin(t*3)*e*.12;pose.y=-Math.abs(Math.sin(t*3))*e*8;break;
    case 'orbit':pose.gazeX=Math.cos(t*1.5)*e*13;pose.gazeY=Math.sin(t*1.5)*e*9;pose.glow=e;pose.tilt=pose.gazeX*.005;break;
  }
  return pose;
}
