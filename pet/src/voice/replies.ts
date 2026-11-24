import type { CaptureStatus, ChatMessage } from "../../shared/types";

/** Keep final replies until capture ends; never interrupt a reply with its successor. */
export class VoiceReplies {
  private pending: ChatMessage[] = [];
  private seen = new Set<string>();
  private running = false;
  private epoch = 0;
  constructor(
    private speak: (text: string) => Promise<void>,
    private state: () => { enabled: boolean; capture: CaptureStatus },
  ) {}
  enqueue(message: ChatMessage) {
    if (!this.state().enabled || message.role !== "assistant" || !message.text.trim() || this.seen.has(message.id)) return;
    this.seen.add(message.id);
    if (this.seen.size > 200) this.seen.delete(this.seen.values().next().value!);
    this.pending.push(message);
    this.pending = this.pending.slice(-8);
    this.resume();
  }
  resume() {
    if (this.running || !this.pending.length || !this.state().enabled || this.state().capture.phase !== "idle") return;
    const message = this.pending.shift()!;
    const epoch = this.epoch;
    this.running = true;
    const finished = () => {
      if (epoch !== this.epoch) return;
      this.running = false;
      this.resume();
    };
    void this.speak(message.text).then(finished, finished);
  }
  clear() {
    this.epoch++;
    this.pending = [];
    this.running = false;
  }
}

/** Sentence boundaries allow the next clip to generate while this one plays. */
export function speechPhrases(text: string, limit = 4096, sentenceTarget = 0, firstSentenceTarget = sentenceTarget): string[] {
  const plain = text
    .replace(/```[\s\S]*?(?:```|$)/g, " ")
    .replace(/!\[[^\]]*\]\([^)]*\)/g, " ")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/https?:\/\/\S+/g, " ")
    .replace(/^[\s#>*+-]+/gm, "")
    .replace(/[*_`]/g, "")
    .trim();
  const result: string[] = [];
  let phrase = "";
  for (const word of plain.split(/\s+/).filter(Boolean)) {
    let remaining = word;
    while (remaining) {
      if (phrase && phrase.length + remaining.length + 1 > limit) {
        result.push(phrase);
        phrase = "";
        continue;
      }
      const part = remaining.slice(0, limit);
      phrase = [phrase, part].filter(Boolean).join(" ");
      remaining = remaining.slice(part.length);
      if (phrase.length >= limit) {
        result.push(phrase);
        phrase = "";
      }
    }
    const target = result.length === 0 ? firstSentenceTarget : sentenceTarget;
    if (target > 0 && phrase.length >= target && /[.!?…]["'»”)]?$/.test(word)) {
      result.push(phrase);
      phrase = "";
    }
  }
  if (phrase) result.push(phrase);
  return result;
}
