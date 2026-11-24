import type {
  DesktopBridge,
  DesktopEvent,
  Snapshot,
  Settings,
  ModelSelection,
} from "../shared/types";
export function serverBridge(): DesktopBridge {
  const request = async <T>(path: string, body?: unknown): Promise<T> => {
    const response = await fetch(`/api/${path}`, {
      method: body === undefined ? "GET" : "POST",
      credentials: "same-origin",
      headers:
        body === undefined
          ? {}
          : { "Content-Type": "application/json", "X-Karen-Client": "browser" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const result = await response.json();
    if (!response.ok)
      throw new Error(
        typeof result.error === "string"
          ? result.error
          : "El servidor no pudo completar la operación.",
      );
    return result as T;
  };
  const unsupported = async () => {
    throw new Error(
      "Esta función requiere la aplicación de Windows o un adaptador de voz externo.",
    );
  };
  return {
    snapshot: () => request<Snapshot>("snapshot"),
    settings: (patch) => request<Settings>("settings", { patch }),
    credential: unsupported,
    connect: () => request<void>("connect", {}),
    models: () => request<ModelSelection>('models', {}),
    selectModel: model => request<ModelSelection>('select-model', {model}),
    disconnect: () => request<void>("disconnect", {}),
    send: (text, images) => images?.length ? unsupported() : request<void>("send", { text }),
    abort: () => request<void>("abort", {}),
    openSettings: async () => {
      location.search = "?view=settings";
    },
    hide: unsupported,
    show: async () => {
      location.search = "?view=pet";
    },
    contextMenu: unsupported,
    hitTest: () => {},
    drag: () => {},
    synthesize: unsupported,
    transcribe: unsupported,
    voiceHealth: async () =>
      "Modo servidor: sin motores TTS/STT configurados. El cliente Windows incluye voz de sistema.",
    demo: (state) => request<void>("demo", { state }),
    energy: () => {},
    listen: unsupported,
    testVoice: unsupported,
    chooseVoiceRoot: unsupported,
    captureSources: unsupported,
    captureScreen: unsupported,
    pointAt: unsupported,
    locateOnScreen: unsupported,
    approveScreenAction: unsupported,
    cancelScreenAction: unsupported,
    stopPointing: unsupported,
    systemAudio: unsupported,
    captureStatus: () => {},
    event: (callback) => {
      const events = new EventSource("/api/events");
      events.onmessage = (message) => {
        try {
          callback(JSON.parse(message.data) as DesktopEvent);
        } catch {
          /* Malformed frames are ignored. */
        }
      };
      events.onerror = () =>
        callback({
          type: "connection",
          info: {
            state: "disconnected",
            message:
              "Canal con el servidor interrumpido. Recarga e inicia sesión si caducó el acceso.",
          },
        });
      events.onopen = () => {
        void request<Snapshot>("snapshot")
          .then((snapshot) => {
            callback({ type: "connection", info: snapshot.connection });
            for (const message of snapshot.messages)
              callback({ type: "chat", message, final: false });
          })
          .catch(() => {});
      };
      return () => events.close();
    },
  };
}
