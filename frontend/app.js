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

function bubble(text, cls, fontes){
  const d=document.createElement("div");
  d.className="msg-live "+(cls||"");
  d.textContent=text;
  if(fontes&&fontes.length){
    const s=document.createElement("small");
    s.textContent="Fontes: "+fontes.map(f=>f.source).join(", ");
    d.appendChild(s);
    const row=document.createElement("div");
    row.style.cssText="display:flex;gap:8px;margin-top:8px";
    const b1=document.createElement("button");
    b1.textContent="🔊 Ouvir";
    b1.style.cssText="border:1px solid #c0c8c3;border-radius:10px;min-height:44px;padding:8px 12px;font-weight:700;background:#F2F7F4";
    b1.onclick=()=>speak(text, b1);
    const b2=document.createElement("button");
    b2.textContent="🔖 Salvar";
    b2.style.cssText=b1.style.cssText;
    b2.onclick=()=>{
      const arr=JSON.parse(localStorage.getItem("guias_salvos")||"[]");
      arr.push({text:text.slice(0,300),em:new Date().toISOString()});
      localStorage.setItem("guias_salvos",JSON.stringify(arr));
      b2.textContent="✔ Salvo";
    };
    row.appendChild(b1);row.appendChild(b2);d.appendChild(row);
  }
  live.appendChild(d);
  d.scrollIntoView({behavior:"smooth",block:"end"});
  return d;
}

async function perguntar(p){
  bubble(p,"user");
  const l=bubble("Buscando nas cartilhas locais...","");
  try{
    const r=await fetch("/api/ask",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({pergunta:p})});
    const data=await r.json();
    l.remove();
    bubble(data.resposta+"\n(modo: "+data.modo+")","",data.fontes);
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
if(mic) mic.addEventListener("click",()=>alert("Voz offline em breve: TODO equipe-dia MediaRecorder → /api/stt"));

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
