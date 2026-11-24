import { describe, expect, it } from "vitest";
import { petBounds } from "../shared/pet-layout";
import { gazeTarget } from "../src/pet/gaze";

describe("tamaño del PET en varios monitores", () => {
  const previous = { x: 100, y: 200, width: 380, height: 440 };
  it("mantiene el punto de apoyo y el centro al cambiar tamaño", () => {
    const area = { x: 0, y: 0, width: 1920, height: 1080 };
    expect(petBounds(0.5, previous, area)).toEqual({ x: 195, y: 420, width: 190, height: 220 });
    const large = petBounds(2, { ...previous, y: 440 }, area);
    expect(large).toEqual({ x: 0, y: 0, width: 760, height: 880 });
  });
  it("cabe sin deformarse en un monitor pequeño con coordenadas negativas", () => {
    const area = { x: -800, y: -100, width: 800, height: 600 };
    const result = petBounds(2, { ...previous, x: -500 }, area);
    expect(result.x).toBeGreaterThanOrEqual(area.x);
    expect(result.x + result.width).toBeLessThanOrEqual(0);
    expect(result.y).toBe(-100);
    expect(result.height).toBe(600);
    expect(result.width / result.height).toBeCloseTo(380 / 440, 2);
  });
});

describe("mirada", () => {
  it("sigue en ambos ejes y limita el recorrido fuera del monitor", () => {
    expect(gazeTarget({ x: 1, y: 0.52 }, true)).toEqual({ x: 14, y: 0 });
    expect(gazeTarget({ x: 0, y: 0.52 }, true)).toEqual({ x: -14, y: 0 });
    const far = gazeTarget({ x: -500, y: 900 }, true);
    expect(Math.hypot(far.x / 14, far.y / 9)).toBeCloseTo(1);
  });
  it("vuelve al centro al dormir o desactivar seguimiento, y rechaza señales inválidas", () => {
    expect(gazeTarget({ x: 2, y: -1 }, false)).toEqual({ x: 0, y: 0 });
    expect(gazeTarget({ x: NaN, y: 0 }, true)).toEqual({ x: 0, y: 0 });
  });
});
