const seleccion = JSON.parse(sessionStorage.getItem("reserva_seleccion") || "null");
const fechaHora = JSON.parse(sessionStorage.getItem("reserva_fecha_hora") || "null");
if (!seleccion || !fechaHora) {
  window.location.href = "/app/servicios/";
}
if (!getAccessToken()) {
  window.location.href = "/app/login/";
}

let tipoPago = "deposito";
let totales = { subtotal: 0, total: 0, deposito: 0, saldo: 0 };

function money(n) {
  return `$${n.toFixed(2)}`;
}

const NOMBRES_DIA = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];
const NOMBRES_MES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];

function formatearFechaHora() {
  const [y, m, d] = fechaHora.fecha.split("-").map(Number);
  const fechaObj = new Date(y, m - 1, d);
  const [hh, mm] = fechaHora.hora_inicio.split(":").map(Number);
  const ampm = hh >= 12 ? "PM" : "AM";
  const h12 = hh % 12 || 12;
  return `${NOMBRES_DIA[fechaObj.getDay()]} ${d} ${NOMBRES_MES[m - 1]}, ${h12}:${String(mm).padStart(2, "0")} ${ampm}`;
}

async function cargarResumen() {
  const [respServicios, respExtras] = await Promise.all([
    fetch(`${API_BASE}/servicios/`),
    fetch(`${API_BASE}/extras/`),
  ]);
  const servicios = await respServicios.json();
  const extras = await respExtras.json();
  const servicio = servicios.find((s) => s.id === seleccion.servicio_id);
  const extrasSel = extras.filter((e) => seleccion.extra_ids.includes(e.id));

  const duracion = (servicio ? servicio.duracion_minutos : 0) + extrasSel.reduce((sum, e) => sum + e.duracion_minutos, 0);
  const subtotal = (servicio ? parseFloat(servicio.precio) : 0) + extrasSel.reduce((sum, e) => sum + parseFloat(e.precio), 0);
  const total = subtotal + 1;
  const deposito = Math.round((total / 2) * 100) / 100;
  const saldo = Math.round((total - deposito) * 100) / 100;
  totales = { subtotal, total, deposito, saldo };

  document.getElementById("resumen-fecha-hora").textContent = formatearFechaHora();
  document.getElementById("resumen-duracion").textContent = `${duracion} min`;

  const items = [`
    <div class="flex justify-between items-center py-1">
      <span class="flex items-center gap-2 text-on-surface"><span class="material-symbols-outlined text-[16px] text-primary">content_cut</span>${servicio ? servicio.nombre : ""}</span>
      <span class="font-price-xl text-time-slot text-on-surface font-semibold">${money(servicio ? parseFloat(servicio.precio) : 0)}</span>
    </div>`];
  extrasSel.forEach((e) => {
    items.push(`
      <div class="flex justify-between items-center py-1">
        <span class="flex items-center gap-2 text-on-surface"><span class="material-symbols-outlined text-[16px] text-primary">add</span>${e.nombre}</span>
        <span class="font-price-xl text-time-slot text-on-surface font-semibold">${money(parseFloat(e.precio))}</span>
      </div>`);
  });
  items.push(`
    <div class="flex justify-between items-center py-1">
      <span class="flex items-center gap-2 text-on-surface"><span class="material-symbols-outlined text-[16px] text-primary">chair</span>Reserva exclusiva de espacio</span>
      <span class="font-price-xl text-time-slot text-on-surface font-semibold">$1.00</span>
    </div>
    <div class="h-px bg-surface-container-highest my-1"></div>
    <div class="flex justify-between items-center pt-1 text-on-surface font-semibold">
      <span class="font-label-lg text-label-lg">Total del Servicio</span>
      <span class="font-price-xl text-headline-sm text-primary tracking-tight">${money(total)}</span>
    </div>`);
  document.getElementById("resumen-items").innerHTML = items.join("");

  document.getElementById("precio-deposito").textContent = money(deposito);
  document.getElementById("precio-completo").textContent = money(total);
  document.getElementById("texto-saldo").textContent = money(saldo);

  actualizarModalidad();
}

function actualizarModalidad() {
  const cardDeposit = document.getElementById("card-deposit");
  const cardFull = document.getElementById("card-full");
  const radioDeposit = document.getElementById("radio-deposit");
  const radioFull = document.getElementById("radio-full");

  if (tipoPago === "deposito") {
    cardDeposit.className = "cursor-pointer rounded-xl bg-surface-container-high p-space-md shadow-md transition-all duration-200";
    radioDeposit.className = "mt-1 w-5 h-5 rounded-full bg-primary flex items-center justify-center shrink-0";
    radioDeposit.innerHTML = '<div class="w-2 h-2 rounded-full bg-on-primary"></div>';
    cardFull.className = "cursor-pointer rounded-xl bg-surface-container p-space-md shadow-md transition-all duration-200";
    radioFull.className = "mt-1 w-5 h-5 rounded-full bg-surface-container-highest flex items-center justify-center shrink-0";
    radioFull.innerHTML = '<div class="w-2 h-2 rounded-full bg-transparent"></div>';
    document.getElementById("displayAmount").textContent = `${money(totales.deposito)} USD`;
  } else {
    cardFull.className = "cursor-pointer rounded-xl bg-surface-container-high p-space-md shadow-md transition-all duration-200";
    radioFull.className = "mt-1 w-5 h-5 rounded-full bg-primary flex items-center justify-center shrink-0";
    radioFull.innerHTML = '<div class="w-2 h-2 rounded-full bg-on-primary"></div>';
    cardDeposit.className = "cursor-pointer rounded-xl bg-surface-container p-space-md shadow-md transition-all duration-200";
    radioDeposit.className = "mt-1 w-5 h-5 rounded-full bg-surface-container-highest flex items-center justify-center shrink-0";
    radioDeposit.innerHTML = '<div class="w-2 h-2 rounded-full bg-transparent"></div>';
    document.getElementById("displayAmount").textContent = `${money(totales.total)} USD`;
  }
}

document.getElementById("card-deposit").addEventListener("click", () => {
  tipoPago = "deposito";
  actualizarModalidad();
});
document.getElementById("card-full").addEventListener("click", () => {
  tipoPago = "completo";
  actualizarModalidad();
});

function mostrarError(mensaje) {
  const el = document.getElementById("pagoError");
  el.textContent = mensaje;
  el.classList.remove("hidden");
}

document.getElementById("btn-paypal").addEventListener("click", async () => {
  const btn = document.getElementById("btn-paypal");
  const label = document.getElementById("btn-paypal-label");
  btn.disabled = true;
  label.textContent = "Redirigiendo a PayPal…";
  document.getElementById("pagoError").classList.add("hidden");

  try {
    const resp = await fetch(`${API_BASE}/citas/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${getAccessToken()}`,
      },
      body: JSON.stringify({
        servicio: seleccion.servicio_id,
        extras: seleccion.extra_ids,
        fecha: fechaHora.fecha,
        hora_inicio: fechaHora.hora_inicio,
        tipo_pago: tipoPago,
      }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      const mensaje = Array.isArray(data) ? data[0] : data.detail || "No se pudo crear la reserva.";
      throw new Error(mensaje);
    }
    sessionStorage.removeItem("reserva_seleccion");
    sessionStorage.removeItem("reserva_fecha_hora");

    if (data.link_pago) {
      window.location.href = data.link_pago;
    } else {
      // Modo simulado: todavía no se cobra de verdad, la cita ya quedó confirmada.
      label.textContent = "¡Cita confirmada!";
      const infoEl = document.getElementById("pagoError");
      infoEl.className = "mb-space-sm px-4 py-3 rounded-lg bg-primary/10 text-primary font-body-sm text-body-sm";
      infoEl.textContent = "Tu cita quedó confirmada. Te enviamos un correo con los detalles.";
      infoEl.classList.remove("hidden");
      setTimeout(() => { window.location.href = "/app/citas/"; }, 1800);
    }
  } catch (err) {
    mostrarError(err.message || "Ocurrió un error al iniciar el pago.");
    btn.disabled = false;
    label.textContent = "Pagar ahora";
  }
});

cargarResumen();
