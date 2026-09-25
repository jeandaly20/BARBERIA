if (!getAccessToken()) {
  window.location.href = "/app/login/";
}

const ESTADO_LABEL = {
  pendiente_pago: { texto: "Pendiente de pago", color: "text-secondary" },
  confirmada: { texto: "Confirmada", color: "text-primary" },
  completada: { texto: "Completada", color: "text-on-surface-variant" },
  cancelada: { texto: "Cancelada", color: "text-error" },
  no_show: { texto: "No se presentó", color: "text-error" },
  expirada: { texto: "Expirada", color: "text-error" },
};

function money(n) {
  return `$${parseFloat(n).toFixed(2)}`;
}

async function cargarMisCitas() {
  const resp = await fetch(`${API_BASE}/citas/mias/`, {
    headers: { Authorization: `Bearer ${getAccessToken()}` },
  });
  if (resp.status === 401) {
    window.location.href = "/app/login/";
    return;
  }
  const citas = await resp.json();
  const container = document.getElementById("citas-list");

  if (citas.length === 0) {
    container.innerHTML = `<p class="font-body-sm text-body-sm text-on-surface-variant text-center py-space-lg">Todavía no tenés citas agendadas.</p>`;
    return;
  }

  container.innerHTML = citas
    .map((c) => {
      const estado = ESTADO_LABEL[c.estado] || { texto: c.estado, color: "text-on-surface-variant" };
      const puedeCancelar = ["pendiente_pago", "confirmada"].includes(c.estado);
      return `
        <div class="rounded-xl bg-surface-container p-space-md shadow-md space-y-2" data-id="${c.id}">
          <div class="flex items-center justify-between">
            <span class="font-label-lg text-label-lg text-on-surface font-semibold">${c.fecha} — ${c.hora_inicio.slice(0, 5)}</span>
            <span class="font-label-sm text-label-sm font-semibold ${estado.color}">${estado.texto}</span>
          </div>
          <div class="flex items-center justify-between text-on-surface-variant font-body-sm text-body-sm">
            <span>Total: <strong class="text-on-surface">${money(c.precio_total)}</strong></span>
            <span>Pagado online: <strong class="text-on-surface">${money(c.monto_a_pagar_online)}</strong></span>
          </div>
          ${puedeCancelar ? `<button class="btn-cancelar w-full h-10 rounded-lg bg-surface-container-high text-error font-label-md text-label-md font-semibold" data-id="${c.id}">Cancelar cita</button>` : ""}
        </div>`;
    })
    .join("");

  container.querySelectorAll(".btn-cancelar").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("¿Seguro que querés cancelar esta cita?")) return;
      await fetch(`${API_BASE}/citas/${btn.dataset.id}/cancelar/`, {
        method: "POST",
        headers: { Authorization: `Bearer ${getAccessToken()}` },
      });
      cargarMisCitas();
    });
  });
}

cargarMisCitas();
