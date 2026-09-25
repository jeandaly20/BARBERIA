// Configuración compartida por todas las páginas. La lógica real de fetch a cada endpoint
// (login, disponibilidad, citas, PayPal...) se agrega página por página en el siguiente paso.
const API_BASE = "/api";

function getAccessToken() {
  return localStorage.getItem("access_token");
}

function setTokens({ access, refresh }) {
  localStorage.setItem("access_token", access);
  if (refresh) localStorage.setItem("refresh_token", refresh);
}

function clearTokens() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}
