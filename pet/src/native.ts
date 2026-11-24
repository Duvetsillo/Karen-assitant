import type { DesktopBridge, Snapshot } from "../shared/types";
import { defaults } from "../shared/settings";
import { serverBridge } from "./server-bridge";
import { APP_VERSION } from "../shared/version";
declare global {
  interface Window {
    karen?: DesktopBridge;
  }
}
const unavailable = async () => {
  throw new Error("Esta función necesita la aplicación de Windows.");
};
let previewSettings = { ...defaults };
const preview: DesktopBridge = {
  snapshot: async (): Promise<Snapshot> => ({
    settings: { ...previewSettings },
    connection: {
      state: "disconnected",
      message: "Vista de navegador · sin conexión nativa",
    },
    diagnostics: [],
    messages: [],
    hasCredential: false,
    native: false,
    version: APP_VERSION,
  }),
  settings: async (patch) => {
    previewSettings = { ...previewSettings, ...patch };
    return { ...previewSettings };
  },
  credential: unavailable,
  connect: unavailable,
  models: unavailable,
  selectModel: unavailable,
  disconnect: unavailable,
  send: unavailable,
  abort: unavailable,
  openSettings: async () => {
    location.search = "?view=settings";
  },
  hide: unavailable,
  show: unavailable,
  contextMenu: unavailable,
  hitTest: () => {},
  drag: () => {},
  synthesize: unavailable,
  transcribe: unavailable,
  voiceHealth: async () => "Diagnóstico disponible en Windows.",
  event: () => () => {},
  demo: async () => {},
  energy: () => {},
  listen: unavailable,
  testVoice: unavailable,
  chooseVoiceRoot: unavailable,
  captureSources: unavailable,
  captureScreen: unavailable,
  pointAt: unavailable,
  locateOnScreen: unavailable,
  approveScreenAction: unavailable,
  cancelScreenAction: unavailable,
  stopPointing: unavailable,
  systemAudio: unavailable,
  captureStatus: () => {},
};
export const bridge =
  window.karen ??
  (document
    .querySelector('meta[name="karen-runtime"]')
    ?.getAttribute("content") === "server"
    ? serverBridge()
    : preview);
