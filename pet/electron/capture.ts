import { desktopCapturer } from "electron";
import type { CaptureSource, ImageAttachment } from "../shared/types.js";


export class ScreenCapture {
  private choices = new Map<string, { selectedAt: number; displayId: string }>();
  private reviewedScreen?: { id: string; at: number };
  async sources(): Promise<CaptureSource[]> {
    const sources = await desktopCapturer.getSources({ types: ["screen", "window"], thumbnailSize: { width: 0, height: 0 }, fetchWindowIcons: false });
    this.choices.clear();
    return sources.map(source => {
      this.choices.set(source.id, { selectedAt: Date.now(), displayId: source.display_id });
      return { id: source.id, name: source.name, ...(source.id.startsWith('screen:') && source.display_id ? { canPoint: true } : {}) };
    });
  }
  async snapshot(id: string): Promise<ImageAttachment> {
    const choice = this.choices.get(id);
    if (!choice || Date.now() - choice.selectedAt > 120000) throw new Error("Vuelve a elegir una pantalla o ventana.");
    const sources = await desktopCapturer.getSources({ types: [id.startsWith("screen:") ? "screen" : "window"], thumbnailSize: { width: 1600, height: 900 }, fetchWindowIcons: false });
    const source = sources.find(source => source.id === id);
    if (!source || source.thumbnail.isEmpty()) throw new Error("La ventana no está disponible. Puede estar minimizada o protegida.");
    if (id.startsWith('screen:')) this.reviewedScreen = { id, at: Date.now() };
    return { type: "image", mimeType: "image/jpeg", fileName: "karen-screen.jpg", content: source.thumbnail.toJPEG(80).toString("base64") };
  }
  selectedScreen(): string | undefined {
    const reviewed = this.reviewedScreen;
    if (!reviewed || Date.now() - reviewed.at > 120000) return undefined;
    try { this.pointDisplay(reviewed.id); return reviewed.id; }
    catch { return undefined; }
  }
  pointDisplay(id: string): string {
    const choice = this.choices.get(id);
    if (!id.startsWith('screen:') || !choice?.displayId || Date.now() - choice.selectedAt > 120000)
      throw new Error('Elige de nuevo la pantalla para señalar.');
    return choice.displayId;
  }
}
