# Barbería API

API REST (Django + Django REST Framework) para gestionar las reservas y cobros de una
barbería real, propiedad del autor. Es un proyecto de portafolio pensado para demostrar
lógica de negocio real (disponibilidad de horarios, depósitos, no-shows) bien probada con
tests automatizados, autenticación por JWT, e integración real de pagos con **PayPal**.

## Características

- **Autenticación JWT** (`djangorestframework-simplejwt`) con registro de clientes por email.
- **Catálogo** de servicios (corte clásico, corte fade, ...) y extras (diseño freestyle,
  cejas, barba), cada uno con su propio precio y duración.
- **Motor de disponibilidad** que respeta el horario real del negocio: lunes a domingo,
  cerrado los martes, 9:30 a.m.–7:00 p.m., con almuerzo bloqueado de 12:30 a 1:30 p.m.
- **Cobro real con PayPal** (Orders API v2): al reservar, el cliente paga de verdad (depósito
  o el servicio completo) antes de que la cita quede confirmada. Si no completa el pago en 15
  minutos, la reserva se libera automáticamente.
- **Calendario semanal** para el dueño (todas las citas por hora) y vista de "mis citas" para
  cada cliente (nunca ve el calendario completo del negocio).
- **Notificaciones por email**: confirmación al cliente y aviso al dueño al confirmarse el
  pago, recordatorio 10 minutos antes de la cita, y resumen diario de citas para el dueño.
- **Swagger / OpenAPI** en `/api/docs/`.

## Stack técnico

- Django 5 + Django REST Framework
- PostgreSQL (`dj-database-url`)
- JWT (`djangorestframework-simplejwt`)
- PayPal Orders API v2 (vía `requests`, sin SDK oficial — están deprecados)
- Base de datos en **Supabase** (Postgres administrado, free tier)
- Despliegue: Docker + Gunicorn + WhiteNoise en Render

## Instalación local

1. Crear un entorno virtual e instalar dependencias:

   ```bash
   python -m venv venv
   venv\Scripts\activate     # Windows
   source venv/bin/activate  # Mac/Linux
   pip install -r requirements.txt
   ```

2. Crear una base de datos PostgreSQL vacía (en local puede ser un Postgres propio; en
   producción se usa Supabase — ver más abajo).

3. Copiar `.env.example` a `.env` y completar tus propios valores (ver las secciones de
   Supabase y PayPal más abajo para la base de datos y las credenciales de pago).

4. Migrar y correr el servidor:

   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

5. Correr los tests (no requieren credenciales reales de PayPal — está todo mockeado):

   ```bash
   python manage.py test
   ```

## Configurar Supabase (base de datos en producción)

Se usa Supabase en vez de la base de datos gratuita de Render porque una cuenta de Render
solo permite una base PostgreSQL gratis por cuenta, y ya está ocupada por otro proyecto.

1. Crear una cuenta/proyecto en [supabase.com](https://supabase.com) (tiene free tier
   permanente).
2. En **Project Settings → Database → Connection string**, usar el connection string del
   **pooler** (host tipo `aws-0-<región>.pooler.supabase.com`), **no** el de "Direct
   connection" (`db.<proyecto>.supabase.co`): ese host solo resuelve a IPv6, así que en redes
   sin salida IPv6 —incluida la mayoría de PaaS, Render entre ellos— la conexión falla con
   "could not translate host name". Dentro de las opciones del pooler, usar el puerto **5432
   (session mode)** y no el 6543 (transaction mode): Django reutiliza conexiones persistentes
   (`conn_max_age`) y necesita el modo sesión para que eso funcione bien.
3. Cargar esos datos en las variables `DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT`/`DB_NAME`
   del `.env` (o como `DATABASE_URL` completo en Render), y `DB_SSL_REQUIRE=True` — a
   diferencia de una base interna de Render, Supabase se conecta por internet público y
   necesita SSL. Si el usuario o la contraseña tienen caracteres como `?`, `@` o `/`,
   `settings.py` ya los codifica automáticamente al armar la URL.
4. Correr `python manage.py migrate` contra esa base para crear las tablas.
5. **Nota**: para correr `python manage.py test` en el día a día, conviene usar un Postgres
   local en vez de Supabase — el pooler mantiene conexiones idle que chocan con el ciclo de
   crear/borrar la base de test en cada corrida. Supabase queda para verificar el despliegue
   real, no para la corrida de tests de todos los días (ver los comentarios en `.env.example`).

## Configurar login con Google

1. Ir a [console.cloud.google.com](https://console.cloud.google.com) → crear (o elegir) un
   proyecto → **APIs y servicios → Pantalla de consentimiento OAuth** (configurarla en modo
   "Externo", solo hace falta nombre de la app y correo de contacto).
2. **APIs y servicios → Credenciales → Crear credenciales → ID de cliente de OAuth**, tipo
   **Aplicación web**. En "Orígenes autorizados de JavaScript" agregar
   `http://127.0.0.1:8010` (o el puerto que uses en local) y, más adelante, la URL de Render
   en producción. No hace falta "URI de redirección" — este flujo no la usa.
3. Copiar el **Client ID** (el único dato que hace falta; no se usa el Client Secret porque el
   backend solo verifica el token que ya firmó Google, no hace el intercambio OAuth completo)
   a la variable `GOOGLE_CLIENT_ID` del `.env`.
4. Si la variable queda vacía, el botón de Google simplemente no se muestra en el login — el
   resto de la app funciona igual.

## Modo de pagos simulados (mientras el negocio no vende todavía)

Toda la integración de PayPal (abajo) está lista y probada, pero **no se usa por defecto**:
con `PAGOS_REALES_HABILITADOS=False` (el default), al crear una cita el sistema la confirma
al instante — como si ya estuviera pagada — y dispara los mismos emails de confirmación al
cliente y aviso al dueño, sin llamar a PayPal para nada. Esto permite mostrar/probar la app
completa de punta a punta sin estar realmente cobrando. Cuando el dueño esté listo para vender
de verdad, alcanza con poner `PAGOS_REALES_HABILITADOS=True` (y tener las credenciales de
PayPal cargadas, ver abajo) — no hace falta tocar código.

## Configurar PayPal (Sandbox primero, para cuando se active `PAGOS_REALES_HABILITADOS`)

1. Crear una cuenta en [developer.paypal.com](https://developer.paypal.com) y una app
   **Sandbox** desde el dashboard. Copiar el `Client ID` y el `Secret` a tu `.env`
   (`PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_MODE=sandbox`).
2. En el mismo dashboard, bajo la app, configurar un **Webhook** apuntando a
   `https://tu-servicio.onrender.com/api/pagos/webhook/` (o a una URL pública temporal en
   local, ej. con `ngrok`, si querés probar el webhook antes de desplegar) suscrito al evento
   `PAYMENT.CAPTURE.COMPLETED`. Copiar el `Webhook ID` a `PAYPAL_WEBHOOK_ID`.
3. Crear una cuenta de comprador de prueba (Sandbox) desde el mismo dashboard para poder
   pagar de mentira durante el desarrollo.
4. Cuando quieras cobrar de verdad: crear una app **Live** en PayPal (requiere una cuenta
   PayPal Business real), y cambiar en las variables de entorno de producción
   `PAYPAL_MODE=live` junto con el `Client ID`/`Secret`/`Webhook ID` de esa app Live. Este
   cambio lo hace el dueño del negocio cuando esté listo — no es algo que se automatice.

## Flujo de reserva y pago

1. El cliente se registra (`POST /api/auth/registro/`) e inicia sesión
   (`POST /api/auth/login/`) para obtener sus tokens JWT.
2. Consulta los horarios libres de un día para el servicio que quiere
   (`GET /api/disponibilidad/`).
3. Crea la cita (`POST /api/citas/`). La cita queda en `pendiente_pago` y la respuesta incluye
   `link_pago`: la URL de PayPal donde el cliente completa el cobro (depósito o completo,
   según `tipo_pago`).
4. El cliente paga en PayPal. Al volver, `GET /pagos/retorno/` confirma la cita
   (`estado=confirmada`) y dispara los emails de confirmación/aviso. Independientemente de
   eso, el webhook de PayPal (`POST /api/pagos/webhook/`) hace la misma confirmación de forma
   robusta por si el cliente cierra la pestaña antes de volver.
5. Si no paga dentro de 15 minutos, el comando `liberar_citas_expiradas` libera el horario.
6. Si eligió pagar solo el depósito, el saldo se cobra en físico y el dueño lo confirma con
   `POST /api/citas/<id>/confirmar-saldo/`.

## Endpoints principales

| Método y ruta | Descripción | Acceso |
|---|---|---|
| `POST /api/auth/registro/` | Registro de cliente | Público |
| `POST /api/auth/login/`, `/api/auth/refresh/` | JWT | Público |
| `GET /api/auth/mi-perfil/` | Perfil del usuario autenticado | Autenticado |
| `GET /api/servicios/`, `/api/extras/` | Catálogo | Público |
| `GET /api/disponibilidad/?fecha=&servicio=&extras=` | Horarios libres del día | Autenticado |
| `POST /api/citas/` | Crear reserva (devuelve `link_pago`) | Cliente |
| `GET /api/citas/mias/` | Mis citas | Cliente |
| `POST /api/citas/<id>/cancelar/` | Cancelar cita | Cliente dueño / Propietario |
| `GET /api/citas/semana/?desde=&hasta=` | Calendario semanal completo | Propietario |
| `POST /api/citas/<id>/marcar-completada/` | Marcar cita completada | Propietario |
| `POST /api/citas/<id>/marcar-no-show/` | Marcar no-show (pierde el depósito) | Propietario |
| `POST /api/citas/<id>/confirmar-saldo/` | Confirmar saldo pagado en físico | Propietario |
| `GET /pagos/retorno/`, `/pagos/cancelado/` | Retorno del navegador desde PayPal | Público |
| `POST /api/pagos/webhook/` | Webhook de PayPal | Público (firma verificada) |
| `GET /api/docs/` | Swagger UI | — |

## Comandos periódicos (Render Cron Jobs)

Estos tres comandos no configuran ningún cron por sí solos — están pensados para correr como
**Render Cron Jobs** (mismo repo/imagen, cambiando el "Start Command"), o cualquier
scheduler equivalente:

| Comando | Cadencia sugerida | Qué hace |
|---|---|---|
| `python manage.py liberar_citas_expiradas` | cada 5 min | Libera horarios de citas sin pagar a tiempo |
| `python manage.py enviar_recordatorios` | cada 5-10 min | Recuerda al cliente su cita de hoy |
| `python manage.py resumen_diario_propietario` | 1 vez al día (ej. `0 8 * * *`) | Le avisa al dueño cuántas citas tiene hoy |

Nota: los horarios de Render Cron corren en UTC — ajustar la hora según corresponda.

## Desplegar en Render

La base de datos vive en Supabase (ver arriba); Render solo aloja la app y los cron jobs.

1. Crear el proyecto en Supabase y copiar su connection string (ver sección anterior).
2. **New +** → **Web Service** en Render → conectar este repositorio de GitHub
   (Environment: Docker).
3. Configurar las variables de entorno: `SECRET_KEY` (una real, generada para producción —
   nunca la de desarrollo), `DEBUG=False`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`,
   `DATABASE_URL` (la de Supabase), `DB_SSL_REQUIRE=True`, `SITE_URL` (la URL pública del
   propio servicio, para los `return_url`/`cancel_url` de PayPal), variables `EMAIL_*`, las
   variables `PAYPAL_*` (Sandbox al inicio, Live cuando el dueño decida cobrar de verdad), y
   `GOOGLE_CLIENT_ID` (agregando la URL de Render a los orígenes autorizados en Google Cloud
   Console).
4. **New +** → **Cron Job** (uno por cada comando de la tabla anterior), misma imagen/repo,
   cambiando el comando de arranque, con las mismas variables de entorno que el Web Service.
5. Desplegar, y configurar en el dashboard de PayPal el webhook apuntando a
   `https://tu-servicio.onrender.com/api/pagos/webhook/`.

## Seguridad y datos sensibles

Esta app maneja datos reales de clientes (email, teléfono, historial de citas), así que:

- **Nunca se tocan números de tarjeta**: el cobro pasa siempre por la página de PayPal
  (redirect); esta API nunca recibe ni guarda datos de tarjetas.
- Contraseñas hasheadas con PBKDF2 (nativo de Django), nunca en texto plano.
- El webhook de PayPal verifica la firma (`pagos/paypal.py::verificar_webhook`) antes de
  confirmar cualquier pago — nadie puede fingir una cita pagada.
- Límite de intentos (`throttle_scope="auth"`, 10/min) en login y registro para frenar fuerza
  bruta.
- `SECRET_KEY`, credenciales de base de datos, de email y de PayPal viven solo en variables de
  entorno (`.env` en local, nunca commiteado — ver `.gitignore`; variables de entorno de Render
  en producción). El propio `settings.py` **rechaza arrancar** (`ImproperlyConfigured`) si
  `DEBUG=False` y la `SECRET_KEY` sigue siendo la de desarrollo, para evitar desplegar por
  accidente sin haber puesto una real.
- En producción (`DEBUG=False`) se fuerza HTTPS, cookies de sesión/CSRF marcadas `Secure`, y
  HSTS — ver el bloque final de `config/settings.py`.
- Checklist antes de operar con clientes reales:
  - [ ] `SECRET_KEY` real y distinta a la de desarrollo, puesta como variable de entorno.
  - [ ] `DEBUG=False` en Render.
  - [ ] Contraseña fuerte y única para el usuario admin/propietario (`/admin/`).
  - [ ] Confirmar que Supabase tiene backups automáticos habilitados (revisar el plan
        contratado — perder las citas de los clientes sería peor que cualquier otra falla).
  - [ ] `PAYPAL_MODE=live` con credenciales reales solo cuando el dueño esté listo para cobrar
        de verdad (hasta entonces, Sandbox).

## Mejoras futuras (fuera de alcance del MVP)

- Recordatorios/avisos por WhatsApp o SMS (hoy solo van por email).
- Mover el envío de emails a una cola asíncrona (hoy es síncrono dentro del request; aceptable
  para el volumen de un solo negocio, pero no escalaría a muchos barberos).
- Soporte para más de un barbero (hoy el modelo asume un solo dueño/barbero).
