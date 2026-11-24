import type { DesktopEvent, ChatMessage } from "./types.js";
import { expressionForReply } from './expression.js';
export function mergeMessages(
  snapshot: ChatMessage[],
  live: ChatMessage[],
): ChatMessage[] {
  const messages = new Map(snapshot.map((message) => [message.id, message]));
  for (const message of live) messages.set(message.id, message);
  return [...messages.values()].slice(-100);
}
function object(value: unknown): Record<string, unknown> {
  return value && typeof value === "object"
    ? (value as Record<string, unknown>)
    : {};
}
export function rawMessageText(value: unknown): string {
  const m = object(value);
  const content = m.content;
  const text =
    typeof content === "string"
      ? content
      : Array.isArray(content)
        ? content
            .filter((p) => object(p).type === "text")
            .map((p) => object(p).text)
            .filter((v) => typeof v === "string")
            .join("\n")
        : typeof m.text === "string"
          ? m.text
          : "";
  return text;
}
export function extractText(value: unknown): string {
  return rawMessageText(value)
    .replace(/<think\b[^>]*>[\s\S]*?(?:<\/think>|$)/gi, "")
    .replace(/\[\[(?:reply_to_[^\]]*|audio_as_voice)\]\]/g, "")
    .replace(
      /<(tool_call|function_call|tool_calls|function_calls)\b[^>]*>[\s\S]*?(?:<\/\1>|$)/gi,
      "",
    )
    .trim()
    .slice(0, 32000);
}
export function nextChatText(value: unknown, previous = ""): string {
  const p = object(value);
  if (p.message !== undefined) return rawMessageText(p.message).slice(0, 64000);
  if (typeof p.deltaText === "string")
    return (p.replace ? p.deltaText : previous + p.deltaText).slice(0, 64000);
  return previous;
}
export function routeGatewayEvent(
  name: string,
  value: unknown,
  sessionKey: string,
  knownRuns: ReadonlySet<string> = new Set(),
  previousRaw = "",
): DesktopEvent[] {
  const p = object(value);
  if (
    p.sessionKey !== sessionKey &&
    !(name === "agent" && typeof p.runId === "string" && knownRuns.has(p.runId))
  )
    return [];
  if (name === "chat") {
    const state = p.state;
    const text = extractText({ text: nextChatText(p, previousRaw) });
    if (state === "status") return [{ type: "pet", state: "THINKING" }];
    if (state === "error")
      return [
        { type: "pet", state: "ERROR", reason: "OpenClaw informó un error" },
        {
          type: "chat",
          message: {
            id: String(p.runId ?? "error"),
            role: "assistant",
            text: "OpenClaw no pudo completar la respuesta. Consulta su diagnóstico.",
          },
          final: true,
          speak: false,
        },
      ];
    if (state === "aborted")
      return [
        { type: "voice-cancel" },
        { type: "pet", state: "IDLE" },
        {
          type: "chat",
          message: {
            id: String(p.runId ?? "aborted"),
            role: "assistant",
            text: text || "Respuesta detenida.",
          },
          final: true,
          speak: false,
        },
      ];
    if (state === "delta" || state === "final") {
      const events: DesktopEvent[] = [];
      if (text && !["NO_REPLY", "no_reply", "HEARTBEAT_OK"].includes(text))
        events.push({
          type: "chat",
          message: {
            id: String(p.runId ?? "assistant"),
            role: "assistant",
            text,
            pending: state === "delta",
          },
          final: state === "final",
        });
      if (state === "final")
        events.push({
          type: "pet",
          state: expressionForReply(text),
          reason: "Respuesta completada",
        });
      else events.push({ type: "pet", state: "THINKING" });
      return events;
    }
  }
  if (name === "agent") {
    const data = object(p.data);
    if (p.stream === "tool")
      return [
        {
          type: "pet",
          state: data.isError
            ? "ERROR"
            : data.phase === "result"
              ? "HAPPY"
              : "THINKING",
          reason:
            typeof data.name === "string"
              ? `Herramienta: ${data.name}`
              : "Herramienta de OpenClaw",
        },
      ];
    if (p.stream === "lifecycle") {
      if (data.phase === "start") return [{ type: "pet", state: "THINKING" }];
      if (data.phase === "error") return [{ type: "pet", state: "ERROR" }];
      if (data.phase === "end") return [{ type: "pet", state: "HAPPY" }];
    }
  }
  return [];
}
