"""Guia documentada del SLA de tickets (solo lectura / documentacion)."""

from .models import PrioridadSupport, SLA_HORAS_POR_PRIORIDAD

# Aviso "por vencer": el menor entre este tope y el 25 % del SLA.
SLA_AVISO_TOPE_HORAS = 4
SLA_AVISO_FRACCION = 0.25

_PRIORIDAD_ORDEN = (
    PrioridadSupport.URGENTE,
    PrioridadSupport.ALTA,
    PrioridadSupport.MEDIA,
    PrioridadSupport.BAJA,
)


def _formato_duracion(horas):
    if horas == int(horas):
        horas = int(horas)
        if horas % 24 == 0:
            dias = horas // 24
            return "1 dia" if dias == 1 else f"{dias} dias"
        return "1 hora" if horas == 1 else f"{horas} horas"
    minutos = int(round(float(horas) * 60))
    return "1 minuto" if minutos == 1 else f"{minutos} minutos"


def _horas_aviso(horas_sla):
    return min(SLA_AVISO_TOPE_HORAS, horas_sla * SLA_AVISO_FRACCION)


def sla_guide_for_template():
    """Datos para la pantalla Admin de guia SLA. Sin codigo en la UI."""
    filas_prioridad = []
    for value in _PRIORIDAD_ORDEN:
        horas = SLA_HORAS_POR_PRIORIDAD[value]
        filas_prioridad.append(
            {
                "prioridad": value.label,
                "horas": horas,
                "equivalente": _formato_duracion(horas),
                "aviso": f"Cuando quedan {_formato_duracion(_horas_aviso(horas))}",
            }
        )

    return {
        "que_es": (
            "SLA significa Service Level Agreement (acuerdo de nivel de servicio). "
            "En Gestor IT no es un contrato legal: es el tiempo maximo interno "
            "para atender un ticket segun su prioridad."
        ),
        "como_se_mide": [
            "El reloj empieza en la fecha y hora de creacion del ticket.",
            "La fecha limite es esa creacion mas las horas de la prioridad.",
            "El tiempo es calendario corrido: incluye noches, fines de semana y dias festivos. No son dias habiles.",
            "Seguimientos, comentarios o cambios de estado (Abierto, En Revision, En Proceso) no pausan ni reinician el reloj.",
            "El SLA deja de aplicar solo cuando el ticket queda Cerrado.",
            "Si un ticket no tiene prioridad reconocida, se usa Media.",
        ],
        "filas_prioridad": filas_prioridad,
        "criterios_prioridad": [
            {
                "prioridad": "Urgente",
                "badge": "prio-urgente",
                "horas": "4 horas",
                "criterio": "Falla critica general que detiene la operacion o produccion (servidor caido, enlace principal, falla masiva).",
                "ejemplos": "Caida de enlace principal, servidor inoperativo, corte general de sistema de planta.",
            },
            {
                "prioridad": "Alta",
                "badge": "prio-alta",
                "horas": "24 horas (1 dia)",
                "criterio": "Afecta sistemas clave de negocio o a un area completa sin alternativa de trabajo inmediata.",
                "ejemplos": "Bloqueo de facturacion en SAP / BPCS, problema critico en ordenes de produccion, impresora unica de embarques.",
            },
            {
                "prioridad": "Media",
                "badge": "prio-media",
                "horas": "72 horas (3 dias)",
                "criterio": "Incidente que afecta el puesto de un usuario individual pero no detiene la operacion global.",
                "ejemplos": "Laptop lenta o con fallas, desbloqueo de contrasenas o cuentas, problemas con Office / Teams / Outlook.",
            },
            {
                "prioridad": "Baja",
                "badge": "prio-baja",
                "horas": "168 horas (7 dias)",
                "criterio": "Solicitudes programables o problemas con alternativas disponibles (no impiden continuar trabajando).",
                "ejemplos": "Mantenimiento preventivo, perifericos secundarios (mouse, teclado), impresora departamental con equipo alternativo.",
            },
        ],
        "prioridad_regla_usuario": (
            "Al crear un ticket desde la pantalla de seleccion de problema, el sistema sugiere automaticamente "
            "la prioridad correspondiente segun el tipo de falla. El usuario puede cambiarla si su situacion operativa "
            "lo requiere, y el personal tecnico puede reclasificarla durante la revision del ticket."
        ),
        "aviso_regla": (
            f"El aviso Por vencer aparece cuando el tiempo restante es el menor entre "
            f"{_formato_duracion(SLA_AVISO_TOPE_HORAS)} y el 25 % del SLA de esa prioridad. "
            "Por eso Urgente avisa mas pronto (una parte del SLA corto) y el resto avisa "
            f"a las {_formato_duracion(SLA_AVISO_TOPE_HORAS)}."
        ),
        "estados": [
            {
                "nombre": "En tiempo",
                "badge": "asignado",
                "cuando": "El ticket sigue abierto y aun no llega al aviso de por vencer.",
            },
            {
                "nombre": "Por vencer",
                "badge": "advertencia",
                "cuando": "El ticket sigue abierto y ya entro en la ventana de aviso de la tabla de arriba.",
            },
            {
                "nombre": "Vencido",
                "badge": "prio-urgente",
                "cuando": "Ya paso la fecha limite y el ticket sigue abierto.",
            },
            {
                "nombre": "Cerrado",
                "badge": "cerrado",
                "cuando": "El ticket se cerro. El SLA ya no aplica y no se sigue contando.",
            },
        ],
        "donde_se_ve": [
            {
                "lugar": "Lista de tickets",
                "detalle": "Columna SLA y filtros: vencido, por vencer, o SLA o sin check.",
            },
            {
                "lugar": "Detalle del ticket",
                "detalle": "Estado SLA, fecha limite y horas objetivo de la prioridad.",
            },
            {
                "lugar": "Inicio y campana",
                "detalle": "Conteo de tickets con SLA vencido (aviso en panel, sin correo).",
            },
            {
                "lugar": "Panel de tickets",
                "detalle": "KPI de vencidos y por vencer, mas una tabla de horas por prioridad.",
            },
            {
                "lugar": "Calendario de Inicio",
                "detalle": "Un ticket abierto se muestra en el dia de su fecha limite SLA, no en el dia de alta.",
            },
            {
                "lugar": "Historial",
                "detalle": "Un job periodico deja un evento si cambia el panorama de vencidos. No envia correo.",
            },
        ],
        "no_hace": [
            "No cambia el estado del ticket por si solo.",
            "No asigna tecnico ni cierra el ticket al vencer.",
            "No usa horario laboral ni pausas.",
            "Un comentario no mueve el SLA.",
            "Un check (seguimiento) no reinicia el reloj: sigue contando desde la creacion.",
            "Esta pantalla solo documenta el comportamiento actual; no modifica tiempos.",
        ],
    }
