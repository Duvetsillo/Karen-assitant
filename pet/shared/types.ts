import type { IntroPreferences } from './startup-intros.js';
import type { MusicPreferences } from './music.js';
export const PET_STATES = [
  "IDLE",
  "LISTENING",
  "THINKING",
  "SPEAKING",
  "HAPPY",
  "LAUGHING",
  "ANGRY",
  "SAD",
  "SURPRISED",
  "PROUD",
  "CURIOUS",
  "CONFUSED",
  "ERROR",
  "SLEEPING",
  "DRAGGING",
] as const;
export type PetState = (typeof PET_STATES)[number];
export const PET_STYLES = ['crystal', 'cloud', 'orbit', 'sprite', 'bloom', 'aurora', 'ember', 'midnight'] as const;
export type PetStyle = (typeof PET_STYLES)[number];
export interface ModelOption {
  id: string;
  name: string;
  provider: string;
  available: boolean;
}
export interface ModelSelection {
  busy: boolean;
  sessionKey: string;
  selected: string | null;
  effective: string | null;
  models: ModelOption[];
}
export const VOICE_STYLES = ['neutral', 'serene', 'warm', 'serious', 'bright', 'wry'] as const;
export type VoiceStyle = (typeof VOICE_STYLES)[number];
export type WakeStatus = 'off' | 'listening' | 'processing' | 'recovering' | 'paused' | 'error';
export type ConnectionState =
  | "disconnected"
  | "connecting"
  | "connected"
  | "reconnecting"
  | "action-required";
export interface Settings extends IntroPreferences, MusicPreferences {
  initiativeEnabled: boolean;
  initiativeSpeak: boolean;
  initiativeInterval: number;
  initiativeDailyLimit: number;
  initiativeQuietStart: number;
  initiativeQuietEnd: number;
  petStyle: PetStyle;
  showArms: boolean;
  showLegs: boolean;
  idleActivities: boolean;
  idleActivity: 'variety' | 'play' | 'stretch' | 'stargaze';
  idleAfter: number;
  scale: number;
  brightness: number;
  opacity: number;
  particles: boolean;
  accent: string;
  animations: boolean;
  cursorTracking: boolean;
  sleepAfter: number;
  activity: number;
  gatewayUrl: string;
  agentId: string;
  authSource: "local" | "stored";
  bubbles: boolean;
  petChatShape: "bubble" | "panel" | "ribbon";
  voiceEnabled: boolean;
  ttsEngine: "system" | "local" | "fast" | "edge";
  voiceStyle: VoiceStyle;
  wakeWordEnabled: boolean;
  inputDevice: string;
  outputDevice: string;
  volume: number;
  sensitivity: number;
  sttEnabled: boolean;
  voiceRoot: string;
  alwaysOnTop: boolean;
  autoStart: boolean;
  lowPower: boolean;
  nightMode: boolean;
  mode: "normal" | "gaming" | "do_not_disturb";
}
export interface Diagnostic {
  time: number;
  level: "info" | "warn" | "error";
  area: string;
  message: string;
}
export interface ConnectionInfo {
  state: ConnectionState;
  message: string;
  version?: string;
  nextRetryMs?: number;
  scopes?: string[];
}
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  pending?: boolean;
}
export interface ImageAttachment {
  type: "image";
  mimeType: "image/jpeg" | "image/png";
  fileName: string;
  content: string;
}
export interface CaptureSource { id: string; name: string; canPoint?: boolean; }
export interface ScreenActionProposal {
  id: string;
  kind: 'click' | 'type';
  target: string;
  text?: string;
  x: number;
  y: number;
  expiresAt: number;
}
export interface CaptureStatus {
  kind: "microphone" | "system" | "voice";
  phase: "idle" | "recording" | "transcribing" | "preparing" | "speaking";
  startedAt?: number;
}
export type DesktopEvent =
  | { type: 'pet-departure'; token: string }
  | { type: 'intro-landing'; token: string | null }
  | { type: 'music'; snapshot: import('./music.js').MusicSnapshot }
  | { type: 'initiative'; snapshot: import('./initiative.js').InitiativeSnapshot; notice?: import('./initiative.js').InitiativeNotice }
  | { type: 'surface-visibility'; visible: boolean }
  | { type: 'core-activity'; clients: { interface: string; state: string }[] }
  | { type: 'screen-action-proposal'; proposal: ScreenActionProposal | null }
  | { type: 'models'; selection: ModelSelection }
  | { type: 'wake-status'; status: WakeStatus; error?: string }
  | { type: "connection"; info: ConnectionInfo }
  | { type: "pet"; state: PetState; reason?: string }
  | { type: "chat"; message: ChatMessage; final: boolean; speak?: boolean }
  | { type: "diagnostic"; item: Diagnostic }
  | { type: "settings"; settings: Settings }
  | { type: "cursor"; x: number; y: number }
  | { type: "pointing"; side: -1 | 0 | 1 }
  | { type: "voice-cancel" }
  | { type: "voice-listen" }
  | { type: "voice-speak"; text: string }
  | { type: "capture"; status: CaptureStatus }
  | { type: "transcript"; text: string }
  | { type: "error"; message: string }
  | { type: "energy"; value: number }
  | { type: "wake" };
export interface Snapshot {
  music?: import('./music.js').MusicSnapshot;
  initiative?: import('./initiative.js').InitiativeSnapshot;
  settings: Settings;
  connection: ConnectionInfo;
  diagnostics: Diagnostic[];
  messages: ChatMessage[];
  hasCredential: boolean;
  native: boolean;
  runtime?: "desktop" | "server" | "preview";
  version: string;
  capture?: CaptureStatus;
  wakeStatus?: WakeStatus;
  wakeError?: string;
}
export interface DesktopBridge {
  departureComplete?(token: string): Promise<void>;
  introPetRendered?(token: string): Promise<void>;
  music?: import('./music.js').MusicBridge;
  playIntro?(id?: import('./startup-intros.js').IntroId): Promise<boolean>;
  introGreetingStatus?(): Promise<{ available: boolean; message: string }>;
  introMonitors?(): Promise<{ id: string; name: string }[]>;
  interaction?(): void;
  initiative?(action: import('./initiative.js').InitiativeAction, id?: string): Promise<import('./initiative.js').InitiativeSnapshot>;
  claimMicrophone?(): Promise<string>;
  releaseMicrophone?(token: string): Promise<void>;
  models(): Promise<ModelSelection>;
  selectModel(model: string | null): Promise<ModelSelection>;
  snapshot(): Promise<Snapshot>;
  settings(patch: Partial<Settings>): Promise<Settings>;
  credential(value: string): Promise<void>;
  connect(): Promise<void>;
  disconnect(): Promise<void>;
  send(text: string, images?: ImageAttachment[]): Promise<void>;
  abort(): Promise<void>;
  copyText?(text: string): Promise<void>;
  openSettings(): Promise<void>;
  hide(): Promise<void>;
  show(): Promise<void>;
  contextMenu(): Promise<void>;
  hitTest(interactive: boolean): void;
  drag(action: "start" | "end"): void;
  synthesize(text: string): Promise<ArrayBuffer>;
  cancelSynthesis?(): Promise<void>;
  prepareVoice?(): Promise<void>;
  voiceHealth(): Promise<string>;
  transcribe(pcm: ArrayBuffer): Promise<string>;
  cancelTranscription?(): Promise<void>;
  demo(state: PetState): Promise<void>;
  energy(value: number): void;
  listen(): Promise<void>;
  testVoice(): Promise<void>;
  chooseVoiceRoot(): Promise<string | null>;
  captureSources(): Promise<CaptureSource[]>;
  captureScreen(id: string): Promise<ImageAttachment>;
  pointAt(id: string, x: number, y: number): Promise<void>;
  locateOnScreen(id: string, description: string, image: ImageAttachment): Promise<void>;
  approveScreenAction(id: string): Promise<void>;
  cancelScreenAction(id: string): Promise<void>;
  stopPointing(): Promise<void>;
  systemAudio(action: "start" | "finish"): Promise<void>;
  captureStatus(status: CaptureStatus): void;
  wakeStatus?(status: WakeStatus, error?: string): void;
  event(callback: (event: DesktopEvent) => void): () => void;
}
