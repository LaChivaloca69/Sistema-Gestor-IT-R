# Sistema-Gestor-IT-R
Proyecto sistema web gestor de it

El proyecto correspondiente tiene como objetivo generar un sistema gestor para el area de It en una fabrica. 
La idea principal es llevar un registro completo de todo el apartado del area IT y el gestor de ticktes, con la opcion de expandirse a futuro.

## Lenguajes y programas a utilizar etc
Lenguaje: Python
Base de datos: Postgresql with DjangoDB

## Principales caracteristicas
- CRUD para el inventario general
    - Alta y bajas etc.
- Entradas y salidas de equipos
    - Entradas y salidas de equipos 
    - Apoyar a la elaboracion de formatos 
- Manejo de mantenimiento
    - Registro de mantenimientos, calendarios y agendas proximas etc
- Registro de asignaciones de equipo al personal 
    - Llevar un regstro de asignacion de equipos.
Sistema de tickets 
    It
Gestor de ventas y presupuestos(Ayuda a generar el formato para)
    Ayuda a dar formato para los presupuestos y compras de materiales etc.

## Instalacion
Para instalar el sistema web es necesario 
Python, Postgresql y las dependencias correspondientes dentro del archivo requeriments.txt


### Git
Instalar git para copiar el repositorio Nota: puedes descargar el repositorio y ejecutarlo pero git hace mas comodo todo este proceso 
Copiar repo
Pasos para copiar el repositorio
`git clone https://github.com/LaChivaloca69/Sistema-Gestor-IT-R.git`


### Crear entorno o espacio de trabajo
``` cmd
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual (Linux/Mac)
source venv/bin/activate

# Activar entorno virtual (Windows)
venv\Scripts\activate

# Salir del entorno
deactive

```

Dependencias
```
# Guardar Dependencias
pip freeze > requirements.txt

# Descargar dependencias
pip install -r requeriments.txt

# Verificar instalacion
pip list


```

Django
```
# Instalacion Django dentro del entorno
pip install django
# Crear un proyecto
django-admin startproject nombre_projecto
# Activar servidor de desarrollo 
python manage.py runserver
# Crear una aplicacion dentro de la carpeta actual
python manage.py startapp nombre_app
# Creacion de super usuario
python manage.py createsuperuser
\\ El super usuario es solamente para el entorno de django recuerde administrar de manera correcta los usuarios en la Base de datos
#

#

#
```



