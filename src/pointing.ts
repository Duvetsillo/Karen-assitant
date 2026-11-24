/** Map a click on an object-fit: contain preview to the source image. */
export function pointInImage(rect: { left: number; top: number; width: number; height: number }, naturalWidth: number, naturalHeight: number, clientX: number, clientY: number) {
  if (![rect.left, rect.top, rect.width, rect.height, naturalWidth, naturalHeight, clientX, clientY].every(Number.isFinite) ||
    rect.width <= 0 || rect.height <= 0 || naturalWidth <= 0 || naturalHeight <= 0) return null;
  const scale = Math.min(rect.width / naturalWidth, rect.height / naturalHeight);
  const width = naturalWidth * scale;
  const height = naturalHeight * scale;
  const x = (clientX - rect.left - (rect.width - width) / 2) / width;
  const y = (clientY - rect.top - (rect.height - height) / 2) / height;
  return x >= 0 && x <= 1 && y >= 0 && y <= 1 ? { x, y } : null;
}
