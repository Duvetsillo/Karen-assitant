import type { PetStyle } from './types.js';

export const petStyles: Record<PetStyle, { name: string; description: string }> = {
  crystal: { name: 'Cristal', description: 'Vidrio azul y aletas de luz.' },
  cloud: { name: 'Nube', description: 'Suave, redonda y de tonos perlados.' },
  orbit: { name: 'Órbita', description: 'Caparazón lunar y antenas luminosas.' },
  sprite: { name: 'Lucero', description: 'Pequeña exploradora flotante de luz.' },
  bloom: { name: 'Flor', description: 'Pétalos suaves y una silueta juguetona.' },
  aurora: { name: 'Aurora', description: 'Silueta de gota y reflejos de jade.' },
  ember: { name: 'Ámbar', description: 'Contorno de cometa y destellos cálidos.' },
  midnight: { name: 'Nocturna', description: 'Forma lunar, cristal oscuro y luz violeta.' },
};
