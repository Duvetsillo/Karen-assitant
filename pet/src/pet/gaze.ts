/** Bounded elliptical travel keeps both pupils inside their luminous eye shapes. */
export function gazeTarget(cursor: { x: number; y: number }, active: boolean) {
  if (!active || !Number.isFinite(cursor.x) || !Number.isFinite(cursor.y))
    return { x: 0, y: 0 };
  const x = (cursor.x - 0.5) * 2.8;
  const y = (cursor.y - 0.52) * 2.8;
  const length = Math.max(1, Math.hypot(x, y));
  return { x: (x / length) * 14, y: (y / length) * 9 };
}
