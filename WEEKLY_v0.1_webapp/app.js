const state={
  sources:[
    {name:"IGN",cat:"Gaming"},
    {name:"Eurogamer",cat:"Gaming"},
    {name:"The Verge",cat:"Technology"},
    {name:"Wired",cat:"Technology"},
    {name:"Ars Technica",cat:"Technology"},
    {name:"Rock Paper Shotgun",cat:"Gaming"}
  ],
  articles:[
    ["El nuevo hardware que quiere cambiar cómo jugamos","IGN","GAMES",94,true],
    ["La carrera por construir el ordenador personal definitivo","The Verge","TECH",91,true],
    ["Por qué los videojuegos están recuperando una estética perdida","Eurogamer","GAMES",89,true],
    ["Las revistas vuelven a ser objetos de diseño","Wired","CULTURE",84,false],
    ["La interfaz que nadie esperaba encontrar en 2026","Ars Technica","TECH",81,false],
    ["El diseño de sonido que está redefiniendo los videojuegos","Rock Paper Shotgun","GAMES",80,false]
  ],
  readerPage:0
};

const screens=["dashboard","sources","articles","magazine","reader","archive"];
const titles={dashboard:"Dashboard",sources:"My Sources",articles:"This Week",magazine:"Magazine",reader:"Reader",archive:"Archive"};

function $(s){return document.querySelector(s)}
function show(id){
  document.querySelectorAll(".screen").forEach(x=>x.classList.toggle("active",x.id===id));
  document.querySelectorAll(".nav-btn").forEach(x=>x.classList.toggle("active",x.dataset.screen===id));
  $("#screen-title").textContent=titles[id]||"Dashboard";
}
function renderSources(){
  const box=$("#source-grid"); box.innerHTML="";
  state.sources.forEach((s,i)=>{
    const el=document.createElement("div"); el.className="source";
    el.innerHTML='<span class="dot"></span><div><strong></strong><small></small></div><button class="remove">REMOVE</button>';
    el.querySelector("strong").textContent=s.name;
    el.querySelector("small").textContent=`${s.cat} · RSS`;
    el.querySelector(".remove").addEventListener("click",()=>{state.sources.splice(i,1);renderAll()});
    box.appendChild(el);
  });
  $("#source-count").textContent=`${state.sources.length} ACTIVE FEEDS`;
}
function renderArticles(){
  const box=$("#article-list"); box.innerHTML="";
  state.articles.forEach((a,i)=>{
    const label=document.createElement("label"); label.className="article";
    label.innerHTML='<input type="checkbox"><div><span class="cat"></span><h3></h3><p></p></div><span class="score"></span>';
    const c=label.querySelector("input"); c.checked=a[4];
    label.querySelector(".cat").textContent=a[2];
    label.querySelector("h3").textContent=a[0];
    label.querySelector("p").textContent=`${a[1]} · esta semana · ${Math.max(3,Math.round(a[3]/10))} fuentes relacionadas`;
    label.querySelector(".score").textContent=a[3];
    c.addEventListener("change",()=>{a[4]=c.checked;updateCounts()});
    box.appendChild(label);
  });
  updateCounts();
}
function updateCounts(){
  const n=state.articles.filter(a=>a[4]).length;
  $("#article-count").textContent=`${n} SELECTED · 126 FOUND`;
  $("#selected-stat").textContent=`${n} SELECTED`;
}
function renderMagazine(){
  const selected=state.articles.filter(a=>a[4]);
  $("#cover-dek").textContent=`${selected.length} stories seleccionadas · ${state.sources.length} fuentes · una edición construida automáticamente.`;
  const box=$("#cover-stories");box.innerHTML="";
  selected.slice(0,4).forEach(a=>{
    const el=document.createElement("div");el.className="mini";
    el.innerHTML='<b></b><h4></h4>';el.querySelector("b").textContent=a[2];el.querySelector("h4").textContent=a[0];box.appendChild(el);
  });
}
function renderReader(){
  const p=state.readerPage;
  const selected=state.articles.filter(a=>a[4]);
  const stories=selected.length?selected:state.articles;
  const left=stories[(p*2)%stories.length], right=stories[(p*2+1)%stories.length];
  $("#reader-page").textContent=`${String(p+1).padStart(2,"0")} / 04`;
  $("#reader-status").textContent=`SPREAD ${String(p+1).padStart(2,"0")} / 04`;
  $("#spread").innerHTML=`
    <section class="page">
      <div class="tag">${left[2]} · ${left[1]}</div>
      <h2>${escapeHtml(left[0])}</h2>
      <div class="feature"></div>
      <p>Una historia seleccionada para la edición semanal. En la versión conectada, aquí aparecerá el resumen generado a partir del artículo original y un enlace a la fuente.</p>
      <p><strong>SCORE ${left[3]}</strong> · Selección editorial WEEKLY.</p>
    </section>
    <section class="page">
      <div class="tag">${right[2]} · ${right[1]}</div>
      <div class="story"><h3>${escapeHtml(right[0])}</h3><p>El editor agrupa historias relacionadas, elimina duplicados y decide qué piezas merecen protagonismo.</p></div>
      <div class="story"><h3>THE EDITOR'S NOTE</h3><p>La revista no intenta competir con el flujo infinito de noticias. Su objetivo es convertir una semana de información en una edición que puedas terminar.</p></div>
      <div class="story"><h3>WHAT'S NEXT</h3><p>RSS real, imágenes de las fuentes, resúmenes, agrupación automática y generación semanal.</p></div>
    </section>`;
}
function escapeHtml(s){return s.replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]))}
function renderAll(){
  renderSources();renderArticles();renderMagazine();renderReader();
  $("#source-stat").textContent=`${state.sources.length} SOURCES`;
}
document.querySelectorAll(".nav-btn").forEach(b=>b.addEventListener("click",()=>show(b.dataset.screen)));
document.querySelectorAll("[data-go]").forEach(b=>b.addEventListener("click",()=>show(b.dataset.go)));
$("#add-source").addEventListener("click",()=>{
  const name=prompt("Nombre del medio o fuente:");
  if(!name?.trim())return;
  const cat=prompt("Categoría (Gaming / Technology / Culture / World):","Technology")||"Technology";
  state.sources.push({name:name.trim(),cat:cat.trim()});
  renderAll();
});
$("#generate").addEventListener("click",()=>{renderMagazine();show("magazine")});
$("#back-to-articles").addEventListener("click",()=>show("articles"));
$("#open-reader").addEventListener("click",()=>{state.readerPage=0;renderReader();show("reader")});
$("#close-reader").addEventListener("click",()=>show("magazine"));
$("#prev-page").addEventListener("click",()=>{state.readerPage=(state.readerPage+3)%4;renderReader()});
$("#next-page").addEventListener("click",()=>{state.readerPage=(state.readerPage+1)%4;renderReader()});
document.addEventListener("keydown",e=>{
  if(!$("#reader").classList.contains("active"))return;
  if(e.key==="ArrowLeft")$("#prev-page").click();
  if(e.key==="ArrowRight")$("#next-page").click();
});
const d=new Date();
$("#today").textContent=d.toLocaleDateString("es-CL",{day:"2-digit",month:"short",year:"numeric"}).toUpperCase();
$("#issue-date").textContent=d.toLocaleDateString("es-CL",{day:"2-digit",month:"short",year:"numeric"}).toUpperCase();
renderAll();