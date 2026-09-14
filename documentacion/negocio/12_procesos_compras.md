# 12. Procesos de compras

---

## 12.1 Ordenes de compra

### Crear o subir

1. Menu **Ordenes**, nueva.
2. Elegir crear en sistema o subir archivo.
3. Capturar proveedor, condiciones y lineas (o el archivo).
4. Se genera folio de orden.

### Alcance por rol

| Rol | Ve | Terminar |
|-----|----|----------|
| Usuario | Solo las que elaboro | No |
| Tecnico IT / Administrador | Todas | Si, cuando la orden lo permita |

### Terminar y PDF

Al terminar, el sistema genera el PDF con la plantilla configurada (cuando aplica). Una orden terminada puede usarse al dar de alta equipos contra sus lineas.

### Borrar

Sujeto a reglas: no conviene borrar ordenes terminadas o con equipos ya ligados; el sistema bloquea casos invalidos.

---

## 12.2 Plantillas de documentos

Solo **Administrador**.

1. Menu **Plantillas**.
2. Subir o editar plantillas DOCX, XLSX o PDF.
3. Verificar campos antes de usarlas en ordenes reales.

---

## 12.3 Relacion con inventario

Flujo tipico:

1. Crear o subir la orden.
2. Terminarla (TI).
3. Dar de alta equipos consumiendo el cupo de cada linea.
4. Asignar los equipos al personal destino.
