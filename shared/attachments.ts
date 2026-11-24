import type { ImageAttachment } from "./types.js";

export function validateImages(value: unknown): ImageAttachment[] {
  if (value === undefined) return [];
  if (!Array.isArray(value) || value.length > 1) throw new Error("Adjunta una sola captura.");
  return value.map((image) => {
    if (!image || image.type !== "image" || !["image/jpeg", "image/png"].includes(image.mimeType) || typeof image.content !== "string" || image.content.length > 4_000_000 || !/^[A-Za-z0-9+/]+={0,2}$/.test(image.content)) throw new Error("Captura inválida o demasiado grande.");
    return { type: "image", mimeType: image.mimeType, fileName: "karen-screen." + (image.mimeType === "image/png" ? "png" : "jpg"), content: image.content };
  });
}
