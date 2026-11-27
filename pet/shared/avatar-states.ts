import type { PetState } from './types.js';

export interface VisualState {
  label: string; face: PetState; priority: number; duration: number;
  tilt: number; eyes: number; scan: number; wave: number; lift: number;
}
const state = (label: string, face: PetState, priority: number, pose: Partial<VisualState> = {}): VisualState =>
  ({ label, face, priority, duration: 0, tilt: 0, eyes: 1, scan: 0, wave: 0, lift: 0, ...pose });

/** Provider-independent visual vocabulary; a label never authorizes a tool. */
export const AVATAR_STATES: Record<PetState, VisualState> = {
  IDLE: state('En calma','IDLE',0),
  LISTENING: state('Escuchando','LISTENING',100,{tilt:-.035,eyes:1.08}),
  THINKING: state('Pensando','THINKING',65,{tilt:.04,scan:2}),
  SPEAKING: state('Hablando','SPEAKING',95),
  HAPPY: state('Feliz','HAPPY',30,{duration:2400,lift:-2}),
  LAUGHING: state('Riendo','LAUGHING',32,{duration:3000,lift:-3}),
  ANGRY: state('Molesta','ANGRY',35,{duration:3500,tilt:.025}),
  SAD: state('Triste','SAD',30,{duration:4000,eyes:.8}),
  SURPRISED: state('Sorprendida','SURPRISED',35,{duration:2300,eyes:1.12}),
  PROUD: state('Orgullosa','PROUD',30,{duration:3200,tilt:-.03,lift:-2}),
  CURIOUS: state('Curiosa','CURIOUS',30,{duration:3500,tilt:-.06,scan:4}),
  CONFUSED: state('Con duda','CONFUSED',32,{duration:4000,tilt:-.07}),
  ERROR: state('Algo ocurrió','ERROR',110,{duration:5000}),
  SLEEPING: state('Descansando','SLEEPING',50,{eyes:.1}),
  DRAGGING: state('En tus manos','DRAGGING',120),
  WORKING: state('Trabajando','THINKING',62,{tilt:.025,scan:1.5}),
  SEARCHING: state('Buscando','CURIOUS',62,{scan:8,tilt:-.025}),
  READING: state('Leyendo','IDLE',60,{eyes:.86,scan:5,tilt:.025}),
  WRITING: state('Escribiendo','THINKING',62,{eyes:.9,scan:2.5,tilt:.045}),
  CODING: state('Programando','THINKING',64,{eyes:.85,scan:3.5,tilt:-.04}),
  OBSERVING: state('Observando','CURIOUS',42,{eyes:1.1,scan:6}),
  CONCERNED: state('Con atención','CONFUSED',34,{duration:4000,eyes:.88,tilt:.055}),
  BORED: state('Un momento de calma','IDLE',8,{duration:6000,eyes:.62,tilt:.06}),
  SLEEPY: state('Con sueño','SAD',12,{duration:6500,eyes:.45,tilt:-.045}),
  EXCITED: state('Entusiasmada','HAPPY',36,{duration:3000,eyes:1.08,lift:-5,wave:.06}),
  MUSIC_LISTENING: state('Escuchando música','IDLE',10,{eyes:.92,wave:.035}),
  GREETING: state('Hola','HAPPY',38,{duration:2400,lift:-3,wave:.09}),
  GOODBYE: state('Hasta pronto','HAPPY',130,{duration:1000,tilt:-.05,wave:.1}),
  INTERRUPTED: state('Te escucho','SURPRISED',105,{duration:700,eyes:1.06}),
  FOCUSED: state('Concentrada','IDLE',25,{eyes:.8,tilt:.025,scan:1}),
};

/** Classify real tool metadata for display only; never classify arbitrary model prose. */
export function toolVisualState(name: unknown): PetState {
  if (typeof name !== 'string') return 'WORKING';
  const value = name.slice(0,128).toLowerCase();
  if (/search|buscar|fetch|browse/.test(value)) return 'SEARCHING';
  if (/code|compile|test|python|typescript/.test(value)) return 'CODING';
  if (/write|edit|crear|escribir|patch/.test(value)) return 'WRITING';
  if (/read|leer|memory|recall/.test(value)) return 'READING';
  if (/screen|vision|observe/.test(value)) return 'OBSERVING';
  return 'WORKING';
}
