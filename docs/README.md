# Documentación de Study Timetrial

**Fecha de revisión:** 2026-09-11  
**Estado:** vigente para la implementación actual

## Cómo usar esta documentación

La documentación técnica y funcional de Study Timetrial está organizada en cuatro especificaciones complementarias:

1. [Arquitectura general](ARQUITECTURA_2026-09-07.md): Capas de diseño (Presentación, Aplicación, Dominio, Infraestructura), diagrama Mermaid, responsabilidades de cada módulo y reglas de diseño.
2. [Arquitectura de presentación](ARQUITECTURA_PRESENTACION.md): Descomposición modular de la interfaz gráfica, componentes especializados, motor de temas con tokens de diseño y guía de extensibilidad.
3. [Especificación funcional](Study%20Timetrial%20%E2%80%94%20Especificaci%C3%B3n%20funcional%20y%20estructura%20de%20datos.md): Descripción funcional detallada de las 4 vistas (Cronómetro, Registros, Estadísticas, Planificador), flujo de sesión, navegación con control de límites, resolución de desfasaje de incisos, filtros estilo Excel, temas y sonido.
4. [Contrato de persistencia JSON](CONTRATO_JSON.md): Esquema JSON versión `1` para `Record`, `TimerItem` y `PlannedSection`, estructura de archivos auxiliares y reglas de compatibilidad hacia atrás.
5. [Operación y validación](OPERACION_Y_VALIDACION.md): Requisitos de entorno, instrucciones de instalación, ejecución de tests unitarios, comandos de compilación de sintaxis y protocolo de validación manual paso a paso.
6. [Product Backlog y Hoja de Ruta](../BACKLOG.md): Hoja de ruta del proyecto, backlog categorizado por tipo, prioridad y capas arquitectónicas, con criterios de aceptación detallados y optimizado para agentes.

## Convenciones de estado

- **Implementado:** Comportamiento y módulos verificados en el código activo del proyecto.
- **Contrato:** Reglas invariantes que deben respetarse al realizar refactorizaciones o extensiones futuras.
- **Pendiente:** Mejoras o nuevas características no contempladas en el alcance de la versión actual.

Para validar cualquier cambio en el código fuente, la comprobación mínima requerida está detallada en [Operación y validación](OPERACION_Y_VALIDACION.md).
