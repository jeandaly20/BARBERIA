let authMode = "login";

function switchAuthTab(mode) {
  authMode = mode;
  const tabLogin = document.getElementById("tabLogin");
  const tabRegister = document.getElementById("tabRegister");
  const submitLabel = document.getElementById("submitBtnLabel");
  const nombreField = document.getElementById("nombreField");
  const phoneField = document.getElementById("phoneField");

  const activeClasses = "flex-1 py-2.5 rounded-lg font-label-lg text-label-lg text-on-primary bg-primary shadow-sm transition-all duration-200 text-center";
  const inactiveClasses = "flex-1 py-2.5 rounded-lg font-label-lg text-label-lg text-on-surface-variant bg-transparent transition-all duration-200 text-center hover:text-on-surface";

  if (mode === "login") {
    tabLogin.className = activeClasses;
    tabRegister.className = inactiveClasses;
    submitLabel.textContent = "Ingresar y Agendar Cita";
    nombreField.classList.add("hidden");
    nombreField.classList.remove("flex");
    phoneField.classList.add("hidden");
    phoneField.classList.remove("flex");
  } else {
    tabRegister.className = activeClasses;
    tabLogin.className = inactiveClasses;
    submitLabel.textContent = "Crear Cuenta Atelier";
    nombreField.classList.remove("hidden");
    nombreField.classList.add("flex");
    phoneField.classList.remove("hidden");
    phoneField.classList.add("flex");
  }
}

function mostrarFormularioRecuperar() {
  document.getElementById("authSegment").classList.add("hidden");
  document.getElementById("authForm").classList.add("hidden");
  document.getElementById("recoverForm").classList.remove("hidden");
  document.getElementById("recoverForm").classList.add("flex");
  document.getElementById("recoverPaso1").classList.remove("hidden");
  document.getElementById("recoverPaso2").classList.add("hidden");
  document.getElementById("recoverPaso2").classList.remove("flex");
  document.getElementById("recoverInfo").classList.add("hidden");
  document.getElementById("recoverError").classList.add("hidden");
  document.getElementById("googleSection")?.classList.add("hidden");
}

function volverALogin() {
  document.getElementById("authSegment").classList.remove("hidden");
  document.getElementById("authForm").classList.remove("hidden");
  document.getElementById("recoverForm").classList.add("hidden");
  document.getElementById("recoverForm").classList.remove("flex");
  document.getElementById("googleSection")?.classList.remove("hidden");
  switchAuthTab("login");
}

document.getElementById("btnOlvideClave").addEventListener("click", mostrarFormularioRecuperar);
document.getElementById("btnVolverLogin").addEventListener("click", volverALogin);

document.getElementById("btnEnviarCodigo").addEventListener("click", async () => {
  const email = document.getElementById("recoverEmailInput").value.trim();
  const infoEl = document.getElementById("recoverInfo");
  const errorEl = document.getElementById("recoverError");
  errorEl.classList.add("hidden");

  if (!email) {
    errorEl.textContent = "Ingresá tu correo.";
    errorEl.classList.remove("hidden");
    return;
  }

  const btn = document.getElementById("btnEnviarCodigo");
  btn.disabled = true;
  try {
    const resp = await fetch(`${API_BASE}/auth/recuperar/solicitar/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "No se pudo enviar el código.");

    infoEl.textContent = "Si el correo está registrado, te enviamos un código. Revisá tu bandeja de entrada.";
    infoEl.classList.remove("hidden");
    document.getElementById("recoverPaso2").classList.remove("hidden");
    document.getElementById("recoverPaso2").classList.add("flex");
  } catch (err) {
    errorEl.textContent = err.message || "Ocurrió un error. Intenta de nuevo.";
    errorEl.classList.remove("hidden");
  } finally {
    btn.disabled = false;
  }
});

document.getElementById("btnCambiarClave").addEventListener("click", async () => {
  const email = document.getElementById("recoverEmailInput").value.trim();
  const codigo = document.getElementById("recoverCodigoInput").value.trim();
  const nueva_password = document.getElementById("recoverNuevaPassInput").value;
  const infoEl = document.getElementById("recoverInfo");
  const errorEl = document.getElementById("recoverError");
  errorEl.classList.add("hidden");

  const btn = document.getElementById("btnCambiarClave");
  btn.disabled = true;
  try {
    const resp = await fetch(`${API_BASE}/auth/recuperar/confirmar/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, codigo, nueva_password }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      const primerError = Object.values(data)[0];
      throw new Error(data.detail || (Array.isArray(primerError) ? primerError[0] : "Código inválido."));
    }

    infoEl.textContent = "¡Contraseña actualizada! Ya podés iniciar sesión.";
    infoEl.classList.remove("hidden");
    setTimeout(volverALogin, 1500);
  } catch (err) {
    errorEl.textContent = err.message || "Ocurrió un error. Intenta de nuevo.";
    errorEl.classList.remove("hidden");
  } finally {
    btn.disabled = false;
  }
});

function togglePassVisibility() {
  const passInput = document.getElementById("passInput");
  const toggleIcon = document.getElementById("passToggleIcon");
  if (passInput.type === "password") {
    passInput.type = "text";
    toggleIcon.textContent = "visibility";
  } else {
    passInput.type = "password";
    toggleIcon.textContent = "visibility_off";
  }
}

function mostrarError(mensaje) {
  const el = document.getElementById("authError");
  el.textContent = mensaje;
  el.classList.remove("hidden");
}

function ocultarError() {
  document.getElementById("authError").classList.add("hidden");
}

async function iniciarSesion(email, password) {
  const resp = await fetch(`${API_BASE}/auth/login/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await resp.json();
  if (!resp.ok) {
    throw new Error(data.detail || "Credenciales inválidas.");
  }
  setTokens({ access: data.access, refresh: data.refresh });
}

async function crearCuenta(email, nombre, telefono, password) {
  const resp = await fetch(`${API_BASE}/auth/registro/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, nombre, telefono, password }),
  });
  const data = await resp.json();
  if (!resp.ok) {
    const primerError = Object.values(data)[0];
    throw new Error(Array.isArray(primerError) ? primerError[0] : "No se pudo crear la cuenta.");
  }
}

document.getElementById("authForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  ocultarError();

  const email = document.getElementById("emailInput").value.trim();
  const password = document.getElementById("passInput").value;
  const nombre = document.getElementById("nombreInput").value.trim();
  const telefono = document.getElementById("phoneInput").value.trim();

  const submitBtn = document.getElementById("authSubmitBtn");
  submitBtn.disabled = true;

  try {
    if (authMode === "register") {
      await crearCuenta(email, nombre, telefono, password);
    }
    await iniciarSesion(email, password);
    window.location.href = "/app/servicios/";
  } catch (err) {
    mostrarError(err.message || "Ocurrió un error. Intenta de nuevo.");
  } finally {
    submitBtn.disabled = false;
  }
});

// --- Login con Google ---

async function handleGoogleCredential(response) {
  ocultarError();
  try {
    const resp = await fetch(`${API_BASE}/auth/google/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ credential: response.credential }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      throw new Error(data.detail || "No se pudo iniciar sesión con Google.");
    }
    setTokens({ access: data.access, refresh: data.refresh });
    window.location.href = "/app/servicios/";
  } catch (err) {
    mostrarError(err.message || "No se pudo iniciar sesión con Google.");
  }
}

// El script de Google llama a este callback global cuando termina de cargar.
window.onGoogleLibraryLoad = function () {
  const contenedor = document.getElementById("googleButtonContainer");
  if (!contenedor || !window.GOOGLE_CLIENT_ID) return;

  google.accounts.id.initialize({
    client_id: window.GOOGLE_CLIENT_ID,
    callback: handleGoogleCredential,
  });
  google.accounts.id.renderButton(contenedor, {
    theme: "outline",
    size: "large",
    shape: "pill",
    width: 328,
    text: "continue_with",
  });
};
