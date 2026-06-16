# Roadmap de Optimización Arquitectónica - Asubarnipal

**Documento de referencia**: [Arquitectura-comparativa.pdf](./Arquitectura-comparativa.pdf)

## Resumen Ejecutivo

Este roadmap define tres fases de optimización para Asubarnipal basadas en un análisis comparativo con 10 repositorios de referencia en el ecosistema de agentes de investigación.

**Objetivos principales:**
- Reducir costes de RAM en 40-60%
- Mejorar calidad de investigación en 30-50%
- Acelerar inferencia de modelos en 2-4x

## Fases de Implementación

### Fase 1: Validación Estricta de Ingesta (ALTA PRIORIDAD)

**Estado**: 🔴 Pendiente  
**Estimación**: 2-3 semanas  
**Impacto**: Mejora calidad de investigación en 30-50%

**Objetivo**: Implementar ontologías rígidas durante la ingesta para garantizar calidad y consistencia de datos.

**Especificación detallada**: [FASE-1-VALIDACION-INGESTA.md](./FASE-1-VALIDACION-INGESTA.md)

**Tareas principales:**
1. Definir esquemas de validación para cada tipo de fuente (URL, PDF, YouTube)
2. Implementar validación bidireccional de citas
3. Añadir métricas de completitud y calidad
4. Integrar con FidelityChecker existente

**Criterios de éxito:**
- 100% de ingestas validadas contra esquemas
- 0 citas huérfanas (todas verificadas)
- Score de calidad mínimo de 80/100 en todas las ingestas

---

### Fase 2: Aceleración de TurboQuant (PRIORIDAD MEDIA)

**Estado**: 🔴 Pendiente  
**Estimación**: 3-4 semanas  
**Impacto**: Acelera inferencia en 2-4x, reduce uso de RAM en 30%

**Objetivo**: Integrar PyTorch para cuantización de modelos y optimización con kernels CUDA.

**Especificación detallada**: [FASE-2-TURBOQUANT.md](./FASE-2-TURBOQUANT.md)

**Tareas principales:**
1. Integrar PyTorch en `core/turboquant_engine.py`
2. Implementar cuantización de 4 bits con rangos asimétricos
3. Añadir kernels CUDA personalizados
4. Implementar retención de histórico en memoria

**Criterios de éxito:**
- Inferencia 2-4x más rápida en modelos cuantizados
- Reducción de 30% en uso de RAM
- Compatibilidad con modelos GGUF existentes

---

### Fase 3: Búsqueda Híbrida y Fusión de Clasificación (PRIORIDAD MEDIA-BAJA)

**Estado**: 🔴 Pendiente  
**Estimación**: 2-3 semanas  
**Impacto**: Mejora precisión de búsqueda en 25-40%

**Objetivo**: Combinar búsqueda vectorial (FAISS) con búsqueda por grafos (Graphify) y fusionar resultados.

**Especificación detallada**: [FASE-3-BUSQUEDA-HIBRIDA.md](./FASE-3-BUSQUEDA-HIBRIDA.md)

**Tareas principales:**
1. Implementar fusión de resultados vectoriales y de grafos
2. Añadir fusión de clasificadores para scoring
3. Integrar telemetría detallada de búsquedas
4. Optimizar `/query` y `/queryhybrid`

**Criterios de éxito:**
- Precisión de búsqueda mejorada en 25-40%
- Telemetría completa de todas las búsquedas
- Latencia < 2s para queries complejas

---

## Métricas de Éxito Global

| Métrica | Actual | Objetivo | Mejora |
|---------|--------|----------|--------|
| Calidad de investigación (FidelityChecker) | ~70/100 | 90+/100 | +30% |
| Uso de RAM (modelo grande) | ~8GB | ~4.8GB | -40% |
| Velocidad de inferencia | ~3s/query | ~1s/query | 3x |
| Precisión de búsqueda | ~65% | ~90% | +38% |

## Dependencias y Riesgos

### Dependencias Críticas
- PyTorch 2.0+ con soporte CUDA
- Graphify actualizado con API de búsqueda
- FidelityChecker funcional (ya implementado)

### Riesgos Identificados
1. **Compatibilidad de modelos**: Algunos modelos pueden no soportar cuantización de 4 bits
2. **Calidad vs velocidad**: Cuantización agresiva puede degradar calidad
3. **Complejidad de fusión**: Fusionar resultados de múltiples fuentes es complejo

## Próximos Pasos Inmediatos

1. **Revisar especificaciones detalladas** de cada fase
2. **Priorizar Fase 1** (validación de ingesta) por su impacto en calidad
3. **Crear issues en GitHub** para cada tarea específica
4. **Asignar responsables** y estimaciones de tiempo
5. **Establecer milestones** y fechas de entrega

## Referencias

- **Análisis completo**: [Arquitectura-comparativa.pdf](./Arquitectura-comparativa.pdf)
- **Repositorios comparados**: Ver página 13 del PDF
- **Fundamentos matemáticos**: Páginas 4-5 del PDF (TurboQuant)

---

**Última actualización**: 2026-06-10  
**Versión**: 1.0  
**Autor**: Análisis arquitectónico comparativo
