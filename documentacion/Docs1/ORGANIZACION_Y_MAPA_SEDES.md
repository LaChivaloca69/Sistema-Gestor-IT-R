# Organización y Mapa de sedes

Guía del funcionamiento actual: **organización** (departamentos, puestos, personal) y **espacios físicos** (mapa de sedes, almacén / stock).

**Última revisión:** agosto 2026. Relacionado: `MODULOS.md`, `INVENTARIO.md`.

---

## 1. Visión general

Hay **dos ejes distintos** que antes convivían en el mismo menú:

| Eje | Pregunta que responde | Menú |
|-----|----------------------|------|
| **Organización** | ¿A qué departamento pertenece la persona? | Organización |
| **Espacios físicos** | ¿Dónde está físicamente el equipo o el puesto de trabajo? | Espacios físicos → Mapa de sedes |

No se mezclan: gente del mismo departamento puede estar en edificios o escritorios distintos.

```
Organización                          Espacios físicos
─────────────                         ────────────────
Departamento (Area)                   Edificio
Puesto (cargo)                          └── Sector (piso / zona)
Personal ──┬─ departamento                └── Espacio físico
           └─ espacio fijo (opcional)           (escritorio, sala, almacén…)
```

---

## 2. Nombres en pantalla vs modelos

| En la interfaz | Modelo / código | Significado |
|----------------|-----------------|-------------|
| Departamento | `Area` | Unidad organizativa (RH, Contabilidad, TI…) |
| Puesto | `Puesto` | Cargo laboral |
| Personal | `Personal` | Empleado / custodio |
| Edificio | `Edificio` | Sede o bodega |
| Sector | `ZonaEdificio` | Piso, ala, área dentro del edificio |
| Espacio físico | `Ubicacion` | Punto concreto (escritorio, sala, rack…) |
| Almacén / stock | `Ubicacion.es_stock_default` | Espacio al que regresan los equipos en stock |

Las URLs internas (`/Areas/`, `/ZonaEdificios/`, etc.) pueden conservar el nombre técnico; la UI usa los nombres de la tabla.

---

## 3. Organización

### 3.1 Menú

```
Organización
  ├── Departamentos
  ├── Puestos
  └── Personal
```

### 3.2 Departamentos

Catálogo de áreas organizativas. Se usan en:

- Ficha de personal
- Tickets / solicitudes (campo departamento del solicitante)
- Herencia al **asignar un equipo** (el equipo toma el departamento del custodio)

### 3.3 Puestos

Cargos laborales (Analista, Técnico, etc.). **No** representan un lugar físico.

### 3.4 Personal

Cada persona puede tener:

| Campo | Obligatorio | Notas |
|-------|-------------|-------|
| Departamento | No | Recomendable para reportes y herencia al asignar |
| Puesto | No | Cargo |
| Espacio físico | No | Puesto fijo (escritorio). Vacío = **sin puesto fijo** |

**Sin puesto fijo** significa que la persona no tiene escritorio asignado (móvil, remoto, campo). En ese caso, al asignarle un equipo **no** se copia un espacio y **no** se dispara la alerta de “sin espacio físico”.

---

## 4. Mapa de sedes

### 4.1 Acceso

Menú: **Espacios físicos → Mapa de sedes**  
URL: `/Espacios-fisicos/`

Las rutas antiguas (`/Edificios/`, `/ZonaEdificios/`, `/Ubicacion/`) redirigen al mapa o se usan como formularios internos.

### 4.2 Jerarquía

```
Edificio          →  Torre Central
  └── Sector      →  Piso 3
        └── Espacio físico  →  Escritorio 12
```

Un **espacio físico** es la referencia del lugar concreto: escritorio, sala de juntas, rack, ventana, mueble, almacén, etc. No es un departamento.

### 4.3 Pantalla (árbol + panel)

| Lado | Contenido |
|------|-----------|
| **Izquierda** | Árbol: edificios → sectores → espacios. Botón **+** para agregar hijo |
| **Derecha** | Detalle y acciones del elemento seleccionado |

Guía visual en la parte superior:

1. Edificio → 2. Sector → 3. Espacio físico → Stock (almacén)

### 4.4 Cómo crear la estructura

#### A) Primera vez (mapa vacío)

Formulario de bienvenida / plantilla:

1. Nombre del edificio o sede  
2. Sectores (uno por línea), ej. `Piso 1`, `Piso 2`  
3. Espacios opcionales (uno por línea) o cantidad automática  
4. Opciones: incluir sector **Almacen** y marcar **stock por defecto**

#### B) Plantilla rápida (ya hay sedes)

Misma lógica, desde el botón **Plantilla rápida**.

#### C) Paso a paso en el mapa

| Acción | Cómo |
|--------|------|
| Nuevo edificio | Botón o modal |
| Nuevo sector | **+** junto al edificio, o “Nuevo sector” en el panel |
| Agregar espacios | **+** junto al sector, o “Agregar espacios” |

#### D) Agregar espacios (alta masiva)

Se escribe **un nombre por línea**; cada línea crea un espacio físico.

```
Escritorio 1
Escritorio 2
Sala juntas A
Stock principal
```

Opcional: marcar el **primero** de la lista como almacén / stock por defecto.(Sera registrado como el almacen)

---

## 5. Almacén / stock por defecto

### 5.1 Qué es

Un espacio físico marcado como **stock** (`es_stock_default`). Solo puede haber **uno** activo a la vez.

Sirve como lugar de los equipos **En Stock** (sin custodio): almacén IT, bodega, rack de recepción, etc.

### 5.2 Cómo marcarlo

1. Abrir el espacio en el mapa  
2. Pulsar **Usar como stock**  

O crearlo con la plantilla / alta masiva y activar la casilla correspondiente.

El mapa muestra una tarjeta: **Almacén listo** o **Falta almacén de stock**.

### 5.3 Comportamiento en inventario

| Momento | Qué pasa |
|---------|----------|
| **Alta de equipo** | Se preselecciona el espacio de stock (si existe) |
| **Asignar a personal** | El equipo toma departamento del personal; y su espacio fijo **solo si** tiene uno |
| **Devolver a stock** | Se limpia el departamento del equipo y se mueve al **almacén por defecto** |
| **Personal sin puesto fijo** | El equipo asignado puede quedar sin espacio; **no** entra en la alerta “Sin espacio físico” |

---

## 6. Relación con inventario (resumen)

```
Personal (departamento + espacio opcional)
        │
        │  al asignar
        ▼
Equipo  (departamento heredado + espacio heredado o almacén)
        │
        │  al devolver
        ▼
Equipo En Stock  →  espacio = almacén / stock por defecto
```

| Situación | Alerta “Sin espacio físico” |
|-----------|----------------------------|
| En stock, sin ubicación y sin almacén configurado / vacío | Sí (dato incompleto) |
| En stock, en el almacén | No |
| Asignado, persona **con** espacio fijo, equipo sin él | Sí |
| Asignado, persona **sin** puesto fijo | **No** |

---

## 7. Flujos rápidos para el usuario

### Armar una sede nueva

1. Ir a **Mapa de sedes**  
2. Usar bienvenida o **Plantilla rápida**  
3. Confirmar que hay un espacio con etiqueta **Stock**  
4. (Opcional) Completar escritorios con **Agregar espacios**

### Dar de alta un equipo en almacén

1. Configurar stock en el mapa  
2. Crear equipo → el espacio físico debería salir en el almacén  
3. Estado **En Stock**, sin asignación

### Asignar a un empleado

1. En Personal, definir departamento y, si aplica, espacio fijo  
2. En Inventario → Asignar  
3. El equipo hereda departamento (y espacio si el empleado tiene puesto fijo)

### Devolver equipo

1. Devolver desde la ficha del equipo  
2. El equipo vuelve a **En Stock** en el almacén por defecto

---

## 8. Archivos relevantes

| Área | Ruta |
|------|------|
| Modelos | `GestorApp/models.py` (`Area`, `Personal`, `Edificio`, `ZonaEdificio`, `Ubicacion`, `Equipo`) |
| Mapa / CRUD espacios | `GestorApp/views/ubicaciones.py` |
| Herencia asignación / devolución | `GestorApp/views/helpers.py` |
| Asignar / devolver equipo | `GestorApp/views/equipo.py`, `GestorApp/views/asignacion.py` |
| Plantilla mapa | `GestorApp/Templates/espacios/mapa_sedes.html` |
| Menú | `GestorApp/Templates/base.html` |
| Migraciones | `0046_personal_ubicacion_equipo_area`, `0047_ubicacion_es_stock_default` |

---

## 9. Checklist operativo

- [ ] Existe al menos un edificio con sectores y espacios  
- [ ] Hay un espacio marcado como **stock por defecto**  
- [ ] El personal tiene departamento cuando se va a asignar equipo  
- [ ] Quien tiene escritorio fijo tiene **espacio físico** en su ficha  
- [ ] Quien es móvil / remoto deja el espacio vacío (sin puesto fijo)
