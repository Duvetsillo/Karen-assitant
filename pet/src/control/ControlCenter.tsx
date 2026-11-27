import { ArrowUpRight, AudioLines, Bell, Brain, Database, Eye, Gauge, Layers, Music2, Palette, ShieldCheck, Sparkles, Workflow } from 'lucide-react';
import { useStore } from '../state/store';

export const controlSections = [
  { title: 'Apariencia', description: 'Forma, luz y presencia en el escritorio.', target: 'Apariencia', icon: Palette },
  { title: 'Animaciones', description: 'Ritmo, reposo, saludos y movimiento.', target: 'Comportamiento', icon: Sparkles },
  { title: 'Inteligencia artificial', description: 'Modelo, sesión y conexión local.', target: 'OpenClaw', icon: Brain },
  { title: 'Personalidad', description: 'Iniciativa, expresividad y compañía.', target: 'Personalidad', icon: Layers },
  { title: 'Voz', description: 'Tu voz, su respuesta y las interrupciones.', target: 'Voz', icon: AudioLines },
  { title: 'Entorno', description: 'Compartir audio o pantalla de forma explícita.', target: 'Percepción', icon: Eye },
  { title: 'Música', description: 'Reproductor, plataformas y reacciones.', target: 'Música', icon: Music2 },
  { title: 'Memoria', description: 'Consultar tus datos y decidir qué compartir.', target: 'Memoria', icon: Database },
  { title: 'Obsidian', description: 'Notas y proyectos con permisos del Core.', target: 'Obsidian', icon: Layers },
  { title: 'Agentes y herramientas', description: 'Conexiones y aprobaciones para actuar.', target: 'Herramientas', icon: Workflow },
  { title: 'Proactividad', description: 'Sugerencias y horarios de tranquilidad.', target: 'Iniciativa', icon: Bell },
  { title: 'Rendimiento', description: 'Recursos, modo Gaming y disponibilidad.', target: 'Sistema', icon: Gauge },
  { title: 'Privacidad y seguridad', description: 'Percepción, voz y acceso bajo tu control.', target: 'Privacidad', icon: ShieldCheck },
];

export function ControlCenter() {
  return <section className="control-center"><div className="control-introduction"><span className="eyebrow">UN ESPACIO PARA CADA COSA</span><h2>Karen, a tu manera.</h2><p>Elige qué quieres ajustar. Las opciones avanzadas aparecen cuando las necesitas.</p></div>
    <div className="control-directory">{controlSections.map(({title,description,target,icon:Icon}) => <button key={title} onClick={() => useStore.setState({tab:target})}><Icon size={22}/><span><strong>{title}</strong><small>{description}</small></span><ArrowUpRight size={16}/></button>)}</div>
  </section>;
}

export function CoreArea({ area }: { area: 'Memoria' | 'Obsidian' | 'Herramientas' }) {
  const copy = {
    Memoria: { title: 'Tus recuerdos, bajo tu control.', text: 'La memoria persistente vive en Karen Core. Las consultas de memoria se resuelven localmente; compartir contenido con un proveedor requiere una acción explícita.', command: '/memoria', action: 'Consultar memoria' },
    Obsidian: { title: 'Un lugar para lo que aprendes.', text: 'Core dispone de búsqueda y edición de Markdown con raíces autorizadas. La conexión directa del vault a este panel no está disponible todavía; consulta su estado antes de configurar acceso.', command: '/core', action: 'Consultar estado de Core' },
    Herramientas: { title: 'Capacidad no significa permiso.', text: 'OpenClaw conserva los permisos de sus herramientas. La captura y las acciones visuales necesitan autorización independiente. Los conectores sin adaptador permanecen fuera de la ejecución.', command: '/core', action: 'Consultar capacidades del Core' },
  }[area];
  return <section className="core-area"><span className="eyebrow">{area.toUpperCase()}</span><h2>{copy.title}</h2><p>{copy.text}</p><button onClick={() => useStore.setState({tab:'Conversación',conversationDraft:copy.command})}>{copy.action}<ArrowUpRight size={15}/></button><small>El comando se prepara en el editor. Tú decides cuándo enviarlo.</small></section>;
}
