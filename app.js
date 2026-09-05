const state={sources:[],articles:[],selected:[],clusters:[],readerPage:0};
const titles={dashboard:"Dashboard",sources:"My Sources",articles:"This Week",magazine:"Magazine",reader:"Reader",archive:"Archive"};
const $=s=>document.querySelector(s);

function show(id){
 document.querySelectorAll(".screen").forEach(x=>x.classList.toggle("active",x.id===id));
 document.querySelectorAll(".nav-btn").forEach(x=>x.classList.toggle("active",x.dataset.screen===id));
 $("#screen-title").textContent=titles[id]||"Dashboard";
}
function escapeHtml(s){return String(s||"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]))}
function renderSources(){
 const box=$("#source-grid");box.innerHTML="";
 state.sources.forEach((s,i)=>{
  const el=document.createElement("div");el.className="source";
  el.innerHTML='<span class="dot"></span><div><strong></strong><small></small></div><button class="remove">REMOVE</button>';
  el.querySelector("strong").textContent=s.name;el.querySelector("small").textContent=`${s.category||"Other"} · RSS`;
  el.querySelector(".remove").onclick=()=>{state.sources.splice(i,1);renderSources();updateDashboard()};
  box.appendChild(el);
 });
 $("#source-count").textContent=`${state.sources.length} ACTIVE FEEDS`;
}
function renderArticles(){
 const box=$("#article-list");box.innerHTML="";
 state.articles.slice(0,80).forEach((a,i)=>{
  const label=document.createElement("label");label.className="article";
  label.innerHTML=`<input type="checkbox" ${a.selected?"checked":""}><div><span class="cat">${escapeHtml((a.category||"OTHER").toUpperCase())}</span><h3>${escapeHtml(a.title)}</h3><p>${escapeHtml(a.source)} · ${escapeHtml((a.published||"").slice(0,10))}</p></div><span class="score">${a.editorialScore||"-"}</span>`;
  label.querySelector("input").onchange=e=>{a.selected=e.target.checked;syncSelected();updateCounts()};
  box.appendChild(label);
 });
 updateCounts();
}
function syncSelected(){state.selected=state.articles.filter(a=>a.selected).slice(0,24)}
function updateCounts(){
 syncSelected();
 $("#article-count").textContent=`${state.selected.length} SELECTED · ${state.articles.length} FOUND`;
 $("#selected-stat").textContent=`${state.selected.length} SELECTED`;
}
function updateDashboard(){
 $("#source-stat").textContent=`${state.sources.length} SOURCES`;
 $("#found-stat").textContent=`${state.articles.length} STORIES`;
}
function renderMagazine(){
 const selected=state.selected.length?state.selected:state.articles.slice(0,6);
 $("#cover-dek").textContent=`${selected.length} stories seleccionadas · ${state.sources.length} fuentes · editor v0.3`;
 const box=$("#cover-stories");box.innerHTML="";
 selected.slice(0,5).forEach(a=>{
  const el=document.createElement("div");el.className="mini";
  el.innerHTML=`<b>${escapeHtml((a.category||"OTHER").toUpperCase())}</b><h4>${escapeHtml(a.title)}</h4>`;
  box.appendChild(el);
 });
}
function renderReader(){
 const stories=state.selected.length?state.selected:state.articles;
 if(!stories.length)return;
 const p=state.readerPage%4;
 const left=stories[(p*2)%stories.length],right=stories[(p*2+1)%stories.length];
 $("#reader-page").textContent=`${String(p+1).padStart(2,"0")} / 04`;
 $("#reader-status").textContent=`SPREAD ${String(p+1).padStart(2,"0")} / 04`;
 const img=(a)=>a.image?`<img src="${escapeHtml(a.image)}" alt="" style="width:100%;height:190px;object-fit:cover;background:#20242a" onerror="this.style.display='none'">`:`<div class="feature"></div>`;
 $("#spread").innerHTML=`
 <section class="page"><div class="tag">${escapeHtml((left.category||"OTHER").toUpperCase())} · ${escapeHtml(left.source)}</div>
 <h2>${escapeHtml(left.title)}</h2>${img(left)}
 <p>${escapeHtml(left.description||"Una historia seleccionada por el editor WEEKLY a partir de tus fuentes.")}</p>
 <p><strong>SCORE ${left.editorialScore||"-"}</strong> · <a href="${escapeHtml(left.link)}" target="_blank" rel="noopener" style="color:inherit">READ SOURCE ↗</a></p></section>
 <section class="page"><div class="tag">${escapeHtml((right.category||"OTHER").toUpperCase())} · ${escapeHtml(right.source)}</div>
 <div class="story"><h3>${escapeHtml(right.title)}</h3><p>${escapeHtml(right.description||"Historia destacada de la semana.")}</p></div>
 <div class="story"><h3>EDITOR'S NOTE</h3><p>El editor agrupa historias relacionadas, reduce duplicados y prioriza piezas con mayor relevancia y cobertura.</p></div>
 <div class="story"><h3>THE WEEKLY INDEX</h3><p>${state.clusters.length} temas detectados · ${state.articles.length} artículos encontrados · ${state.selected.length} seleccionados.</p></div></section>`;
}
function renderAll(){renderSources();renderArticles();renderMagazine();renderReader();updateDashboard()}
async function load(){
 try{
  const res=await fetch("data/articles.json?ts="+Date.now());
  if(!res.ok)throw Error("No data");
  const data=await res.json();
  state.articles=data.articles||[];state.selected=data.selected||state.articles.filter(a=>a.selected);
  state.clusters=data.clusters||[];
  const names=[...new Set(state.articles.map(a=>a.source))];
  state.sources=names.map(name=>{const a=state.articles.find(x=>x.source===name);return{name,category:a?.category||"Other"}});
  renderAll();
 }catch(e){console.warn("Using empty/demo state.",e);renderAll()}
}

document.querySelectorAll(".nav-btn").forEach(b=>b.onclick=()=>show(b.dataset.screen));
document.querySelectorAll("[data-go]").forEach(b=>b.onclick=()=>show(b.dataset.go));
$("#generate").onclick=()=>{renderMagazine();show("magazine")};
$("#back-to-articles").onclick=()=>show("articles");
$("#open-reader").onclick=()=>{state.readerPage=0;renderReader();show("reader")};
$("#close-reader").onclick=()=>show("magazine");
$("#prev-page").onclick=()=>{state.readerPage=(state.readerPage+3)%4;renderReader()};
$("#next-page").onclick=()=>{state.readerPage=(state.readerPage+1)%4;renderReader()};
$("#add-source").onclick=()=>{
 const name=prompt("Nombre del medio:");
 if(!name?.trim())return;
 const url=prompt("URL del RSS/Atom (se añadirá a data/feeds.json en la siguiente edición):");
 if(!url?.trim())return;
 state.sources.push({name:name.trim(),category:"Other",url:url.trim()});renderSources();updateDashboard();
 alert("Fuente añadida a esta sesión. Para hacerla persistente en GitHub, añádela a data/feeds.json.");
};
document.addEventListener("keydown",e=>{
 if(!$("#reader").classList.contains("active"))return;
 if(e.key==="ArrowLeft")$("#prev-page").click();if(e.key==="ArrowRight")$("#next-page").click();
});
const d=new Date();$("#today").textContent=d.toLocaleDateString("es-CL",{day:"2-digit",month:"short",year:"numeric"}).toUpperCase();$("#issue-date").textContent=$("#today").textContent;
load();