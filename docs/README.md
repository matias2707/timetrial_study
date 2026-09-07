# Documentación de Study Timetrial

**Fecha de revisión:** 2026-09-07  
**Estado:** vigente para la implementación actual

## Cómo usar esta documentación

Los documentos se organizan por propósito:

1. [Arquitectura](ARQUITECTURA_2026-09-07.md): capas, responsabilidades, dependencias y reglas de evolución.
2. [Especificación funcional](Study%20Timetrial%20%E2%80%94%20Especificaci%C3%B3n%20funcional%20y%20estructura%20de%20datos.md): flujos visibles y reglas de la aplicación.
3. [Contrato JSON](CONTRATO_JSON.md): formato persistido, compatibilidad y archivos auxiliares.
4. [Operación y validación](OPERACION_Y_VALIDACION.md): instalación, ejecución, pruebas y diagnóstico básico.

## Convenciones de estado

- **Implementado:** comportamiento comprobado en el código actual.
- **Contrato:** regla que debe preservarse al modificar la aplicación.
- **Pendiente:** mejora o decisión que no forma parte del comportamiento actual.

La documentación no sustituye a las pruebas. Para cambios de código, la
validación mínima está definida en [Operación y validación](OPERACION_Y_VALIDACION.md).
