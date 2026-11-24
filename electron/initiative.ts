import {readFileSync,writeFileSync,renameSync,existsSync} from 'node:fs';
import {join} from 'node:path';
import {randomUUID} from 'node:crypto';
import type {Settings} from '../shared/types.js';
import type {InitiativeAction,InitiativeSnapshot,InitiativeNotice} from '../shared/initiative.js';
import {freshInitiativeJournal,initiativeSnapshot,proposeInitiative,type InitiativeJournal,type InitiativeContext} from '../shared/initiative-policy.js';

/** One owner in Electron main. Journal contains generated notices, never source text or secrets. */
export class InitiativeService {
  private journal: InitiativeJournal = freshInitiativeJournal();
  private file: string;
  constructor(directory: string, private publish: (state: InitiativeSnapshot, notice?: InitiativeNotice) => void) {
    this.file=join(directory,'initiative.json');
    if (existsSync(this.file)) {
      const j=JSON.parse(readFileSync(this.file,'utf8')) as InitiativeJournal;
      if (j.version!==1 || !Array.isArray(j.notices) || j.notices.length>30 || !Array.isArray(j.seenTasks) || j.seenTasks.length>80 ||
        !['lastAt','snoozedUntil','count','sequence'].every(k=>Number.isSafeInteger(j[k as keyof InitiativeJournal]) && Number(j[k as keyof InitiativeJournal])>=0) ||
        !['day','greetingDay'].every(k=>typeof j[k as keyof InitiativeJournal]==='string') ||
        j.seenTasks.some(k=>typeof k!=='string'||k.length>160) ||
        j.notices.some(n=>!n || typeof n.id!=='string'||n.id.length>64 || !['greeting','check-in','connection','task'].includes(n.kind) ||
          !Number.isSafeInteger(n.at)||n.at<0 || typeof n.text!=='string'||n.text.length>500||typeof n.reason!=='string'||n.reason.length>200||typeof n.dismissed!=='boolean'||
          (n.command!==undefined && !/^\/tareas estado [0-9a-f]{32}$/.test(n.command))))
        throw new Error('Diario de iniciativa incompatible. Se conserva para recuperación.');
      this.journal=j;
    }
  }
  snapshot(now=Date.now()) {return initiativeSnapshot(this.journal,now);}
  expire(now=Date.now()) {
    for(const notice of this.journal.notices)
      if(!notice.dismissed && now-notice.at>=120000)this.act('dismiss',notice.id,now);
  }
  private save() {
    writeFileSync(this.file+'.tmp',JSON.stringify(this.journal,null,2),{mode:0o600});
    renameSync(this.file+'.tmp',this.file);
  }
  tick(settings: Settings, context: InitiativeContext, explicit=false): InitiativeNotice | null {
    const proposal=proposeInitiative(settings,this.journal,context,explicit);
    if (!proposal) return null;
    const next=structuredClone(this.journal);
    if(next.day!==context.day){next.day=context.day;next.count=0;}
    next.count++;next.lastAt=context.now;next.sequence++;
    if(proposal.kind==='greeting')next.greetingDay=context.day;
    if(proposal.taskKey) next.seenTasks=[...next.seenTasks,proposal.taskKey].slice(-80);
    const notice:InitiativeNotice={id:randomUUID(),at:context.now,kind:proposal.kind,text:proposal.text,reason:proposal.reason,
      ...(proposal.command?{command:proposal.command}:{}),dismissed:false};
    next.notices=[...next.notices.map(n=>({...n,dismissed:true})),notice].slice(-30);
    const previous=this.journal;
    this.journal=next;
    try{this.save();}catch(e){this.journal=previous;throw e;}
    this.publish(this.snapshot(context.now),notice);
    return notice;
  }
  act(action: Exclude<InitiativeAction,'now'>, id?: string, now=Date.now()) {
    const previous=structuredClone(this.journal);
    if(action==='snooze'){
      this.journal.snoozedUntil=now+3600000;
      this.journal.notices=this.journal.notices.map(n=>({...n,dismissed:true}));
    }else if(action==='resume')this.journal.snoozedUntil=0;
    else if(action==='dismiss'){
      if(!id || !this.journal.notices.some(n=>n.id===id))throw new Error('Aviso desconocido.');
      this.journal.notices=this.journal.notices.map(n=>n.id===id?{...n,dismissed:true}:n);
    }else throw new Error('Acción de iniciativa inválida.');
    try{this.save();}catch(e){this.journal=previous;throw e;}
    this.publish(this.snapshot(now));
    return this.snapshot(now);
  }
}
