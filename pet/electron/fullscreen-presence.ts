/** Hide only our visible pet, then restore only what this controller hid. */
export class FullscreenPresence {
  private generation=0;
  private hidden=false;
  private leaving=false;
  private fullscreen=false;
  constructor(private pet:{visible:()=>boolean;leave:()=>Promise<void>;hide:()=>void;show:()=>void;reset:()=>void},private blocked:()=>boolean){}
  async update(fullscreen:boolean|null,enabled:boolean){
    if(fullscreen===null&&enabled)return;
    const desired=enabled&&fullscreen===true;
    if(desired===this.fullscreen){
      if(!desired&&this.hidden&&!this.blocked()){this.hidden=false;this.pet.show();}
      if(!desired||this.hidden||this.leaving||this.blocked()||!this.pet.visible())return;
    }
    if(desired&&this.blocked())return;
    this.fullscreen=desired;const generation=++this.generation;
    if(desired){
      if(this.blocked()||!this.pet.visible())return;
      this.leaving=true;
      await this.pet.leave();
      if(generation!==this.generation)return;
      this.leaving=false;this.pet.reset();this.pet.hide();this.hidden=true;
    }else{
      if(this.leaving){this.leaving=false;this.pet.reset();}
      if(this.hidden&&!this.blocked()){this.hidden=false;this.pet.show();}
    }
  }
  userHide(){this.generation++;this.hidden=false;this.leaving=false;this.pet.reset();}
  dispose(){this.userHide();}
}
