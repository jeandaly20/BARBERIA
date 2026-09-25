if (!getAccessToken()) {
  window.location.href = "/app/login/";
}

async function cargarPerfil() {
  const resp = await fetch(`${API_BASE}/auth/mi-perfil/`, {
    headers: { Authorization: `Bearer ${getAccessToken()}` },
  });
  if (resp.status === 401) {
    window.location.href = "/app/login/";
    return;
  }
  const data = await resp.json();
  document.getElementById("perfil-info").innerHTML = `
    <div class="flex items-center gap-space-sm">
      <div class="w-14 h-14 rounded-full bg-primary flex items-center justify-center shrink-0">
        <span class="material-symbols-outlined text-on-primary text-[28px]">person</span>
      </div>
      <div>
        <p class="font-headline-sm text-headline-sm text-on-surface font-semibold">${data.nombre || "Sin nombre"}</p>
        <p class="font-body-sm text-body-sm text-on-surface-variant">${data.email}</p>
      </div>
    </div>
    <div class="pt-space-sm border-t border-surface-variant/30 space-y-1">
      <p class="font-body-sm text-body-sm text-on-surface-variant">Teléfono: <span class="text-on-surface">${data.telefono || "—"}</span></p>
    </div>`;
}

document.getElementById("btn-logout").addEventListener("click", () => {
  clearTokens();
  window.location.href = "/app/login/";
});

cargarPerfil();
