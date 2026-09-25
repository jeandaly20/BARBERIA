let servicios = [];
let extras = [];
let servicioSeleccionado = null;
let extrasSeleccionados = [];

function money(n) {
  return `$${n.toFixed(2)}`;
}

function calcularTotales() {
  if (!servicioSeleccionado) return { subtotal: 0, tarifaReserva: 1, total: 0, deposito: 0, saldo: 0 };
  const subtotalExtras = extrasSeleccionados.reduce((sum, e) => sum + parseFloat(e.precio), 0);
  const subtotal = parseFloat(servicioSeleccionado.precio) + subtotalExtras;
  const tarifaReserva = 1;
  const total = subtotal + tarifaReserva;
  const deposito = Math.round((total / 2) * 100) / 100;
  const saldo = Math.round((total - deposito) * 100) / 100;
  return { subtotal, subtotalExtras, tarifaReserva, total, deposito, saldo };
}

function renderServiceCards() {
  const container = document.getElementById("service-options");
  container.innerHTML = servicios
    .map((s) => {
      const activo = servicioSeleccionado && servicioSeleccionado.id === s.id;
      return `
        <div class="service-card relative rounded-xl p-4 bg-surface-container border-2 ${activo ? "border-primary" : "border-transparent hover:border-surface-variant"} cursor-pointer transition-all duration-200 select-none shadow-lg" data-id="${s.id}">
          <div class="flex items-start justify-between gap-3">
            <div class="flex items-start gap-3">
              <div class="radio-circle mt-0.5 w-5 h-5 rounded-full border-2 ${activo ? "border-primary" : "border-outline-variant"} flex items-center justify-center shrink-0">
                <div class="w-2.5 h-2.5 rounded-full ${activo ? "bg-primary" : "bg-transparent"}"></div>
              </div>
              <div class="space-y-1">
                <h3 class="font-headline-sm text-headline-sm text-on-surface font-semibold">${s.nombre}</h3>
                <div class="flex items-center gap-3 pt-1 text-on-surface-variant font-label-sm text-[11px]">
                  <span class="flex items-center gap-1"><span class="material-symbols-outlined text-[14px] text-primary">schedule</span>${s.duracion_minutos} min</span>
                </div>
              </div>
            </div>
            <div class="text-right shrink-0">
              <div class="font-price-xl text-[22px] ${activo ? "text-primary" : "text-on-surface"} font-bold">${s.precio_desde ? "desde " : ""}${money(parseFloat(s.precio))}</div>
              <div class="text-[11px] font-label-sm text-on-surface-variant">+$1 reserva</div>
            </div>
          </div>
        </div>`;
    })
    .join("");

  container.querySelectorAll(".service-card").forEach((card) => {
    card.addEventListener("click", () => {
      const id = parseInt(card.dataset.id, 10);
      servicioSeleccionado = servicios.find((s) => s.id === id);
      renderServiceCards();
      actualizarResumen();
    });
  });
}

function renderAddons() {
  const list = document.getElementById("addons-list");
  list.innerHTML = extras
    .map(
      (e) => `
      <label class="addon-item flex items-center justify-between p-3 rounded-lg bg-surface-container cursor-pointer select-none border border-transparent hover:border-surface-variant transition-all">
        <div class="flex items-center gap-3">
          <input class="addon-checkbox w-4 h-4 rounded accent-primary-container bg-surface-variant shrink-0" type="checkbox" data-id="${e.id}"/>
          <div class="space-y-0.5">
            <div class="font-label-md text-label-md text-on-surface font-medium">${e.nombre}</div>
            <div class="font-body-sm text-[11px] text-on-surface-variant">+${e.duracion_minutos} min</div>
          </div>
        </div>
        <div class="font-label-lg text-label-lg text-primary font-bold">+${money(parseFloat(e.precio))}</div>
      </label>`
    )
    .join("");

  list.querySelectorAll(".addon-checkbox").forEach((box) => {
    box.addEventListener("change", (e) => {
      const id = parseInt(e.target.dataset.id, 10);
      const extra = extras.find((x) => x.id === id);
      const parentLabel = e.target.closest(".addon-item");
      if (e.target.checked) {
        extrasSeleccionados.push(extra);
        parentLabel.classList.add("bg-surface-container-high");
      } else {
        extrasSeleccionados = extrasSeleccionados.filter((x) => x.id !== id);
        parentLabel.classList.remove("bg-surface-container-high");
      }
      actualizarResumen();
    });
  });
}

function actualizarResumen() {
  const t = calcularTotales();
  const countLabel = document.getElementById("addons-count-label");
  countLabel.textContent = `Personaliza tu turno (${extrasSeleccionados.length} seleccionados)`;

  document.getElementById("detail-service-name").textContent = servicioSeleccionado ? servicioSeleccionado.nombre : "—";
  document.getElementById("detail-service-price").textContent = servicioSeleccionado ? money(parseFloat(servicioSeleccionado.precio)) : money(0);

  const addonsRow = document.getElementById("detail-addons-row");
  if (extrasSeleccionados.length > 0) {
    addonsRow.classList.remove("hidden");
    document.getElementById("detail-addons-label").textContent = `Complementos (${extrasSeleccionados.length})`;
    document.getElementById("detail-addons-price").textContent = money(t.subtotalExtras || 0);
  } else {
    addonsRow.classList.add("hidden");
  }

  document.getElementById("detail-total-price").textContent = money(t.total);
  document.getElementById("detail-online-deposit").textContent = money(t.deposito);
  document.getElementById("detail-in-person").textContent = money(t.saldo);

  const nombreCorto = servicioSeleccionado ? servicioSeleccionado.nombre : "Elegí un servicio";
  document.getElementById("dock-service-name").textContent =
    extrasSeleccionados.length > 0 ? `${nombreCorto} + ${extrasSeleccionados.length} extra` : nombreCorto;
  document.getElementById("dock-total-cost").textContent = money(t.total);
  document.getElementById("dock-balance").textContent = money(t.saldo);
  document.getElementById("dock-deposit-amount").textContent = money(t.deposito);
}

async function cargarCatalogo() {
  const [respServicios, respExtras] = await Promise.all([
    fetch(`${API_BASE}/servicios/`),
    fetch(`${API_BASE}/extras/`),
  ]);
  servicios = await respServicios.json();
  extras = await respExtras.json();

  document.getElementById("services-loading").remove();
  servicioSeleccionado = servicios[0] || null;
  renderServiceCards();
  renderAddons();
  actualizarResumen();
}

document.getElementById("addons-toggle").addEventListener("click", () => {
  const list = document.getElementById("addons-list");
  const chevron = document.getElementById("addons-chevron");
  list.classList.toggle("hidden");
  chevron.style.transform = list.classList.contains("hidden") ? "rotate(0deg)" : "rotate(180deg)";
});

document.getElementById("btn-continue-booking").addEventListener("click", () => {
  if (!servicioSeleccionado) return;
  if (!getAccessToken()) {
    window.location.href = "/app/login/";
    return;
  }
  sessionStorage.setItem(
    "reserva_seleccion",
    JSON.stringify({
      servicio_id: servicioSeleccionado.id,
      extra_ids: extrasSeleccionados.map((e) => e.id),
    })
  );
  window.location.href = "/app/agenda/";
});

cargarCatalogo();
