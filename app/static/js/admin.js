const form = document.getElementById("uploadForm");
const statusEl = document.getElementById("status");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  statusEl.textContent = "Загрузка...";

  const formData = new FormData(form);
  const res = await fetch("/api/admin/buildings", {
    method: "POST",
    body: formData,
  });

  const data = await res.json();

  if (!res.ok) {
    statusEl.textContent = data.detail || "Ошибка при загрузке";
    statusEl.className = "status-error";
    return;
  }

  statusEl.textContent = `Готово: ${data.name}`;
  statusEl.className = "status-ok";
  form.reset();
});
