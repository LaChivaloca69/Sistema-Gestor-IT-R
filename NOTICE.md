# Aviso del proyecto

## Origen

Este software (**Sistema Web para la gestion de inventario y Mesa de ayuda TI**)
fue desarrollado por **Alvarado Cardona Antonio** como proyecto de
**residencia profesional** del **Instituto Tecnologico de Tijuana**.

## Licencia del codigo propio

El codigo fuente y la documentacion propios de este repositorio se distribuyen
bajo la licencia **MIT**. Ver el archivo [`LICENSE`](LICENSE).

En resumen: puedes usar, copiar, modificar y distribuir este software, siempre
que conserves el aviso de copyright y el texto de la licencia. El software se
entrega "tal cual", sin garantia.

## Software de terceros

Este proyecto depende de librerias y herramientas de terceros listadas en
[`requirements.txt`](requirements.txt). Esas librerias **no** se rellicencian
con la MIT de este repositorio: cada una conserva su propia licencia y
copyright.

Dependencias principales (referencia; consulta el paquete oficial para el
texto completo de cada licencia):

| Paquete | Uso en el proyecto |
|---------|--------------------|
| Django, asgiref, sqlparse, tzdata, typing_extensions | Nucleo web |
| django-bootstrap5 | Interfaz |
| psycopg2-binary | Conexion a PostgreSQL |
| django-q2, django-picklefield | Trabajos en segundo plano |
| Pillow | Imagenes |
| docxtpl, python-docx, openpyxl, et_xmlfile, lxml, Jinja2, MarkupSafe, pypdf | Documentos / plantillas |
| waitress, whitenoise, python-dotenv | Despliegue y configuracion |

PostgreSQL y otras herramientas de entorno (servidor, sistema operativo, etc.)
tampoco forman parte de la licencia de este repositorio.

