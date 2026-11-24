export const PET_SCALE = { min: 0.5, max: 2 } as const;
export interface Rectangle {
  x: number;
  y: number;
  width: number;
  height: number;
}

/** Keep the pet's feet and horizontal center steady, and preserve its aspect ratio. */
export function petBounds(scale: number, previous: Rectangle, area: Rectangle): Rectangle {
  const fit = Math.min(scale, area.width / 380, area.height / 440);
  const width = Math.round(380 * fit);
  const height = Math.round(440 * fit);
  return {
    width,
    height,
    x: Math.round(Math.max(area.x, Math.min(area.x + area.width - width, previous.x + (previous.width - width) / 2))),
    y: Math.round(Math.max(area.y, Math.min(area.y + area.height - height, previous.y + previous.height - height))),
  };
}
