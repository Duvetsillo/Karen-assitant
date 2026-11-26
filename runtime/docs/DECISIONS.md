# Decisiones técnicas

## 2026-11-26

1. Mantener el monolito modular Python y los clientes existentes. Node no es el
   runtime principal de este checkout; cambiarlo duplicaría sistemas funcionales.
2. Integrar los módulos Obsidian/eventos previos. Corregir únicamente la normalización
   de Markdown y añadir prevalidación; conservar su diseño y controles de rutas.
3. Usar carpetas explícitas, no descubrimiento indiscriminado del vault. Índice
   reconstruible y backups fuera de la bóveda; configuración local fuera de Git.
4. Mantener aprobación por paso de las escrituras documentales. Las notas y
   propuestas de modelos nunca otorgan autorización. No debilitar permisos del producto.
5. Usar el modo gaming ya persistido por Core. Restringir nuevas asignaciones a CPU;
   no cerrar procesos ni prometer cancelación inmediata de una inferencia ya activa.
6. Registrar solo metadatos validados en eventos. Rotación de 256 KiB, tres copias;
   cerrar handles tras cada escritura para compatibilidad Windows y clientes antiguos.
7. Guardar handoffs en SQLite existente con payload DPAPI. Exportar JSON mediante
   consulta explícita. Un resultado reportado no certifica una capacidad instalada.
8. No añadir dependencias, servicios, embeddings ni modelos nuevos en este incremento.
9. Mover notas mediante publicación sin sobrescritura y eliminación posterior con
   backup. Ante fallo parcial conservar ambas copias y exigir revisión; no reintentar escrituras.
10. Programar solo herramientas READ sobre Plans. Las escrituras siguen requiriendo
    aprobación exacta; el runner automático es optativo y aplaza trabajo en gaming.
11. Sustituir el filtro de 200 recuerdos recientes por 200 candidatos FTS pertinentes.
    Conservar ranking, confirmación, sensibilidad y compatibilidad con escritores antiguos.
12. Registrar accesos como metadatos operativos; no interpretarlos como lectura humana.
    Las correcciones del usuario se registran como tales y no cambian políticas.
13. Conservar procedencia importada separada de historia y ejecuciones locales.
    Importar deja datos pendientes y no modifica duplicados; revisar exige una
    huella vigente por recuerdo. Las contradicciones se calculan al revisar hechos.
14. Exponer solo metadatos a Pet/móvil reutilizando autenticación y SQLite actuales.
    No ampliar permisos del vault ni instalar un nuevo ejecutable para probar el contrato.
15. Condiciones del scheduler mediante predicados finitos validados; nunca eval ni shell.
    Mantener READ y runner optativo. Guardar eventos pendientes y deduplicación en SQLite.
    Suprimir triggers mientras se ejecuta un plan programado para evitar bucles entre
    workers, aceptando la pérdida de eventos externos coincidentes. Sin replay de logs.
