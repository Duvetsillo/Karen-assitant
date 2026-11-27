import { useEffect, useState } from 'react';
import { bridge } from '../native';
import { report } from '../state/store';
import type { MusicSnapshot, MusicRequest } from '../../shared/music';

export const platformNames = {spotify:'Spotify',apple:'Apple Music','youtube-music':'YouTube Music',youtube:'YouTube · música confirmada',windows:'Reproductor de Windows'};
export const time = (seconds?: number) => seconds === undefined ? '—' : `${Math.floor(seconds/60)}:${String(Math.floor(seconds%60)).padStart(2,'0')}`;
export const act = async (request: MusicRequest) => {try{return await bridge.music?.action(request);}catch(error){report(error);}};
export function useMusic() {
  const [state,setState]=useState<MusicSnapshot>({enabled:false,status:'off',sessions:[]});
  useEffect(()=>{
    let alive=true;
    const off=bridge.event(event=>{if(alive&&event.type==='music')setState(event.snapshot);});
    void bridge.music?.snapshot().then(snapshot=>{if(alive)setState(snapshot);}).catch(report);
    return ()=>{alive=false;off();};
  },[]);
  return state;
}
