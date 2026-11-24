import { describe, expect, it } from 'vitest';
import { pointCoordinates, parsePointDirective, screenPointIntent, stripPointPrefix } from '../electron/pointing';
import { pointInImage } from '../src/pointing';

describe('señalamiento sin clics', () => {
  it('sitúa el objetivo en un monitor con coordenadas negativas', () => {
    expect(pointCoordinates({x:-1920,y:0,width:1920,height:1080},0.5,0.25)).toEqual({x:-960,y:270});
    expect(() => pointCoordinates({x:0,y:0,width:100,height:100},Number.NaN,0.5)).toThrow();
    expect(() => pointCoordinates({x:0,y:0,width:100,height:100},1.1,0.5)).toThrow();
  });
  it('ignora los márgenes vacíos de una vista previa con object-fit contain', () => {
    const rect={left:10,top:20,width:400,height:300};
    expect(pointInImage(rect,1600,900,210,170)).toEqual({x:0.5,y:0.5});
    expect(pointInImage(rect,1600,900,210,30)).toBeNull();
  });
  it('acepta solo una coordenada normalizada al inicio de la respuesta', () => {
    expect(parsePointDirective('[[POINT:0.25,0.75]] Aquí está.')).toEqual({x:0.25,y:0.75,text:'Aquí está.'});
    expect(parsePointDirective('[[POINT: 0.25, 0.75]] Aquí está.')).toEqual({x:0.25,y:0.75,text:'Aquí está.'});
    expect(parsePointDirective('[[POINT:2,0.5]] No estoy segura.')).toEqual({text:'No estoy segura.'});
    expect(parsePointDirective('[[NO_POINT]] No distingo un video.')).toEqual({text:'No distingo un video.'});
    expect(stripPointPrefix('[[POINT:0.25,0.75]] Aquí está.')).toBe('Aquí está.');
    expect(stripPointPrefix('[[POINT:0.25')).toBe('');
  });
  it('reconoce una orden explícita de señalar sin capturar una charla cualquiera', () => {
    expect(screenPointIntent('Karen, señala el video en mi pantalla')).toBe('el video');
    expect(screenPointIntent('Pon el dedo encima de la ventana azul')).toBe('la ventana azul');
    expect(screenPointIntent('Karen, ponle el dedo encima a un video')).toBe('un video');
    expect(screenPointIntent('Muéstrame el video de mi escritorio')).toBe('el video');
    expect(screenPointIntent('Muéstrame un ejemplo de código')).toBeNull();
  });
});
