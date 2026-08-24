// Tiny UI helpers
document.addEventListener("DOMContentLoaded", () => {
  // Auto-dismiss flash messages after 4s
  document.querySelectorAll(".alert-dismissible").forEach((el) => {
    setTimeout(() => {
      try { bootstrap.Alert.getOrCreateInstance(el).close(); } catch(_) {}
    }, 4000);
  });
});
