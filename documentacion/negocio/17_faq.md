# 17. Preguntas frecuentes

---

## Acceso

**No puedo crear una cuenta desde la pantalla de registro.**  
El registro publico esta desactivado por defecto. Debe solicitar el alta a un Administrador.

**Inicie sesion pero no veo inventarios ni mantenimientos.**  
Su rol es Usuario. Esas funciones son de Tecnico IT o Administrador.

---

## Equipos

**En Mis equipos no aparece nada.**  
No tiene asignacion activa, o su cuenta no esta vinculada a un registro de Personal.

**Quiero ver el detalle de un equipo y me redirige o niega el acceso.**  
Un Usuario solo consulta equipos asignados a su persona (o ligados a su solicitud). Un equipo ajeno no es visible.

**No puedo asignar el mismo equipo a dos personas a la vez.**  
Es una regla del sistema: solo una asignacion activa por equipo.

---

## Tickets

**No puedo editar mi ticket.**  
Solo se edita en Abierto y sin seguimientos. Si TI ya cargo un check, el contenido queda bajo el flujo de atencion.

**No puedo eliminar un ticket.**  
Solo el Administrador, y solo si no tiene seguimientos.

**Eliminar un comentario pide confirmacion.**  
Es el comportamiento esperado para evitar borrados accidentales.

---

## Compras y solicitudes

**Elabore una orden pero no puedo terminarla.**  
Terminar la orden es una accion de Tecnico IT o Administrador.

**No puedo cancelar mi solicitud de equipo.**  
Si ya fue completada o cerrada en un estado final, no se cancela.

---

## Mantenimiento y consumibles

**Cerro un mantenimiento que estaba Programado.**  
El sistema puede iniciar y completar en el mismo cierre, dejando el trabajo registrado.

**No veo Consumibles en el menu.**  
El modulo es operativo (Tecnico IT o Administrador).

---

## Avisos

**La campana sigue mostrando un conteo que ya resolvi.**  
Espere unos segundos o refresque. Los conteos usan cache breve.

**No recibo correos del sistema.**  
El sistema no envia correo; los avisos son dentro de la aplicacion.

---

## Administracion

**Borre a una persona del Personal y la cuenta sigue existiendo.**  
La cuenta se desactiva; no se elimina automaticamente el usuario de acceso.

**Un usuario tiene marca de personal de plataforma pero no es Administrador en la app.**  
En la aplicacion web el rol efectivo lo da el grupo de negocio (o el superusuario), no esa marca por si sola.
