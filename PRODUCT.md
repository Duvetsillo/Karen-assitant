# Karen Desktop Pet

Aplicación de Windows para representar al asistente Karen existente en OpenClaw.
La mascota es una criatura de vidrio holográfico azul con aletas, ojos luminosos y
un corazón incrustado. No representa a una persona. Su propósito es acompañar en
el escritorio, reflejar actividad real y permitir conversación de texto o voz.

OpenClaw conserva el modelo, la ejecución de herramientas y sus permisos. El
cliente no incorpora otro modelo de lenguaje ni cambia la configuración del Gateway.
El panel distingue conexión real, demostración visual y servicios no disponibles.
El micrófono requiere una acción explícita; no se utiliza cámara.

Electron proporciona las funciones de Windows. Un servidor Node independiente
reutiliza el adaptador oficial para autoalojar la interfaz sin escritorio. Cada
instalación aporta su propio Gateway y secretos. React, TypeScript estricto,
Zustand, PixiJS y Web Audio mantienen las capas sustituibles.
