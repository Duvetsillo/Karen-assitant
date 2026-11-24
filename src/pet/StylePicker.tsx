import { useId } from 'react';
import { Check } from 'lucide-react';
import { PET_STYLES, type PetStyle } from '../../shared/types';
import { petStyles } from '../../shared/pet-styles';

function Portrait({ style, arms, legs }: { style: PetStyle; arms: boolean; legs: boolean }) {
  const id = useId();
  const cloud = style === 'cloud', orbit = style === 'orbit' || style === 'midnight', sprite = style === 'sprite', bloom = style === 'bloom';
  return <svg viewBox="0 0 150 120" aria-hidden="true" focusable="false">
    <defs><linearGradient id={id} x2=".8" y2="1"><stop stopColor={style === 'midnight' ? '#a3add6' : style === 'ember' ? '#fff1d2' : cloud || bloom ? '#fff0fc' : sprite ? '#fff9e8' : '#e0f8ff'}/><stop offset="1" stopColor={style === 'aurora' ? '#68b9b9' : style === 'ember' ? '#d59b7b' : style === 'midnight' ? '#3c4c78' : cloud ? '#b5a4cf' : orbit ? '#566e93' : bloom ? '#d5a9d6' : sprite ? '#80c9e4' : '#7dc4e7'}/></linearGradient></defs>
    <ellipse cx="75" cy="109" rx="35" ry="4" fill="#8be4f3" opacity=".12"/>
    <g visibility={legs ? 'visible' : 'hidden'} fill={`url(#${id})`} stroke="#e8faff" strokeWidth="1.5"><path d="M59 92l-4 13q-13 2-12 8h25l4-21m19 0 4 13q13 2 12 8H82l-4-21"/></g>
    {orbit ? <g fill="#c7ecf9" stroke="#93e4f4" strokeWidth="3"><path d="M52 40L48 19M98 40l4-21"/><circle cx="48" cy="17" r="6"/><circle cx="102" cy="17" r="6"/></g> : <g fill={`url(#${id})`} stroke="#e3e5ff" strokeWidth="1"><path d={cloud ? 'M53 45C22 40 28 7 42 17c12 8 16 16 11 28' : 'M53 44C30 32 51 24 33 7c28 6 34 26 20 37'}/><path d={cloud ? 'M97 45c31-5 25-38 11-28-12 8-16 16-11 28' : 'M97 44c23-12 2-20 20-37-28 6-34 26-20 37'}/></g>}
    <g fill={`url(#${id})`} stroke="#e3f6ff" strokeWidth="1.2">
      <path visibility={arms ? 'visible' : 'hidden'} d="M37 68c-28-8-25 20-7 18l13-8m70-10c28-8 25 20 7 18l-13-8"/>
      <path d={style === 'aurora' ? 'M75 28c18 13 46 27 44 52-1 22-18 31-44 31S32 102 31 80c-2-25 26-39 44-52Z' : style === 'ember' ? 'M75 32c29 1 45 21 43 45-1 17-18 24-43 35-25-11-42-18-43-35-2-24 14-44 43-45Z' : bloom ? 'M75 29c8-16 22-12 25 5 20-10 32 2 24 20 19 8 18 25 1 33 7 20-8 28-24 20-12 16-26 13-35 0-21 8-32-1-26-20-21-11-19-25-2-34-6-17 8-28 24-19 4-5 8-7 13-5Z' : sprite ? 'M75 28c32 0 45 20 45 46s-14 35-45 35-45-10-45-35 13-46 45-46Z' : cloud ? 'M75 36c15-13 35-2 34 12 22 3 23 26 11 34 7 22-13 30-28 23-9 12-27 11-35 0-24 8-35-8-29-24-16-13-6-32 10-33 3-16 22-22 37-12Z' : orbit ? 'M75 34c34 0 47 18 44 42-1 21-13 29-44 29s-43-8-44-29c-3-24 10-42 44-42Z' : 'M75 33c38-3 54 23 43 49-8 15-6 27-21 23-14-9-14 12-28 1-13-11-20 10-29-6-2-12-15-16-11-35 4-23 22-32 46-32Z'}/>
    </g>
    <g visibility={arms ? 'visible' : 'hidden'} fill="#d8f7ff" stroke="#f7ffff" strokeWidth="1"><circle cx="27" cy="83" r="8"/><circle cx="123" cy="83" r="8"/></g>
    <rect x="40" y="55" width="70" height="35" rx="16" fill="#1b304b" stroke="#c4efff" strokeOpacity=".7"/>
    <g fill="#bcf6ff"><ellipse cx="59" cy="71" rx="8" ry="11"/><ellipse cx="91" cy="71" rx="8" ry="11"/></g>
    <g fill="#2b4d79"><ellipse cx="60" cy="72" rx="4" ry="6"/><ellipse cx="90" cy="72" rx="4" ry="6"/></g>
    <g fill="white"><ellipse cx="57" cy="67" rx="2" ry="3"/><ellipse cx="87" cy="67" rx="2" ry="3"/></g>
    <path d="M70 82q5 4 10 0" fill="none" stroke="#dcfaff" strokeWidth="2" strokeLinecap="round"/>
    {orbit && <path d="M66 98h18" stroke="#b5efff" strokeWidth="3" strokeDasharray="4 3"/>}
  </svg>;
}
export function StylePicker({ value, onChange, arms = true, legs = true }: { value: PetStyle; onChange: (style: PetStyle) => void; arms?: boolean; legs?: boolean }) {
  return <fieldset className="pet-styles"><legend className="sr-only">Estilo de Karen</legend>
    {PET_STYLES.map(style => <label className={`pet-style-card ${value === style ? 'selected' : ''}`} key={style}>
      <input type="radio" name="pet-style" value={style} checked={value === style} onChange={() => onChange(style)}/>
      <Portrait style={style} arms={arms} legs={legs}/><span className="pet-style-name">{petStyles[style].name}{value === style && <Check size={14} aria-hidden="true"/>}</span><small>{petStyles[style].description}</small>
    </label>)}
  </fieldset>;
}
