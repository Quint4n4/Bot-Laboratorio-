# Comandos del Bot CAMSI — Asistente Personal

Guia rapida para explicar que hace cada comando del bot de Telegram.
Ademas de los comandos con `/`, el bot acepta **mensajes de texto y notas de voz** en lenguaje natural.

---

## Comandos disponibles

### `/start`
Inicia la conversacion con CAMSI. Crea tu perfil de usuario si es la primera vez y te da una bienvenida con ejemplos de uso. Es el unico comando obligatorio para empezar.

### `/ayuda`
Muestra el listado completo de comandos disponibles con un ejemplo rapido. Util como referencia rapida.

### `/agenda`
Muestra los eventos pendientes que tienes para **hoy**. Cada evento aparece como un mensaje individual con cuatro botones. Los botones cambian segun si el evento es one-shot o recurrente:

**Eventos one-shot** (puntuales):
- ✅ Marcar como completado
- ⏰+15 Posponer 15 minutos
- 📝 Editar (modo conversacional, ver mas abajo)
- ❌ Cancelar el evento

**Eventos recurrentes** (cada N min, cada lunes, etc.):
- ✅ Confirma la ocurrencia actual SIN matar la serie (sigue recordandote en el siguiente ciclo)
- ⏰+15 Posponer 15 minutos
- 📝 Editar
- 🛑 Serie — detiene la serie completa: CAMSI deja de recordarte para siempre

### `/semana`
Lista compacta de tus eventos pendientes de los **proximos 7 dias**, ordenados por fecha. Pensado para ver de un vistazo lo que viene.

### `/notas`
Muestra tus **notas guardadas** (las ultimas 10). Cada nota tiene dos botones:
- ✏️ Editar — modo conversacional para cambiar titulo, contenido o categoria
- ⏰ Recordar — programa un recordatorio sobre la nota a la hora que digas

> Las notas **no tienen boton de borrar en Telegram** (para evitar borrados
> accidentales). Para eliminar una nota: dile a CAMSI por voz o texto
> _"borra la nota del wifi"_, o entra al dashboard web y borra desde alli.

### `/voz`
Activa o desactiva las **respuestas de voz**. Cuando esta activado, CAMSI te contesta con un audio (mas un boton "Ver texto" para leer la transcripcion). Cuando esta desactivado, solo responde con texto.

### `/perfil`
Muestra tu configuracion actual (zona horaria, voz elegida, hora del briefing matutino y wrap-up nocturno) y te permite cambiar la **voz de CAMSI**. Hay 6 voces disponibles: Nova, Shimmer, Alloy, Echo, Fable y Onyx.

### `/sugerencias`
CAMSI analiza tu actividad de los ultimos 90 dias y te sugiere mejoras proactivas, por ejemplo:
- Eventos que has creado >=3 veces y podrian ser recurrentes
- Tareas pendientes desde hace mas de una semana
- Rachas de productividad (>=70% completado en la semana)

### `/dashboard`
Genera un enlace **firmado y unico para ti** al dashboard web (Streamlit). El link expira en 24 horas; si caduca, basta con pedir uno nuevo. En el dashboard puedes ver KPIs, agenda de hoy, completados, conversaciones y crear eventos desde el navegador.

### `/olvidar`
Borra el **historial conversacional** que CAMSI recuerda de ti (los ultimos mensajes que se usan como contexto para las respuestas). NO borra tus eventos ni tu agenda — solo la memoria de chat. Util si quieres empezar de cero o si CAMSI esta interpretando algo raro por contexto viejo.

### `/cancelar`
Sale del **modo edicion** de un evento. Si pulsaste "📝 Editar" en algun evento de tu agenda, este comando aborta el flujo sin hacer cambios.

---

## Sin comando: mensajes en lenguaje natural

CAMSI entiende texto libre y notas de voz. Puedes decirle directamente lo que quieres y ella usa IA para interpretarlo y ejecutar la accion correcta.

### Ejemplos de uso libre

**Eventos (agenda):**
- *"Recuerdame en 10 minutos tomar agua"* → recordatorio puntual
- *"Recuerdame cada 20 minutos tomar agua"* → recordatorio recurrente
- *"Agendame una junta el martes a las 3 PM en Sala 3"* → crea una cita
- *"Cada dia 7 del mes pagar internet"* → recordatorio mensual
- *"Todos los lunes y miercoles a las 9 hacer ejercicio"* → recordatorio semanal
- *"¿Que tengo para mañana?"* → consulta tu agenda
- *"Cancela mi cita del viernes"* → cancela un evento
- *"Reagenda la junta de las 3 para las 5"* → modifica un evento existente
- *"Marca como hecha la tarea de pagar internet"* → completa un evento

**Notas (informacion guardada):**
- *"Anota que el wifi de la oficina es CAMSA2024"* → guarda una nota
- *"Guarda esto: Pedro me debe 500 desde el viernes"* → guarda una nota
- *"¿Que notas tengo?"* → lista tus notas
- *"Busca mi nota del wifi"* → busca por palabras clave
- *"Notas de trabajo"* → filtra por categoria
- *"Recuerdame mi nota del wifi a las 5 PM"* → programa un recordatorio sobre una nota
- *"Borra la nota de Pedro"* → elimina una nota

**Caso especial — ambiguedad:**
Si dices *"recuerdame que [info]"* SIN especificar tiempo, CAMSI te preguntara
si quieres guardarlo como **nota** o como **recordatorio**. Si eliges
recordatorio, tendras que decir cuando.

### Notas de voz

Si mandas un audio en lugar de texto, CAMSI lo transcribe automaticamente con Whisper y lo procesa igual. Util cuando estas en movimiento.

### Modo edicion

Cuando pulsas "📝 Editar" en un evento de tu `/agenda`, CAMSI entra en modo edicion. En el siguiente mensaje, le dices en lenguaje natural que cambiar:
- *"cambia la hora a las 11 AM"*
- *"reagendalo para el viernes"*
- *"cambia el titulo a Junta semanal"*
- *"agregale ubicacion Sala 3"*

Para salir sin cambios, escribe `/cancelar`.

---

## Funcionalidades automaticas (sin comando)

CAMSI tambien hace cosas por su cuenta sin que tengas que pedirselas:

- **Recordatorios automaticos**: cuando llega la hora de un evento, te avisa. Los recordatorios traen botones para confirmar (✅), posponer 15 min (⏰) y, segun el tipo de evento, cancelar (❌) o detener la serie (🛑).
- **Follow-ups**: si no atiendes un recordatorio puntual, insiste cada minuto con mensajes diferentes (hasta 6 veces). Los eventos recurrentes no generan follow-ups: en su lugar, simplemente vuelven a recordarte en la siguiente vuelta de la serie.
- **Briefing matutino**: cada dia a la hora configurada en `/perfil` te manda un PDF con la agenda del dia y un saludo en audio.
- **Wrap-up nocturno**: a la hora configurada te manda un resumen del dia con completados y pendientes.
- **Eventos recurrentes**: si un evento tiene regla de recurrencia (`daily`, `weekly:MO`, `every:20m`, etc.) CAMSI lo reprograma automaticamente cada vez que se dispara.
