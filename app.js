const state={sources:[],articles:[],selected:[],editorial:null,readerPage:0,user:null};
const titles={dashboard:"Dashboard",sources:"My Sources",articles:"This Week",magazine:"Magazine",reader:"Reader",archive:"Archive"};
const $=s=>document.querySelector(s);
const esc=s=>String(s??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]));
const cfg=window.WEEKLY_CONFIG||{};
const hasSupabase=()=>Boolean(cfg.supabaseUrl&&cfg.supabaseAnonKey&&!cfg.supabaseUrl.includes("YOUR_PROJECT_REF")&&!cfg.supabaseAnonKey.includes("YOUR_SUPABASE"));
const apiBase=()=>cfg.supabaseUrl.replace(/\/$/,"")+"/rest/v1";

function show(id){document.querySelectorAll(".screen").forEach(x=>x.classList.toggle("active",x.id===id));document.querySelectorAll(".nav-btn").forEach(x=>x.classList.toggle("active",x.dataset.screen===id));$("#screen-title").textContent=titles[id]||"Dashboard"}
function setConnection(text,ok=false){const el=$("#connection-status");if(!el)return;el.textContent=text;el.classList.toggle("ok",ok)}

async function db(path,options={}){
  const headers={apikey:cfg.supabaseAnonKey,...(options.headers||{})};
  const r=await fetch(apiBase()+path,{...options,headers});
  if(!r.ok){let msg=await r.text();throw new Error(`${r.status} ${msg}`)}
  if(r.status===204)return null;
  return r.json();
}

async function loadSources(){
  if(!hasSupabase()) throw new Error("Supabase no está configurado. Crea config.js.");
  return db("/sources?select=id,name,url,category,enabled,created_at&order=created_at.asc");
}

async function addSource(){
  if(!hasSupabase()){alert("Primero configura Supabase en config.js. Mira README.md.");return}
  const name=prompt("Nombre del medio:",""); if(name===null)return;
  const url=prompt("URL del RSS / Atom:",""); if(url===null)return;
  const category=prompt("Categoría (Technology, Games, Culture, World, Other):","Technology"); if(category===null)return;
  if(!name.trim()||!url.trim()){alert("El nombre y la URL son obligatorios.");return}
  try{
    await db("/sources",{method:"POST",headers:{"Content-Type":"application/json",Prefer:"return=representation"},body:JSON.stringify({name:name.trim(),url:url.trim(),category:category.trim()||"Other",enabled:true})});
    await refreshSources();
    show("sources");
    alert("Feed añadido correctamente. 🎉");
  }catch(err){console.error(err);alert("No pude guardar el feed.\n\n"+err.message)}
}

async function removeSource(id,name){
  if(!confirm(`¿Eliminar "${name}" de WEEKLY?`))return;
  try{await db(`/sources?id=eq.${encodeURIComponent(id)}`,{method:"DELETE"});await refreshSources()}catch(err){console.error(err);alert("No pude eliminar el feed.\n\n"+err.message)}
}

function renderSources(){const box=$("#source-grid");box.innerHTML="";state.sources.forEach(s=>{const e=document.createElement("div");e.className="source";e.innerHTML='<span class="dot"></span><div class="source-copy"><strong></strong><small></small><em></em></div><button class="remove">REMOVE</button>';e.querySelector("strong").textContent=s.name;e.querySelector("small").textContent=`${s.category||"Other"} · RSS`;e.querySelector("em").textContent=s.url;e.querySelector(".remove").onclick=()=>removeSource(s.id,s.name);box.appendChild(e)});$("#source-count").textContent=`${state.sources.filter(s=>s.enabled!==false).length} ACTIVE FEEDS`}

async function refreshSources(){
  if(!hasSupabase()){setConnection("SUPABASE NOT CONFIGURED");renderSources();return}
  try{state.sources=await loadSources();setConnection("SUPABASE CONNECTED",true);renderSources();updateDash()}
  catch(err){console.error(err);setConnection("SUPABASE ERROR");alert("No pude leer Supabase.\n\n"+err.message)}
}

function sync(){const ids=new Set((state.editorial?.selected_ids||[]));state.selected=state.articles.filter((a,i)=>ids.has(i));if(!state.selected.length)state.selected=state.articles.filter(a=>a.selected).slice(0,24)}
function renderArticles(){const box=$("#article-list");box.innerHTML="";const aiIds=new Set(state.editorial?.selected_ids||[]);state.articles.slice(0,100).forEach((a,i)=>{const l=document.createElement("label");l.className="article";l.innerHTML=`<input type="checkbox" ${aiIds.has(i)?"checked":""}><div><span class="cat">${esc((a.category||"OTHER").toUpperCase())}</span><h3>${esc(a.title)}</h3><p>${esc(a.source)} · ${esc((a.published||"").slice(0,10))}</p></div><span class="score">${a.editorialScore||"-"}</span>`;l.querySelector("input").onchange=e=>{a.selected=e.target.checked;updateCounts()};box.appendChild(l)});updateCounts()}
function updateCounts(){sync();$("#article-count").textContent=`${state.selected.length} SELECTED · ${state.articles.length} FOUND`;$("#selected-stat").textContent=`${state.selected.length} SELECTED`}
function updateDash(){$("#source-stat").textContent=`${state.sources.length} SOURCES`;$("#found-stat").textContent=`${state.articles.length} STORIES`}
function renderMagazine(){sync();const s=state.selected;const cover=state.editorial?.cover_story!=null?state.articles[state.editorial.cover_story]:s[0];$("#cover-dek").textContent=`${s.length} stories · ${state.sources.length} sources · ${state.editorial?.status==="ai"?"AI EDITOR":"AUTO EDITOR"}`;const box=$("#cover-stories");box.innerHTML="";(s.length?s:s.slice(0,6)).slice(0,5).forEach(a=>{const e=document.createElement("div");e.className="mini";e.innerHTML=`<b>${esc((a.category||"OTHER").toUpperCase())}</b><h4>${esc(a.title)}</h4>`;box.appendChild(e)});if(cover)$("#mag-cover-title").textContent=cover.title}
function renderReader(){sync();const stories=state.selected.length?state.selected:state.articles;if(!stories.length)return;const p=state.readerPage%4,left=stories[(p*2)%stories.length],right=stories[(p*2+1)%stories.length];$("#reader-page").textContent=`${String(p+1).padStart(2,"0")} / 04`;$("#reader-status").textContent=`SPREAD ${String(p+1).padStart(2,"0")} / 04`;const media=a=>a.image?`<img src="${esc(a.image)}" alt="" style="width:100%;height:190px;object-fit:cover;background:#20242a" onerror="this.style.display='none'">`:`<div class="feature"></div>`;$("#spread").innerHTML=`<section class="page"><div class="tag">${esc((left.category||"OTHER").toUpperCase())} · ${esc(left.source)}</div><h2>${esc(left.title)}</h2>${media(left)}<p>${esc(left.description||"Historia seleccionada por el editor de WEEKLY.")}</p><p><strong>SCORE ${left.editorialScore||"-"}</strong> · <a href="${esc(left.link)}" target="_blank" rel="noopener" style="color:inherit">READ SOURCE ↗</a></p></section><section class="page"><div class="tag">${esc((right.category||"OTHER").toUpperCase())} · ${esc(right.source)}</div><div class="story"><h3>${esc(right.title)}</h3><p>${esc(right.description||"Historia destacada de la semana.")}</p></div><div class="story"><h3>EDITOR'S NOTE</h3><p>${esc(state.editorial?.editor_note||"Una selección editorial automática.")}</p></div><div class="story"><h3>THE WEEKLY INDEX</h3><p>${state.editorial?.sections?.length||1} secciones · ${state.articles.length} artículos · ${state.selected.length} seleccionados.</p></div></section>`}

async function loadArticles(){try{const [a,e]=await Promise.all([fetch("data/articles.json?ts="+Date.now()),fetch("data/editorial.json?ts="+Date.now())]);const ad=await a.json();state.articles=ad.articles||[];state.editorial=e.ok?await e.json():null}catch(err){console.warn(err)}state.selected=state.editorial?.selected_ids?.map(i=>state.articles[i]).filter(Boolean)||[]}
async function load(){await Promise.all([loadArticles(),refreshSources()]);renderAll()}
function renderAll(){renderSources();renderArticles();renderMagazine();renderReader();updateDash()}

document.querySelectorAll(".nav-btn").forEach(b=>b.onclick=()=>show(b.dataset.screen));
document.querySelectorAll("[data-go]").forEach(b=>b.onclick=()=>show(b.dataset.go));
$("#generate").onclick=()=>{renderMagazine();show("magazine")};
$("#back-to-articles").onclick=()=>show("articles");
$("#open-reader").onclick=()=>{state.readerPage=0;renderReader();show("reader")};
$("#close-reader").onclick=()=>show("magazine");
$("#prev-page").onclick=()=>{state.readerPage=(state.readerPage+3)%4;renderReader()};
$("#next-page").onclick=()=>{state.readerPage=(state.readerPage+1)%4;renderReader()};
$("#add-source").onclick=addSource;
$("#refresh-sources").onclick=refreshSources;
document.addEventListener("keydown",e=>{if(!$("#reader").classList.contains("active"))return;if(e.key==="ArrowLeft")$("#prev-page").click();if(e.key==="ArrowRight")$("#next-page").click()});
const d=new Date();$("#today").textContent=d.toLocaleDateString("es-CL",{day:"2-digit",month:"short",year:"numeric"}).toUpperCase();$("#issue-date").textContent=$("#today").textContent;load();
