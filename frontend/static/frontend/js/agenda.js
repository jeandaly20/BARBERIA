const DIA_CERRADO = 2; // getDay(): 0=domingo, 1=lunes, 2=martes...
const HORA_APERTURA_MIN = 9 * 60 + 30;
const HORA_CIERRE_MIN = 19 * 60;
const ALMUERZO_INICIO_MIN = 12 * 60 + 30;
const ALMUERZO_FIN_MIN = 13 * 60 + 30;
const INTERVALO_MIN = 15;

const seleccion = JSON.parse(sessionStorage.getItem("reserva_seleccion") || "null");
if (!seleccion) {
  window.location.href = "/app/servicios/";
}

let duracionTotalMin = 30;
let inicioSemana = lunesDeEstaSemana(new Date());
let fechaSeleccionada = null;
let horaSeleccionada = null;

function lunesDeEstaSemana(fecha) {
  const d = new Date(fecha);
  const dia = d.getDay();
  const diff = dia === 0 ? -6 : 1 - dia;
  d.setDate(d.getDate() + diff);
  d.setHours(0, 0, 0, 0);
  return d;
}

function formatoISO(fecha) {
  const y = fecha.getFullYear();
  const m = String(fecha.getMonth() + 1).padStart(2, "0");
  const d = String(fecha.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function minutosATexto12h(min) {
  let h = Math.floor(min / 60);
  const m = min % 60;
  const ampm = h >= 12 ? "PM" : "AM";
  h = h % 12 || 12;
  return `${h}:${String(m).padStart(2, "0")} ${ampm}`;
}

const NOMBRES_DIA = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];
const NOMBRES_MES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];

async function cargarDuracionSeleccion() {
  const [respServicios, respExtras] = await Promise.all([
    fetch(`${API_BASE}/servicios/`),
    fetch(`${API_BASE}/extras/`),
  ]);
  const servicios = await respServicios.json();
  const extras = await respExtras.json();
  const servicio = servicios.find((s) => s.id === seleccion.servicio_id);
  const extrasSel = extras.filter((e) => seleccion.extra_ids.includes(e.id));
  duracionTotalMin = (servicio ? servicio.duracion_minutos : 30) + extrasSel.reduce((sum, e) => sum + e.duracion_minutos, 0);
}

function renderWeekChips() {
  const container = document.getElementById("day-chips");
  const dias = [];
  for (let i = 0; i < 7; i++) {
    const d = new Date(inicioSemana);
    d.setDate(d.getDate() + i);
    dias.push(d);
  }

  const primero = dias[0];
  const ultimo = dias[6];
  document.getElementById("week-range-label").textContent =
    `${primero.getDate()} ${NOMBRES_MES[primero.getMonth()]} — ${ultimo.getDate()} ${NOMBRES_MES[ultimo.getMonth()]}, ${ultimo.getFullYear()}`;

  container.innerHTML = dias
    .map((d) => {
      const cerrado = d.getDay() === DIA_CERRADO;
      const iso = formatoISO(d);
      const activo = fechaSeleccionada === iso;
      let classes = "day-chip flex-shrink-0 w-[58px] py-3 rounded-xl flex flex-col items-center justify-center transition-all snap-start ";
      if (cerrado) {
        classes += "bg-surface-container-lowest/60 text-on-surface-variant/40 opacity-70";
      } else if (activo) {
        classes += "bg-primary-container text-on-primary-container shadow-[0_0_16px_rgba(245,158,11,0.25)]";
      } else {
        classes += "bg-surface-container text-on-surface-variant";
      }
      return `
        <button class="${classes}" data-date="${iso}" data-closed="${cerrado}">
          <span class="font-label-sm text-label-sm uppercase ${cerrado ? "line-through" : ""}">${NOMBRES_DIA[d.getDay()]}</span>
          <span class="font-headline-sm text-headline-sm mt-0.5">${d.getDate()}</span>
          ${cerrado ? '<span class="font-label-sm text-[9px] text-error mt-0.5 leading-none font-semibold">Cerrado</span>' : '<span class="w-1.5 h-1.5 rounded-full bg-primary/60 mt-1"></span>'}
        </button>`;
    })
    .join("");

  container.querySelectorAll(".day-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      if (chip.dataset.closed === "true") {
        fechaSeleccionada = null;
        document.getElementById("schedule-container").classList.add("hidden");
        document.getElementById("rest-day-banner").classList.remove("hidden");
        actualizarResumenTurno();
        renderWeekChips();
        return;
      }
      fechaSeleccionada = chip.dataset.date;
      horaSeleccionada = null;
      document.getElementById("schedule-container").classList.remove("hidden");
      document.getElementById("rest-day-banner").classList.add("hidden");
      renderWeekChips();
      cargarDisponibilidad();
    });
  });
}

async function cargarDisponibilidad() {
  const params = new URLSearchParams({ fecha: fechaSeleccionada, servicio: seleccion.servicio_id });
  if (seleccion.extra_ids.length) params.set("extras", seleccion.extra_ids.join(","));

  const resp = await fetch(`${API_BASE}/disponibilidad/?${params.toString()}`, {
    headers: { Authorization: `Bearer ${getAccessToken()}` },
  });
  if (resp.status === 401) {
    window.location.href = "/app/login/";
    return;
  }
  const data = await resp.json();
  const disponibles = new Set(data.horarios_disponibles.map((h) => h.slice(0, 5)));

  renderSlots("slots-manana", HORA_APERTURA_MIN, ALMUERZO_INICIO_MIN, disponibles);
  renderSlots("slots-tarde", ALMUERZO_FIN_MIN, HORA_CIERRE_MIN, disponibles);
  actualizarResumenTurno();
}

function renderSlots(containerId, desdeMin, hastaMin, disponibles) {
  const container = document.getElementById(containerId);
  const slots = [];
  for (let min = desdeMin; min + duracionTotalMin <= hastaMin; min += INTERVALO_MIN) {
    const hh = String(Math.floor(min / 60)).padStart(2, "0");
    const mm = String(min % 60).padStart(2, "0");
    const hora24 = `${hh}:${mm}`;
    slots.push({ hora24, disponible: disponibles.has(hora24) });
  }

  container.innerHTML = slots
    .map((s) => {
      if (!s.disponible) {
        return `
          <button class="h-14 rounded-xl bg-surface-container-lowest/50 flex flex-col items-center justify-center text-on-surface-variant/35 cursor-not-allowed" disabled>
            <span class="font-time-slot text-time-slot font-medium line-through">${minutosATexto12h(horaAMinutos(s.hora24))}</span>
            <span class="font-label-sm text-[10px] text-on-surface-variant/40">Ocupado</span>
          </button>`;
      }
      const activo = horaSeleccionada === s.hora24;
      const classes = activo
        ? "time-slot-btn selected-slot h-14 rounded-xl bg-primary-container text-on-primary-container shadow-[0_0_18px_rgba(245,158,11,0.35)] flex flex-col items-center justify-center transition-all active:scale-95"
        : "time-slot-btn h-14 rounded-xl bg-surface-container flex flex-col items-center justify-center text-on-surface transition-all active:scale-95 shadow-sm";
      return `
        <button class="${classes}" data-time="${s.hora24}">
          <span class="font-time-slot text-time-slot font-medium">${minutosATexto12h(horaAMinutos(s.hora24))}</span>
          <span class="font-label-sm text-[10px] ${activo ? "font-bold uppercase tracking-wide" : "text-primary"}">${activo ? "Seleccionado" : "Disponible"}</span>
        </button>`;
    })
    .join("");

  container.querySelectorAll(".time-slot-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      horaSeleccionada = btn.dataset.time;
      cargarDisponibilidad();
    });
  });
}

function horaAMinutos(hora24) {
  const [h, m] = hora24.split(":").map(Number);
  return h * 60 + m;
}

function actualizarResumenTurno() {
  const bookBtn = document.getElementById("book-btn");
  const summary = document.getElementById("appointment-summary");
  if (fechaSeleccionada && horaSeleccionada) {
    const [y, m, d] = fechaSeleccionada.split("-").map(Number);
    const fechaObj = new Date(y, m - 1, d);
    summary.textContent = `${NOMBRES_DIA[fechaObj.getDay()]} ${d} ${NOMBRES_MES[m - 1]} — ${minutosATexto12h(horaAMinutos(horaSeleccionada))}`;
    bookBtn.disabled = false;
  } else {
    summary.textContent = "Elegí día y hora";
    bookBtn.disabled = true;
  }
}

document.getElementById("prev-week-btn").addEventListener("click", () => {
  inicioSemana.setDate(inicioSemana.getDate() - 7);
  renderWeekChips();
});
document.getElementById("next-week-btn").addEventListener("click", () => {
  inicioSemana.setDate(inicioSemana.getDate() + 7);
  renderWeekChips();
});

document.getElementById("book-btn").addEventListener("click", () => {
  if (!fechaSeleccionada || !horaSeleccionada) return;
  sessionStorage.setItem(
    "reserva_fecha_hora",
    JSON.stringify({ fecha: fechaSeleccionada, hora_inicio: `${horaSeleccionada}:00` })
  );
  window.location.href = "/app/pago/";
});

(async function init() {
  await cargarDuracionSeleccion();
  renderWeekChips();
})();
