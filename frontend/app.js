// SPA Stitch 1:1 + backend /api/ask
const live = document.getElementById("chat-live");
const form = document.getElementById("form");
const q = document.getElementById("q");

function go(name){
  if(!["inicio","chat","guias","emergencia"].includes(name)) name="inicio";
  document.querySelectorAll(".view").forEach(v=>v.classList.remove("active"));
  const el = document.getElementById("view-"+name);
  if(el) el.classList.add("active");
  document.querySelectorAll(".tabbtn").forEach(a=>{
    const on = a.dataset.go===name;
    a.classList.toggle("bg-primary-container", on && name!=="emergencia");
    a.classList.toggle("text-white", on && name!=="emergencia");
  });
  if(location.hash!=="#"+name) history.replaceState(null,"","#"+name);
  window.scrollTo({top:0});
}
document.querySelectorAll("[data-go]").forEach(a=>{
  a.addEventListener("click",e=>{e.preventDefault();go(a.dataset.go);});
});
window.addEventListener("hashchange",()=>go(location.hash.replace("#","")));

// ---- Voz natural pt-BR: limpa texto + escolhe melhor voz + seletor ----
function cleanForSpeech(t){
  return String(t||"")
    .replace(/\(modo:[^)]*\)/gi,"")
    .replace(/\[fonte:[^\]]*\]/gi,"")
    .replace(/https?:\S+/gi,"")
    .replace(/[*_#>`]/g,"")
    .replace(/^\s*[-•]\s*/gm,"")
    .replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{2B00}-\u{2BFF}]/gu,"")
    .replace(/([.,;:!?])\s+(?=[.,;:!?])/g,"$1")
    .replace(/([.,;:!?])\1+/g,"$1")
    .replace(/\s*([.,;:!?])\s*/g,"$1 ")
    .replace(/\s+/g," ")
    .trim();
}
function pickBestVoice(){
  try{
    const vs=speechSynthesis.getVoices()||[];
    if(!vs.length) return null;
    const saved=localStorage.getItem("voz_id");
    if(saved){ const f=vs.find(v=>(v.voiceURI||v.name)===saved); if(f) return f; }
    const br=vs.filter(v=>(v.lang||"").toLowerCase().startsWith("pt-br"));
    const pt=vs.filter(v=>(v.lang||"").toLowerCase().startsWith("pt"));
    const pool=br.length?br:(pt.length?pt:vs);
    const prefer=/google|natural|neural|maria|daniel|francisca|antonio|heloisa|camila|vitoria|yara/i;
    return pool.find(v=>prefer.test(v.name))||pool[0];
  }catch(e){ return null; }
}
function speak(text, btn){
  try{
    if(btn && btn.dataset.speaking==="1"){ speechSynthesis.cancel(); btn.dataset.speaking=""; btn.textContent="🔊 Ouvir"; return; }
    speechSynthesis.cancel();
    const clean=cleanForSpeech(text);
    if(!clean) return;
    const parts=(clean.match(/[^.!?\n]+[.!?]+|[^.!?\n]+$/g)||[clean]).map(s=>s.trim()).filter(Boolean);
    const voice=pickBestVoice();
    let i=0;
    if(btn){ btn.dataset.speaking="1"; btn.textContent="⏹ Parar"; }
    const queue=()=>{
      if(i>=parts.length){ if(btn){btn.dataset.speaking="";btn.textContent="🔊 Ouvir";} return; }
      const u=new SpeechSynthesisUtterance(parts[i]);
      u.lang="pt-BR"; u.rate=1.02; u.pitch=1.0;
      if(voice) u.voice=voice;
      i++;
      u.onend=queue; u.onerror=queue;
      speechSynthesis.speak(u);
    };
    queue();
  }catch(e){}
}
function mountVoiceBar(){
  try{
    if(document.getElementById("voiceSel")||!form||!form.parentNode) return;
    const bar=document.createElement("div");
    bar.style.cssText="display:flex;gap:8px;align-items:center;margin:4px 0 8px;font-size:13px;color:#3D5248";
    bar.innerHTML='<label for="voiceSel" style="font-weight:800">🎙 Voz:</label>';
    const sel=document.createElement("select");
    sel.id="voiceSel";
    sel.style.cssText="flex:1;min-height:44px;border:1.5px solid #c0c8c3;border-radius:10px;padding:6px 10px;font-size:14px;background:#fff";
    bar.appendChild(sel);
    form.parentNode.insertBefore(bar, form);
    const fill=()=>{
      try{
        const vs=speechSynthesis.getVoices()||[];
        const pts=vs.filter(v=>(v.lang||"").toLowerCase().startsWith("pt"));
        const list=pts.length?pts:vs.slice(0,12);
        sel.innerHTML="";
        list.forEach(v=>{
          const o=document.createElement("option");
          o.value=v.voiceURI||v.name;
          o.textContent=(v.name||"Voz")+" ("+(v.lang||"?")+")";
          sel.appendChild(o);
        });
        const best=pickBestVoice();
        if(best) sel.value=best.voiceURI||best.name;
      }catch(e){}
    };
    sel.addEventListener("change",()=>{ try{localStorage.setItem("voz_id",sel.value); speechSynthesis.cancel();}catch(e){} });
    if("onvoiceschanged" in speechSynthesis) speechSynthesis.onvoiceschanged=fill;
    fill(); setTimeout(fill, 800);
  }catch(e){}
}
mountVoiceBar();

function bubble(text, cls){
  // Bolha simples: SOMENTE msg do usuário ou status transitório. Resposta do modelo SEMPRE usa renderGuideCard.
  const d=document.createElement("div");
  d.className="msg-live "+(cls||"");
  d.textContent=text;
  live.appendChild(d);
  d.scrollIntoView({behavior:"smooth",block:"end"});
  return d;
}

// ---- Cartão padrão de resposta (único formato em todo o app, 1:1 com o print) ----
function cardSpeechText(card){
  const parts=[card.titulo+". "].concat((card.passos||[]).map(p=>((p.destaque||"")+". "+(p.texto||"")).trim()));
  return cleanForSpeech(parts.join(" "));
}
function saveGuide(card, btn){
  try{
    const arr=JSON.parse(localStorage.getItem("guias_salvos")||"[]");
    arr.push({titulo:card.titulo, passos:card.passos, fonte:card.fonte, em:new Date().toISOString()});
    localStorage.setItem("guias_salvos",JSON.stringify(arr));
    if(btn) btn.querySelector("span:last-child").textContent=" Salvo ✓";
  }catch(e){}
}
function renderGuideCard(card, modo){
  card = card || {};
  const titulo = String(card.titulo||"Orientações de Saúde");
  const icone = String(card.icone||"health_and_safety");
  const passos = Array.isArray(card.passos) && card.passos.length ? card.passos.slice(0,3) : [
    {destaque:"Procure ajuda presencial", texto:"Se piorar, vá à UBS ou ligue SAMU 192.", alerta:false}
  ];
  const fonte = String(card.fonte||"documentos locais");

  const sec=document.createElement("section");
  sec.className="flex items-start gap-2.5";

  const av=document.createElement("div");
  av.className="w-10 h-10 rounded-full bg-primary-container text-primary-fixed flex items-center justify-center flex-shrink-0 shadow-sm border border-primary-fixed-dim";
  const avI=document.createElement("span");
  avI.className="material-symbols-outlined text-[24px]";
  avI.textContent="health_and_safety";
  av.appendChild(avI);

  const box=document.createElement("div");
  box.className="flex-1 bg-surface-container-lowest p-4 rounded-2xl rounded-tl-sm border-2 border-outline-variant shadow-sm space-y-3.5";

  const head=document.createElement("div");
  head.className="flex items-center justify-between border-b border-surface-variant pb-2";
  const title=document.createElement("span");
  title.className="inline-flex items-center gap-1 text-primary font-headline-sm text-headline-sm font-bold";
  const tI=document.createElement("span");
  tI.className="material-symbols-outlined text-secondary text-[22px]";
  tI.textContent=icone;
  title.appendChild(tI);
  title.appendChild(document.createTextNode(" "+titulo));
  const badge=document.createElement("span");
  badge.className="bg-surface-container text-primary text-label-sm font-label-sm px-2 py-0.5 rounded-md font-bold";
  badge.textContent="Local";
  head.appendChild(title); head.appendChild(badge);

  const ol=document.createElement("ol");
  ol.className="space-y-3";
  passos.forEach((p,i)=>{
    const alerta=!!p.alerta || /^\s*n[ãa]o\b/i.test(String(p.destaque||""));
    const li=document.createElement("li");
    li.className="flex items-start gap-2.5";
    const n=document.createElement("span");
    n.className= alerta
      ? "w-6 h-6 rounded-full bg-error-container text-on-error-container font-bold text-label-sm font-label-sm flex items-center justify-center flex-shrink-0 mt-0.5"
      : "w-6 h-6 rounded-full bg-primary-container text-on-primary font-bold text-label-sm font-label-sm flex items-center justify-center flex-shrink-0 mt-0.5";
    n.textContent=String(i+1);
    const par=document.createElement("p");
    par.className="text-body-lg font-body-lg text-on-surface";
    const strong=document.createElement("strong");
    strong.className= alerta ? "text-error font-bold" : "text-primary font-bold";
    strong.textContent=String(p.destaque||"").trim();
    par.appendChild(strong);
    const resto=String(p.texto||"").trim();
    if(resto) par.appendChild(document.createTextNode(" "+resto));
    li.appendChild(n); li.appendChild(par); ol.appendChild(li);
  });

  const src=document.createElement("div");
  src.className="bg-surface-container-low p-2.5 rounded-xl border border-primary-fixed flex items-center gap-2";
  const srcI=document.createElement("span");
  srcI.className="material-symbols-outlined text-primary text-[20px]";
  srcI.textContent="menu_book";
  const srcT=document.createElement("span");
  srcT.className="text-label-sm font-label-sm text-primary font-bold";
  srcT.textContent="[Fonte: "+fonte+"]";
  src.appendChild(srcI); src.appendChild(srcT);

  const bar=document.createElement("div");
  bar.className="pt-2 border-t border-surface-variant flex items-center justify-between gap-2";
  const bHear=document.createElement("button");
  bHear.type="button";
  bHear.className="flex-1 flex items-center justify-center gap-1.5 bg-surface-container hover:bg-surface-container-high text-primary font-label-md text-label-md py-2.5 px-3 rounded-xl border border-outline-variant active:scale-95 transition-all min-h-[48px]";
  const bHearI=document.createElement("span");
  bHearI.className="material-symbols-outlined text-[22px] text-primary";
  bHearI.textContent="volume_up";
  const bHearT=document.createElement("span");
  bHearT.textContent="Ouvir áudio";
  bHear.appendChild(bHearI); bHear.appendChild(bHearT);
  bHear.onclick=()=>speak(cardSpeechText(card), bHearT);
  const bSave=document.createElement("a");
  bSave.className="flex items-center justify-center gap-1 bg-surface-container hover:bg-surface-container-high text-on-surface font-label-md text-label-md py-2.5 px-3 rounded-xl border border-outline-variant active:scale-95 transition-all min-h-[48px]";
  bSave.href="#guias";
  const bSaveI=document.createElement("span");
  bSaveI.className="material-symbols-outlined text-[20px]";
  bSaveI.textContent="bookmark_border";
  const bSaveT=document.createElement("span");
  bSaveT.textContent="Salvar guia";
  bSave.appendChild(bSaveI); bSave.appendChild(bSaveT);
  bSave.addEventListener("click",e=>{e.preventDefault();saveGuide(card,bSave);go("guias");});
  const bLike=document.createElement("button");
  bLike.type="button";
  bLike.setAttribute("aria-label","Resposta útil");
  bLike.className="w-12 h-12 flex items-center justify-center rounded-xl bg-surface-container hover:bg-surface-container-high text-primary border border-outline-variant active:scale-95 transition-all";
  const bLikeI=document.createElement("span");
  bLikeI.className="material-symbols-outlined text-[22px]";
  bLikeI.textContent="thumb_up";
  bLike.appendChild(bLikeI);
  bLike.onclick=()=>{bLikeI.textContent="thumb_up";bLike.classList.add("bg-primary-fixed");};
  bar.appendChild(bHear); bar.appendChild(bSave); bar.appendChild(bLike);

  box.appendChild(head); box.appendChild(ol); box.appendChild(src); box.appendChild(bar);
  if(modo){
    const m=document.createElement("div");
    m.style.cssText="text-align:center;font-size:11px;color:#717974";
    m.textContent="(modo: "+modo+") • Informação educativa — não substitui profissional. SAMU 192";
    box.appendChild(m);
  }
  sec.appendChild(av); sec.appendChild(box);
  live.appendChild(sec);
  sec.scrollIntoView({behavior:"smooth",block:"end"});
  return sec;
}

async function perguntar(p){
  bubble(p,"user");
  const l=bubble("Buscando nas cartilhas locais...","");
  try{
    const r=await fetch("/api/ask",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({pergunta:p})});
    const data=await r.json().catch(()=>null);
    l.remove();
    // Único formato de resposta: cartão padrão vindo do Gemma 4 (data.card).
    if(r.ok && data && data.card) renderGuideCard(data.card, data.modo);
    else if(data && data.detail) bubble("Não foi possível responder agora ("+data.detail+")","");
    else bubble("Não foi possível responder agora (erro "+r.status+"). Verifique se o Ollama está rodando com o modelo Gemma 4.","");
  }catch(e){
    l.remove();
    bubble("Erro: backend desligado? Rode scripts/run-dev.ps1 → http://localhost:8000","");
  }
}
if(form){
  form.addEventListener("submit",e=>{
    e.preventDefault();
    const v=q.value.trim();
    if(!v) return;
    q.value="";
    go("chat");
    perguntar(v);
  });
}
const mic=document.getElementById("micBtn");
if(mic) mic.addEventListener("click",()=>alert("Entrada de voz ainda indisponível neste aparelho."));

// Chips e cards do Stitch viram perguntas reais:
// Qualquer botão da view-chat com emoji ou texto de tópico dispara ask
document.querySelectorAll("#view-chat button").forEach(b=>{
  if(b.id==="micBtn"||b.type==="submit") return;
  const t=(b.textContent||"").toLowerCase();
  if(/queimadura|dengue|água|agua|cobra|febre|cloro/.test(t)){
    b.addEventListener("click",()=>{
      const map=[
        [/queimadura/,"O que fazer se alguém queimar a mão na brasa ou fogão a lenha?"],
        [/dengue|febre/,"Quais os sintomas de dengue e quando procurar ajuda?"],
        [/água|agua|cloro/,"Como deixar a água do rio potável com cloro?"],
        [/cobra/,"O que fazer em caso de picada de cobra?"]
      ];
      for(const [re,perg] of map){ if(re.test(t)){ perguntar(perg); break; } }
    });
  }
});
// Cards da view-guias clicáveis → chat
document.querySelectorAll("#view-guias article, #view-guias button, #view-guias a").forEach(el=>{
  el.style.cursor="pointer";
  el.addEventListener("click",()=>{
    const t=(el.textContent||"").toLowerCase();
    let p=null;
    if(t.includes("queimadura")) p="O que fazer se alguém queimar a mão na brasa ou fogão a lenha?";
    else if(t.includes("dengue")||t.includes("febre")) p="Quais os sintomas de dengue e quando procurar ajuda?";
    else if(t.includes("água")||t.includes("cloro")) p="Como deixar a água do rio potável com cloro?";
    else if(t.includes("cobra")) p="O que fazer em caso de picada de cobra?";
    if(p){ go("chat"); perguntar(p); }
  }, {capture:false});
});

bubble("Olá! Toque num tópico acima ou digite sua pergunta. Tudo offline, com fontes oficiais.","");
go(location.hash.replace("#","")||"inicio");
