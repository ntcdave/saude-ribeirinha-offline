// TODO(equipe-dia): [PESSOA-UI] adicionar gravacao de voz (MediaRecorder) e enviar p/ /api/stt.
// TODO(equipe-dia): [PESSOA-UI] renderizar fontes como links clicaveis.
const chat = document.getElementById("chat");
const form = document.getElementById("form");
const q = document.getElementById("q");

function add(text, cls, fontes) {
  const d = document.createElement("div");
  d.className = "msg " + (cls || "");
  d.textContent = text;
  if (fontes && fontes.length) {
    const s = document.createElement("small");
    s.textContent = "Fontes: " + fontes.map(f => f.source).join(", ");
    d.appendChild(s);
  }
  chat.appendChild(d);
  chat.scrollTop = chat.scrollHeight;
}

add("Ola! Sou o assistente offline. Pergunte sobre saude basica ou primeiros socorros.", "");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const pergunta = q.value.trim();
  if (!pergunta) return;
  add(pergunta, "user");
  q.value = "";
  add("Buscando nos documentos locais...", "");
  try {
    const r = await fetch("/api/ask", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({pergunta})
    });
    const data = await r.json();
    chat.lastChild.remove();
    add(data.resposta + "\n(modo: " + data.modo + ")", "", data.fontes);
  } catch (err) {
    chat.lastChild.remove();
    add("Erro: backend desligado? Rode scripts/run-dev.ps1", "");
  }
});
