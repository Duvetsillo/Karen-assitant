import {afterEach, describe, expect, it} from 'vitest';
import {useStore} from '../src/state/store';

const initial=useStore.getState();
afterEach(()=>useStore.setState(initial));

describe('wake diagnostics across Pet and Settings',()=>{
  it('keeps the specific failure instead of a generic voice error',()=>{
    useStore.getState().event({type:'wake-status',status:'error',error:'El micrófono elegido ya no está conectado.'});
    expect(useStore.getState().wakeError).toContain('micrófono elegido');
    expect(useStore.getState().wakeStatus).toBe('error');
  });
  it('clears its old failure after recovery',()=>{
    useStore.setState({error:'Microphone unavailable',wakeError:'Microphone unavailable',wakeStatus:'error'});
    useStore.getState().event({type:'wake-status',status:'listening'});
    expect(useStore.getState().wakeError).toBe('');
    expect(useStore.getState().error).toBe('');
  });
  it('does not erase an unrelated conversation failure',()=>{
    useStore.setState({error:'Gateway disconnected',wakeError:'Microphone unavailable'});
    useStore.getState().event({type:'wake-status',status:'paused'});
    expect(useStore.getState().error).toBe('Gateway disconnected');
    expect(useStore.getState().wakeError).toBe('');
  });
});
