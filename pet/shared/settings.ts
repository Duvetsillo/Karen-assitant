import type { Settings } from "./types.js";
import { introDefaults, INTRO_IDS } from './startup-intros.js';
import { musicDefaults, MUSIC_PLATFORMS } from './music.js';
import { PET_STYLES, VOICE_STYLES } from './types.js';
import { PET_SCALE } from "./pet-layout.js";
import { ROUTING_MODES, RESOURCE_PROFILES } from './models.js';
import { IDLE_CLIPS } from './idle-clips.js';
export const defaults: Settings = {
  fullscreenHide:true,
  conversationScope:'shared',
  environmentObserve:false,
  environmentAdapt:false,
  routingMode: 'auto',
  resourceProfile: 'balanced',
  ...introDefaults,
  ...musicDefaults,
  initiativeEnabled: false,
  initiativeSpeak: false,
  initiativeInterval: 45,
  initiativeDailyLimit: 4,
  initiativeQuietStart: 22,
  initiativeQuietEnd: 9,
  petStyle: 'crystal',
  showArms: false,
  showLegs: false,
  idleActivities: true,
  idleActivity: 'variety',
  idleAfter: 30,
  scale: 1,
  brightness: 1,
  opacity: 0.94,
  particles: true,
  accent: "#8be4f3",
  animations: true,
  cursorTracking: true,
  sleepAfter: 0,
  activity: 0.6,
  gatewayUrl: "ws://127.0.0.1:18789",
  agentId: "main",
  authSource: "local",
  bubbles: true,
  petChatShape: "bubble",
  voiceEnabled: false,
  ttsEngine: "system",
  voiceStyle: 'serene',
  wakeWordEnabled: false,
  inputDevice: "",
  outputDevice: "",
  volume: 0.8,
  sensitivity: 1.5,
  sttEnabled: false,
  voiceRoot: "",
  alwaysOnTop: true,
  autoStart: false,
  lowPower: false,
  nightMode: false,
  mode: 'normal',
};
/** Temporary runtime profile: underlying user preferences stay intact. */
export function effectiveSettings(settings: Settings): Settings {
  if (settings.showArms || settings.showLegs) settings = {...settings,showArms:false,showLegs:false};
  // Keep the saved preference, but never send voice text to cloud in Core 2.
  if (settings.ttsEngine === 'edge') settings = {...settings, ttsEngine: 'local'};
  if (!settings.mode || settings.mode === 'normal') return settings;
  const quiet = {
    ...settings, lowPower: true, particles: false, animations: false,
    cursorTracking: false, bubbles: false, alwaysOnTop: false,
  };
  return settings.mode === 'gaming' ? quiet : {
    ...quiet, voiceEnabled: false, wakeWordEnabled: false,
  };
}
export function gatewayAddress(value: string): string {
  const url = new URL(value);
  if (
    !["ws:", "wss:"].includes(url.protocol) ||
    url.username ||
    url.password ||
    url.search ||
    url.hash
  )
    throw new Error(
      "Usa una dirección ws:// o wss:// sin credenciales ni parámetros.",
    );
  if (
    url.protocol === "ws:" &&
    !["127.0.0.1", "localhost", "[::1]"].includes(url.hostname)
  )
    throw new Error("Los gateways remotos requieren wss://.");
  return url.toString();
}
export function validateSettings(
  raw: Partial<Settings>,
  current: Settings = defaults,
): Settings {
  const s = { ...current };
  if (raw.musicPlatforms !== undefined) {
    if (!Array.isArray(raw.musicPlatforms) || raw.musicPlatforms.some(p => !MUSIC_PLATFORMS.includes(p))) throw new Error('Plataforma musical inválida.');
    s.musicPlatforms = [...new Set(raw.musicPlatforms)];
  }
  if (raw.introFrequency !== undefined) {
    if (!['startup','daily','after-away','manual'].includes(raw.introFrequency)) throw new Error('Frecuencia de saludo inválida.');
    s.introFrequency = raw.introFrequency;
  }
  if (raw.introSelection !== undefined) {
    if (!['random', 'fixed', 'contextual'].includes(raw.introSelection)) throw new Error('Selección de introducción inválida.');
    s.introSelection = raw.introSelection;
  }
  if (raw.introFixed !== undefined) {
    if (!INTRO_IDS.includes(raw.introFixed)) throw new Error('Introducción desconocida.');
    s.introFixed = raw.introFixed;
  }
  if (raw.introFPS !== undefined) {
    if (![30, 60].includes(raw.introFPS)) throw new Error('Frecuencia de introducción inválida.');
    s.introFPS = raw.introFPS;
  }
  if (raw.introMonitor !== undefined) {
    if (typeof raw.introMonitor !== 'string' || !/^(?:-?\d{1,16})?$/.test(raw.introMonitor)) throw new Error('Monitor inválido.');
    s.introMonitor = raw.introMonitor;
  }
  if (raw.mode !== undefined) {
    if (!['normal', 'gaming', 'do_not_disturb'].includes(raw.mode))
      throw new Error('Modo desconocido.');
    s.mode = raw.mode;
  }
  if(raw.routingMode!==undefined){
    if(!ROUTING_MODES.includes(raw.routingMode))throw new Error('Ruta de modelos desconocida.');
    s.routingMode=raw.routingMode;
  }
  if(raw.conversationScope!==undefined){
    if(!['shared','desktop'].includes(raw.conversationScope))throw new Error('Conversación desconocida.');
    s.conversationScope=raw.conversationScope;
  }
  if(raw.resourceProfile!==undefined){
    if(!RESOURCE_PROFILES.includes(raw.resourceProfile))throw new Error('Perfil de recursos desconocido.');
    s.resourceProfile=raw.resourceProfile;
  }
  if (raw.petStyle !== undefined) {
    if (!PET_STYLES.includes(raw.petStyle)) throw new Error('Apariencia desconocida.');
    s.petStyle = raw.petStyle;
  }
  if (raw.idleActivity !== undefined) {
    if (raw.idleActivity!=='variety'&&!Object.hasOwn(IDLE_CLIPS,raw.idleActivity))
      throw new Error('Actividad de reposo desconocida.');
    s.idleActivity = raw.idleActivity;
  }
  for (const key of [
    'fullscreenHide',
    'environmentObserve','environmentAdapt',
    'musicAutoShow','musicHoverExpand','musicAmbientColors','musicEnabled', 'musicPlayer', 'musicPlayerPinned', 'musicStrictYouTube', 'musicComments', 'musicAnimations', 'musicGamingReactions', 'musicHistory', 'musicObsidian',
    'introEnabled', 'introVoice', 'introSounds', 'introReducedMotion', 'introEscape', 'farewellEnabled',
    "particles",
    "initiativeEnabled",
    "initiativeSpeak",
    "showArms",
    "showLegs",
    "idleActivities",
    "animations",
    "cursorTracking",
    "bubbles",
    "voiceEnabled",
    "sttEnabled",
    "wakeWordEnabled",
    "alwaysOnTop",
    "autoStart",
    "lowPower",
    "nightMode",
  ] as const) {
    if (raw[key] !== undefined) {
      if (typeof raw[key] !== "boolean")
        throw new Error("Ajuste booleano inválido.");
      s[key] = raw[key];
    }
  }
  const ranges = {
    musicCommentProbability: [0, 1], musicCommentVolume: [0, 1], musicCooldownMinutes: [1, 240], musicMaxComments: [1, 10],
    introVolume: [0, 1],
    initiativeInterval: [15, 240],
    initiativeDailyLimit: [1, 12],
    initiativeQuietStart: [0, 23],
    initiativeQuietEnd: [0, 23],
    scale: [PET_SCALE.min, PET_SCALE.max],
    musicAutoHideSeconds: [0,300],
    brightness: [0.35, 1.4],
    opacity: [0.35, 1],
    sleepAfter: [30, 3600],
    activity: [0, 1],
    idleAfter: [15, 300],
    volume: [0, 1],
    sensitivity: [0.2, 5],
  } as const;
  for (const key of Object.keys(ranges) as (keyof typeof ranges)[]) {
    const n = raw[key];
    if (n !== undefined) {
      if (!Number.isFinite(n)) throw new Error("Número inválido.");
      if(key==='sleepAfter'&&n===0){s.sleepAfter=0;continue;}
      const value = Math.min(ranges[key][1], Math.max(ranges[key][0], n));
      s[key] = key.startsWith('initiative') || key === 'musicMaxComments' ? Math.round(value) : value;
    }
  }
  if (raw.gatewayUrl !== undefined)
    s.gatewayUrl = gatewayAddress(raw.gatewayUrl);
  if (raw.agentId !== undefined) {
    if (!/^[a-zA-Z0-9_-]{1,64}$/.test(raw.agentId))
      throw new Error("Identificador de agente inválido.");
    s.agentId = raw.agentId;
  }
  if (raw.accent !== undefined) {
    if (!/^#[\da-f]{6}$/i.test(raw.accent)) throw new Error("Color inválido.");
    s.accent = raw.accent;
  }
  for (const key of ["inputDevice", "outputDevice"] as const)
    if (typeof raw[key] === "string") s[key] = raw[key].slice(0, 256);
  if (raw.voiceRoot !== undefined) {
    if (typeof raw.voiceRoot !== "string" || raw.voiceRoot.length > 2048 || raw.voiceRoot.includes("\0")) throw new Error("Directorio de voz inválido.");
    s.voiceRoot = raw.voiceRoot;
  }
  if (raw.authSource === "local" || raw.authSource === "stored")
    s.authSource = raw.authSource;
  if (raw.ttsEngine === "system" || raw.ttsEngine === "local" || raw.ttsEngine === 'fast' || raw.ttsEngine === 'edge')
    s.ttsEngine = raw.ttsEngine;
  if (raw.voiceStyle !== undefined) {
    if (!VOICE_STYLES.includes(raw.voiceStyle)) throw new Error('Estilo de voz desconocido.');
    s.voiceStyle = raw.voiceStyle;
  }
  if (raw.petChatShape !== undefined) {
    if (!['bubble','panel','ribbon'].includes(raw.petChatShape)) throw new Error('Forma de chat desconocida.');
    s.petChatShape = raw.petChatShape;
  }
  // Retain legacy keys for profile compatibility; the character is always floating.
  s.showArms = false; s.showLegs = false;
  return s;
}
