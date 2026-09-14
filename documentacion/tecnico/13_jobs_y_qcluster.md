# 13. Jobs y qcluster

---

## 13.1 Proposito

Ejecutar trabajos periodicos sin Redis, usando django-q2 con broker ORM en PostgreSQL.

---

## 13.2 Piezas

| Archivo | Rol |
|---------|-----|
| `schedules.py` | Define/actualiza schedules idempotentes |
| `tasks.py` | Funciones ejecutadas por el worker |
| `job_queue.py` | Encolar (async o sync de respaldo) |
| `management/commands/setup_background_jobs.py` | Asegura schedules |
| Settings | `Q_CLUSTER`, `BACKGROUND_JOBS_*` |

Worker: `python manage.py qcluster`.

---

## 13.3 Schedules

| Nombre | Tarea | Cadencia |
|--------|-------|----------|
| `historial-retencion-diaria` | `task_aplicar_retencion` | Diario a las 02:00 **hora local** |
| `recordatorios-operativos-15m` | `task_recordatorios_operativos` | Cada 15 minutos |

La hora local se calcula con `timezone.localtime` (no asumir UTC ciego).

---

## 13.4 Tareas

### Retencion

Aplica archivo/purga segun `HISTORIAL_RETENCION`, registra evento de sistema e invalida cache de metricas.

### Recordatorios operativos

Recalcula panorama de alertas (SLA, mantenimientos, etc.). Si el fingerprint cambio, escribe aviso en historial. No envia correo.

---

## 13.5 Modo sync

Si `BACKGROUND_JOBS_SYNC=True` o falla el enqueue, ciertas tareas pueden correr en el request (util en desarrollo sin worker).

---

## 13.6 CLI relacionada

```text
python manage.py limpiar_historial
python manage.py limpiar_historial --dry-run
python manage.py limpiar_historial --async
python manage.py setup_background_jobs
```

---

## 13.7 Como probar

Verificar que existen schedules tras migrate/`setup_background_jobs`; dry-run de retencion; proceso `qcluster` vivo en el entorno de uso.
