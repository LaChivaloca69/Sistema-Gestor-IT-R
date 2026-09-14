# 3. Glosario

Terminos usados en pantallas y en este manual. Orden alfabetico.

| Termino | Significado |
|---------|-------------|
| Administrador | Rol con acceso a gobierno del sistema y a borrados criticos |
| Asignacion | Vinculo entre un equipo y un registro de Personal; puede estar Activa, Devuelta o Extraviada |
| Auditoria / Historial de actividad | Registro de quien hizo que, en que modulo y cuando |
| Bitacora | Nota operativa interna de TI (no es un ticket de usuario) |
| Campana | Icono del encabezado con avisos pendientes |
| Categoria | Clasificacion del activo (laptop, monitor, cable, etc.) y de su tipo de inventario |
| Check / Seguimiento | Avance registrado sobre un ticket; puede concluir y cerrar el ticket |
| Cierre de mantenimiento | Registro de acciones y fechas al completar un mantenimiento |
| Cobertura | Delegacion temporal: un tecnico suplente atiende tickets del ausente |
| Consumible | Insumo gestionado por cantidad (cables, alcohol, etc.), no por numero de serie unitario |
| En Stock | Estado de equipo disponible para asignar (tambien llamado disponible en lenguaje cotidiano) |
| Equipo | Activo unitario de inventario (una fila = una pieza) |
| Folio | Identificador legible generado por el sistema (ticket, solicitud, OC, etc.) |
| Gobierno | Conjunto de funciones para **administrar el sistema** (no el trabajo diario de piso): quien tiene cada rol, coberturas entre tecnicos, solicitudes de equipo como tramite formal, consulta de la matriz de permisos, guia del SLA y politicas del historial (archivar o purgar). En la practica es lo que hace principalmente el **Administrador**; el Tecnico IT solo participa en partes operativas de gobierno (por ejemplo coberturas y revision de solicitudes) |
| Herramienta | Tipo de inventario de taller; no se asigna a personal como una laptop |
| Kit / Periferico | Periferico vinculado a un equipo padre (mouse, teclado, etc.) |
| Mesa de ayuda | Funcion de soporte mediante tickets |
| Mantenimiento | Orden formal de trabajo sobre un equipo (preventivo, correctivo o predictivo) |
| Operativo | Tecnico IT o Administrador en tareas de piso |
| Orden de compra (OC) | Documento de compra; puede crearse en sistema o subirse |
| Personal | Ficha de empleado en el sistema; puede vincularse a una cuenta de acceso |
| Plantilla | Archivo base (DOCX, XLSX o PDF) para generar documentos de compra |
| Prioridad | Nivel del ticket (Baja, Media, Alta, Urgente) que alimenta el SLA |
| Rol | Perfil de permisos: Usuario, Tecnico IT o Administrador |
| SLA | Acuerdo de tiempo de atencion segun prioridad del ticket |
| Solicitud de equipo | Pedido formal de un activo; TI decide y puede asignar |
| Tecnico IT | Rol de operacion diaria de inventario, soporte y mantenimiento |
| Ticket | Solicitud de soporte registrada en la mesa de ayuda |
| Ubicacion | Espacio fisico (dentro de edificio y zona) donde puede estar un equipo |
| Usuario | Rol de autoservicio del empleado final |

---

## Estados frecuentes

### Ticket

| Estado | Idea general |
|--------|--------------|
| Abierto | Recien creado o sin flujo de atencion avanzado |
| En Revision | Tomado por TI para analisis |
| En Proceso | Hay seguimiento en curso |
| Cerrado | Resuelto o concluido con solucion |

### Equipo

| Estado | Idea general |
|--------|--------------|
| En Stock | Disponible |
| Asignado | Tiene asignacion activa |
| En Mantenimiento | Hay mantenimiento en proceso sobre el equipo |
| Baja | Fuera de operacion (baja logica) |

### Mantenimiento

| Estado | Idea general |
|--------|--------------|
| Programado | Agendado, aun no iniciado |
| En Proceso | En ejecucion; el equipo suele estar En Mantenimiento |
| Completado | Cerrado con registro de trabajo |
| Cancelado | No se ejecuto o se aborto |

### Solicitud de equipo

Pendiente, En revision, Aprobada, Rechazada, Completada, Cancelada.
