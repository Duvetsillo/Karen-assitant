import { describe, it, expect } from "vitest";
import { validateSettings, defaults, gatewayAddress, effectiveSettings } from "../shared/settings";
import { PetMachine } from "../src/state/machine";
import { expressionForReply } from '../shared/expression';
import { APP_VERSION } from '../shared/version';
import packageInfo from '../package.json';
import {
  extractText,
  routeGatewayEvent,
  nextChatText,
  mergeMessages,
} from "../shared/protocol";
describe("configuración", () => {
  it('Gaming y No molestar aplican overrides temporales sin borrar preferencias', () => {
    const base = validateSettings({voiceEnabled: true, wakeWordEnabled: true,
      animations: true, particles: true, bubbles: true, alwaysOnTop: true});
    const gaming = effectiveSettings({...base, mode: 'gaming'});
    expect(gaming).toMatchObject({lowPower:true, animations:false, particles:false,
      bubbles:false, alwaysOnTop:false, voiceEnabled:true, wakeWordEnabled:true});
    const quiet = effectiveSettings({...base, mode: 'do_not_disturb'});
    expect(quiet).toMatchObject({voiceEnabled:false, wakeWordEnabled:false, lowPower:true});
    expect(effectiveSettings(base)).toBe(base);
    expect(base).toMatchObject({animations:true, particles:true, bubbles:true, alwaysOnTop:true});
    expect(effectiveSettings(validateSettings({mode:'normal'}, {...base, mode:'gaming'})))
      .toMatchObject({animations:true, particles:true, bubbles:true, alwaysOnTop:true});
    expect(() => validateSettings({mode:'invalid' as never})).toThrow('Modo');
  });
  it('anuncia la misma versión que el paquete instalado', () => {
    expect(APP_VERSION).toBe(packageInfo.version);
  });
  it('migra la apariencia existente y valida las tres formas sin cambiar voz o conexión', () => {
    expect(validateSettings({}).petStyle).toBe('crystal');
    for (const petStyle of ['crystal', 'cloud', 'orbit', 'sprite', 'bloom'] as const) {
      const settings = validateSettings({petStyle});
      expect(settings.petStyle).toBe(petStyle);
      expect(settings.ttsEngine).toBe(defaults.ttsEngine);
      expect(settings.gatewayUrl).toBe(defaults.gatewayUrl);
    }
    expect(() => validateSettings({petStyle: 'unknown' as never})).toThrow('Apariencia');
  });
  it("acota recursos y rechaza entradas inválidas", () => {
    expect(validateSettings({ scale: 99, brightness: -1 }).scale).toBe(2);
    expect(validateSettings({ brightness: -1 }).brightness).toBe(0.35);
    expect(() => validateSettings({ scale: NaN })).toThrow();
    expect(() => validateSettings({ agentId: "../main" })).toThrow();
    expect(() => validateSettings({ accent: "url(secret)" })).toThrow();
    expect(validateSettings({ voiceEnabled: true }).gatewayUrl).toBe(
      defaults.gatewayUrl,
    );
  });
  it("impide enviar credenciales por websocket remoto en claro", () => {
    expect(() => gatewayAddress("ws://example.com:18789")).toThrow();
    expect(() => gatewayAddress("wss://user:password@example.com")).toThrow();
    expect(() => gatewayAddress("ws://127.0.0.1:18789?token=secret")).toThrow();
    expect(gatewayAddress("wss://example.com")).toBe("wss://example.com/");
  });
});
describe("máquina de estados", () => {
  it("duerme por inactividad, despierta y completa emociones temporales", () => {
    const m = new PetMachine(0);
    expect(m.tick(30, 29999).state).toBe("IDLE");
    expect(m.tick(30, 30000).state).toBe("SLEEPING");
    expect(m.wake(31000).state).toBe("HAPPY");
    expect(m.tick(30, 34000).state).toBe("IDLE");
  });
  it("no duerme durante una conversación y permite interrumpir estados", () => {
    const m = new PetMachine(0);
    m.transition("LISTENING", 10);
    expect(m.tick(30, 90000).state).toBe("LISTENING");
    m.transition("THINKING", 90001);
    m.transition("SPEAKING", 90002);
    m.transition("DRAGGING", 90003);
    expect(m.snapshot.state).toBe("DRAGGING");
    m.transition("ERROR", 90004);
    expect(m.tick(30, 96000).state).toBe("IDLE");
  });
  it('muestra emociones breves y vuelve al reposo', () => {
    const m = new PetMachine(0);
    m.transition('ANGRY', 1000);
    expect(m.tick(30, 4400).state).toBe('ANGRY');
    expect(m.tick(30, 4500).state).toBe('IDLE');
    m.transition('LAUGHING', 5000);
    expect(m.tick(30, 8000).state).toBe('IDLE');
  });
});
describe('expresión según la propia respuesta', () => {
  it('elige matices claros sin atribuir emociones al usuario', () => {
    expect(expressionForReply('Jajaja, eso sí estuvo bueno.')).toBe('LAUGHING');
    expect(expressionForReply('Qué rabia, esa falla volvió.')).toBe('ANGRY');
    expect(expressionForReply('Lo siento, Jefe.')).toBe('SAD');
    expect(expressionForReply('Lo logramos. Buen trabajo.')).toBe('PROUD');
    expect(expressionForReply('Me intriga esa posibilidad.')).toBe('CURIOUS');
    expect(expressionForReply('Aquí tienes el resultado.')).toBe('HAPPY');
    expect(expressionForReply('> Qué rabia, esa falla volvió.\nYa identifiqué la causa.')).toBe('HAPPY');
    expect(expressionForReply('El log dice `lo siento` y responde bien.')).toBe('HAPPY');
  });
});
describe("eventos reales de OpenClaw", () => {
  it("conserva mensajes en vivo al recibir un snapshot de arranque anterior", () => {
    const result = mergeMessages(
      [{ id: "history", role: "assistant", text: "Antes" }],
      [
        { id: "user:run", role: "user", text: "Pregunta" },
        { id: "run", role: "assistant", text: "Respuesta" },
      ],
    );
    expect(result.map((message) => message.text)).toEqual([
      "Antes",
      "Pregunta",
      "Respuesta",
    ]);
    expect(
      mergeMessages(
        [{ id: "run", role: "assistant", text: "Parcial" }],
        [{ id: "run", role: "assistant", text: "Final" }],
      )[0].text,
    ).toBe("Final");
  });
  const sessionKey = "agent:main:main";
  it("aísla otras sesiones y no muestra pensamiento ni herramientas internas", () => {
    expect(
      routeGatewayEvent(
        "chat",
        {
          sessionKey: "agent:other:main",
          state: "final",
          message: { content: "secret" },
        },
        sessionKey,
      ),
    ).toEqual([]);
    expect(
      extractText({
        content: [
          { type: "thinking", thinking: "private" },
          {
            type: "text",
            text: "<think>oculto</think>Hola [[reply_to_current]]<tool_call>oculto</tool_call>",
          },
        ],
      }),
    ).toBe("Hola");
    expect(extractText({ content: "<think>pensamiento incompleto" })).toBe("");
  });
  it("mapea herramientas y respuestas sin fingir audio", () => {
    expect(
      routeGatewayEvent(
        "agent",
        {
          runId: "r1",
          seq: 1,
          ts: 1,
          stream: "tool",
          data: { phase: "start", name: "read" },
        },
        sessionKey,
        new Set(["r1"]),
      )[0],
    ).toMatchObject({ type: "pet", state: "THINKING" });
    expect(
      routeGatewayEvent(
        "agent",
        {
          runId: "other",
          seq: 1,
          ts: 1,
          stream: "tool",
          data: { phase: "start", name: "read" },
        },
        sessionKey,
        new Set(["r1"]),
      ),
    ).toEqual([]);
    const events = routeGatewayEvent(
      "chat",
      {
        sessionKey,
        runId: "r1",
        state: "final",
        message: { content: [{ type: "text", text: "Hola" }] },
      },
      sessionKey,
    );
    expect(events[0]).toMatchObject({
      type: "chat",
      final: true,
      message: { id: "r1", text: "Hola" },
    });
    expect(events.some((e) => e.type === "pet" && e.state === "SPEAKING")).toBe(
      false,
    );
  });
  it("mapea cancelación y errores", () => {
    expect(
      routeGatewayEvent("chat", { sessionKey, state: "aborted" }, sessionKey)[0]
        .type,
    ).toBe("voice-cancel");
    expect(
      routeGatewayEvent("chat", { sessionKey, state: "error" }, sessionKey)[0],
    ).toMatchObject({ type: "pet", state: "ERROR" });
  });
  it("acumula deltaText v4 y conserva el filtro de pensamiento entre fragmentos", () => {
    let previous = nextChatText({ deltaText: "<think>razonamiento" });
    expect(
      routeGatewayEvent(
        "chat",
        { sessionKey, runId: "r", state: "delta", deltaText: " privado" },
        sessionKey,
        new Set(),
        previous,
      ).some((e) => e.type === "chat"),
    ).toBe(false);
    previous = nextChatText({ deltaText: " privado</think>Hola " }, previous);
    const events = routeGatewayEvent(
      "chat",
      { sessionKey, runId: "r", state: "delta", deltaText: "Karen" },
      sessionKey,
      new Set(),
      previous,
    );
    expect(events[0]).toMatchObject({
      type: "chat",
      message: { text: "Hola Karen" },
    });
    expect(nextChatText({ deltaText: "Cambio", replace: true }, previous)).toBe(
      "Cambio",
    );
  });
});
