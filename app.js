const state={sources:[],articles:[],selected:[],selectedTags:new Set(),customTags:new Set(),editorial:null,clusters:[],readerPage:0,readerView:"single",shuffled:false,readerModel:null};
const titles={dashboard:"Dashboard",sources:"My Sources",articles:"This Week",magazine:"Magazine",reader:"Reader",archive:"Archive"};
const $=s=>document.querySelector(s);
const esc=s=>String(s??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]));
const cfg=window.WEEKLY_CONFIG||{};
const hasSupabase=()=>Boolean(cfg.supabaseUrl&&(cfg.supabaseAnonKey||cfg.supabasePublishableKey)&&!cfg.supabaseUrl.includes("YOUR_PROJECT_REF"));
const supabaseKey=()=>cfg.supabaseAnonKey||cfg.supabasePublishableKey||"";
const apiBase=()=>cfg.supabaseUrl.replace(/\/$/,"")+"/rest/v1";
function show(id){document.querySelectorAll(".screen").forEach(x=>x.classList.toggle("active",x.id===id));document.querySelectorAll(".nav-btn").forEach(x=>x.classList.toggle("active",x.dataset.screen===id));$("#screen-title").textContent=titles[id]||"Dashboard"}
function setConnection(text,ok=false){const el=$("#connection-status");if(!el)return;el.textContent=text;el.classList.toggle("ok",ok)}
async function db(path,options={}){const key=supabaseKey();const headers={apikey:key,Authorization:`Bearer ${key}`,...(options.headers||{})};const r=await fetch(apiBase()+path,{...options,headers});if(!r.ok){let msg=await r.text();throw new Error(`${r.status} ${msg}`)}if(r.status===204)return null;return r.json()}
async function loadSources(){if(!hasSupabase())throw new Error("Supabase no está configurado. Crea config.js.");return db("/sources?select=id,name,url,category,enabled,created_at&order=created_at.asc")}
async function addSource(){if(!hasSupabase()){alert("Primero configura Supabase en config.js. Mira README.md.");return}const name=prompt("Nombre del medio:","");if(name===null)return;const url=prompt("URL del RSS / Atom:","");if(url===null)return;const category=prompt("Categoría (Technology, Games, Culture, World, Other):","Other");if(category===null)return;if(!name.trim()||!url.trim()){alert("El nombre y la URL son obligatorios.");return}try{await db("/sources",{method:"POST",headers:{"Content-Type":"application/json",Prefer:"return=representation"},body:JSON.stringify({name:name.trim(),url:url.trim(),category:category.trim()||"Other",enabled:true})});await refreshSources();show("sources");alert("Feed añadido correctamente. 🎉")}catch(err){console.error(err);alert("No pude guardar el feed.\n\n"+err.message)}}
async function removeSource(id,name){if(!confirm(`¿Eliminar "${name}" de WEEKLY?`))return;try{await db(`/sources?id=eq.${encodeURIComponent(id)}`,{method:"DELETE"});await refreshSources()}catch(err){console.error(err);alert("No pude eliminar el feed.\n\n"+err.message)}}
function renderSources(){const box=$("#source-grid");box.innerHTML="";state.sources.forEach(s=>{const e=document.createElement("div");e.className="source";e.innerHTML='<span class="dot"></span><div class="source-copy"><strong></strong><small></small><em></em></div><button class="remove">REMOVE</button>';e.querySelector("strong").textContent=s.name;e.querySelector("small").textContent=`${s.category||"Other"} · RSS`;e.querySelector("em").textContent=s.url;e.querySelector(".remove").onclick=()=>removeSource(s.id,s.name);box.appendChild(e)});$("#source-count").textContent=`${state.sources.filter(s=>s.enabled!==false).length} ACTIVE FEEDS`}
async function refreshSources(){if(!hasSupabase()){setConnection("SUPABASE NOT CONFIGURED");renderSources();return}try{state.sources=await loadSources();setConnection("SUPABASE CONNECTED",true);renderSources();updateDash()}catch(err){console.error(err);setConnection("SUPABASE ERROR");alert("No pude leer Supabase.\n\n"+err.message)}}
const TAG_STOP=new Set("the a an and or of to in on for with from by is are was were this that how why what your you new news more into about after as at it its there their they has have had will would could should just than then very been being not you our their from about today week best one two three get gets can may might while over under who where when into onto only also says said according latest plus here this these those all any any more most some such other another much many much new own its his her them he she we us i me my mine de an der die das und für mit von ist sind auf den im die der ein eine the los las del para por con que una uno como sus más este esta estos estas puede pueden fue han ha hay ya hoy según sobre entre tras al se su es en de".split());
function deriveTags(a){const text=`${a.title||""} ${a.description||""} ${(a.headings?.h1||[]).join(" ")} ${(a.headings?.h2||[]).join(" ")}`.toLowerCase();const words=(text.match(/[a-zA-ZÀ-ÿ0-9]{4,}/g)||[]).map(w=>w.toLowerCase()).filter(w=>!TAG_STOP.has(w));const freq={};words.forEach(w=>freq[w]=(freq[w]||0)+1);const generic=new Set(["history","story","article","selected","source","week","today","best","world","thing","things","edition","review","technology","games"]);const keywords=Object.entries(freq).filter(([w])=>!generic.has(w)).sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0])).slice(0,5).map(([w])=>w.toUpperCase());const base=[];if(a.category)base.push(String(a.category).toUpperCase());if(Array.isArray(a.tags))base.push(...a.tags.map(x=>String(x).toUpperCase()));return [...new Set([...base,...keywords])].slice(0,8)}
const CUSTOM_ALIASES={
  "ANIME":["anime","manga","otaku","japanese animation","shonen","isekai","studio ghibli"],
  "MARVEL":["marvel","mcu","avengers","spider-man","spiderman","x-men","xmen","deadpool","fantastic four","guardians of the galaxy"],
  "DC":["dc comics","dc","batman","superman","wonder woman","justice league","joker","gotham"],
  "RETRO GAMING":["retro gaming","retro game","classic games","arcade","nes","snes","game boy","gameboy","mega drive","genesis","dreamcast","playstation 1","ps1","playstation 2","ps2","n64","sega saturn"],
  "POKEMON":["pokemon","pokémon","pikachu","game freak"],
  "MANGA":["manga","shonen","shojo","seinen","josei"],
  "STAR WARS":["star wars","lightsaber","jedi","sith","mandalorian","skywalker"],
  "HORROR":["horror","horr","slasher","survival horror","creepy","ghost","vampire","zombie"]
};
function allTags(){const m=new Map();state.articles.filter(isUsableArticle).forEach(a=>{(a.tags?.length?a.tags:deriveTags(a)).forEach(t=>m.set(t,(m.get(t)||0)+1))});return [...m.entries()].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0]))}
function articleSearchText(a){return `${a.title||""} ${a.description||""} ${a.source||""} ${(a.category||"")} ${(a.headings?.h1||[]).join(" ")} ${(a.headings?.h2||[]).join(" ")} ${(a.tags||[]).join(" ")}`.toLowerCase()}
function topicAliases(topic){const key=String(topic||"").trim().toUpperCase();return [key.toLowerCase(),...(CUSTOM_ALIASES[key]||[])].filter(Boolean)}
function matchesCustomTopic(a,topic){const text=articleSearchText(a);return topicAliases(topic).some(alias=>{const q=alias.toLowerCase().trim();return q.length>=2&&text.includes(q)})}
function matchesTags(a){if(!state.selectedTags.size&&!state.customTags.size)return true;const tags=a.tags?.length?a.tags:deriveTags(a);const auto=tags.some(t=>state.selectedTags.has(String(t).toUpperCase()));const custom=[...state.customTags].some(t=>matchesCustomTopic(a,t));return auto||custom}
function normalizeSource(s){return String(s||"").toLowerCase().replace(/https?:\/\//g,"").replace(/^www\./,"").replace(/\/$/,"").trim()}
function activeSourceNames(){return new Set(state.sources.filter(s=>s.enabled!==false).flatMap(s=>[normalizeSource(s.name),normalizeSource(s.url),normalizeSource((()=>{try{return new URL(s.url).hostname}catch(e){return ""}})())]).filter(Boolean))}
function articleBelongsToActiveSource(a){
  if(!state.sources.length)return true;
  const active=activeSourceNames();
  if(!active.size)return true;
  const raw=[a?.source,a?.sourceName,a?.feed,a?.feedTitle].map(normalizeSource).filter(Boolean);
  if(raw.some(x=>[...active].some(n=>x===n||x.includes(n)||n.includes(x))))return true;
  const linkHost=(()=>{try{return normalizeSource(new URL(a?.link||"").hostname)}catch(e){return ""}})();
  if(linkHost && [...active].some(n=>linkHost===n||linkHost.endsWith("."+n)||n.endsWith("."+linkHost)))return true;
  return false;
}
const COMMERCIAL_PATTERNS=[/\bpromo(?:tion)?\s*code\b/i,/\bcoupon\s*code\b/i,/\bdiscount\s*code\b/i,/\bpromo\s*codes?\b/i,/\bcoupon\s*codes?\b/i,/\bdeals?\b/i,/\bdiscounts?\b/i,/\bgroupon\b/i,/\bsave\s+\d{1,3}%/i,/\b(?:up to|save)\s+\d{1,3}%\s+off\b/i,/\bsponsored\b/i,/\badvertorial\b/i,/\baffiliate\b/i,/\bshopping\s+guide\b/i];
function isCommercial(a){const text=`${a?.title||""} ${a?.description||""} ${(a?.tags||[]).join(" ")}`;return COMMERCIAL_PATTERNS.some(re=>re.test(text));}
function isUsableArticle(a){return articleBelongsToActiveSource(a)&&!isCommercial(a)}
function clusterLeadIds(){
  const ids=new Set();
  if(Array.isArray(state.clusters)&&state.clusters.length){
    state.clusters.forEach(c=>{
      const lead=Number(c?.lead); if(Number.isInteger(lead)&&state.articles[lead])ids.add(state.articles[lead].id||state.articles[lead].link);
    });
  }
  return ids;
}
function candidatePool(){
  const base=state.articles.filter(isUsableArticle).filter(matchesTags);
  const leadIds=clusterLeadIds();
  return leadIds.size?base.filter(a=>leadIds.has(a.id||a.link)):base;
}
function shuffleArray(arr){const out=[...arr];for(let i=out.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[out[i],out[j]]=[out[j],out[i]]}return out}
function chooseRandomStories(pool=candidatePool()){const ranked=shuffleArray(pool.slice()).sort((a,b)=>((b.editorialScore||0)-(a.editorialScore||0))*(Math.random()*.55+.45));const out=[],counts={};for(const a of ranked){const cat=a.category||"Other";if((counts[cat]||0)>=8)continue;out.push(a);counts[cat]=(counts[cat]||0)+1;if(out.length>=24)break}return out}
function sync(){if(!state.selected.length||state.shuffled){state.selected=chooseRandomStories();state.shuffled=false}if(!state.selected.length)state.selected=candidatePool().filter(a=>a.selected).slice(0,24);updateCounts()}
function saveTopics(){localStorage.setItem("weekly.selectedTags",JSON.stringify([...state.selectedTags]));localStorage.setItem("weekly.customTags",JSON.stringify([...state.customTags]))}
function rerenderTopicSelection(){state.selected=[];state.readerModel=null;state.shuffled=true;saveTopics();renderTags();renderArticles();renderMagazine()}
function addCustomTopic(raw){const topic=String(raw||"").trim().replace(/\s+/g," ");if(!topic)return false;const key=topic.toUpperCase();if(state.customTags.has(key)||state.selectedTags.has(key))return false;state.customTags.add(key);rerenderTopicSelection();return true}
function removeCustomTopic(topic){state.customTags.delete(String(topic).toUpperCase());rerenderTopicSelection()}
function renderTags(){const box=$("#tag-cloud");if(!box)return;box.innerHTML="";const custom=[...state.customTags];if(custom.length){const head=document.createElement("div");head.className="custom-topic-list";head.innerHTML=custom.map(t=>`<button class="tag-chip custom-chip active" data-custom-topic="${esc(t)}"><span>${esc(t)}</span><small>×</small></button>`).join("");box.appendChild(head);head.querySelectorAll("[data-custom-topic]").forEach(b=>b.onclick=()=>removeCustomTopic(b.dataset.customTopic))}
const tags=allTags();const cloud=document.createElement("div");cloud.className="auto-tag-list";tags.forEach(([tag,count])=>{const b=document.createElement("button");b.className="tag-chip"+(state.selectedTags.has(tag)?" active":"");b.innerHTML=`<span>${esc(tag)}</span><small>${count}</small>`;b.onclick=()=>{if(state.selectedTags.has(tag))state.selectedTags.delete(tag);else state.selectedTags.add(tag);rerenderTopicSelection()};cloud.appendChild(b)});box.appendChild(cloud);$("#tag-count").textContent=`${state.selectedTags.size+state.customTags.size} SELECTED`}
function renderArticles(){const box=$("#article-list");if(!box)return;const pool=candidatePool();if(!state.selected.length||state.shuffled){state.selected=chooseRandomStories(pool);state.shuffled=false}$("#pool-stat").textContent=`${pool.length} STORIES IN POOL`;const activeTopics=[...state.selectedTags,...state.customTags];$("#pool-note").textContent=activeTopics.length?`Temas: ${activeTopics.join(" · ")}`:"Todo el feed está disponible. WEEKLY elegirá una combinación al azar.";box.innerHTML="";shuffleArray(pool).slice(0,12).forEach(a=>{const l=document.createElement("div");l.className="article preview-article";const tags=(a.tags?.length?a.tags:deriveTags(a)).slice(0,4);l.innerHTML=`<div class="article-thumb">${a.image?`<img src="${esc(a.image)}" alt="">`:""}</div><div><span class="cat">${esc((a.category||"OTHER").toUpperCase())}</span><h3>${esc(a.title)}</h3><p>${esc(a.source)} · ${esc((a.published||"").slice(0,10))}</p><div class="mini-tags">${tags.map(t=>`<span>${esc(t)}</span>`).join("")}</div></div><span class="score">${a.editorialScore||"-"}</span>`;box.appendChild(l)});updateCounts()}
function updateCounts(){const pool=candidatePool();$("#article-count").textContent=`${state.selected.length} SELECTED · ${pool.length} IN POOL`;$("#selected-stat").textContent=`${state.selected.length} SELECTED`}
function storyFor(a){return(state.editorial?.stories||[]).find(s=>s.article_id===state.articles.indexOf(a))||null}
function articleTags(a){return(a?.tags?.length?a.tags:deriveTags(a)).slice(0,5)}
function layoutFor(index){
  const layouts=["layout-feature","layout-news","layout-image","layout-quote","layout-short","layout-dark"];
  return layouts[Math.abs(Number(index)||0)%layouts.length]
}
function coverImage(a,cls="cover-image",label="WEEKLY FEATURE"){return a?.image?`<div class="${cls}"><img src="${esc(a.image)}" alt=""><span>${esc(label)}</span></div>`:`<div class="${cls}"><span>${esc(label)}</span></div>`}
function storyTitle(a){const st=storyFor(a);return st?.headline||a?.title||"UNTITLED STORY"}
function layoutFor(index){
  const layouts=["layout-feature","layout-news","layout-image","layout-quote","layout-short","layout-dark"];
  return layouts[Math.abs(Number(index)||0)%layouts.length]
}
function storyWords(a){
  return storyBlocks(a).map(b=>b.text).join(" ").replace(/\s+/g," ").trim();
}
function pullQuote(a){
  const blocks=storyBlocks(a);
  const explicit=blocks.find(b=>b.type==="blockquote" && b.text.length>35);
  if(explicit)return explicit.text;
  const text=storyWords(a);
  const sentences=(text.match(/[^.!?]+[.!?]+/g)||[]).map(x=>x.trim()).filter(x=>x.length>=45&&x.length<=150);
  if(sentences.length)return sentences[Math.min(1,sentences.length-1)];
  return text.slice(0,150).trim()+ (text.length>150?"…":"");
}
function sectionName(a){return String(a?.category||"WEEKLY PICKS").toUpperCase();}
function sectionOpener(a,number){
  const name=sectionName(a);
  const lead=storyTitle(a);
  return `<section class="page section-opener"><div class="section-opener-grid"><div class="section-marker">SECTION ${String(number).padStart(2,"0")}</div><div class="section-name">${esc(name)}</div><div class="section-rule"></div><div class="section-lead"><span>UP NEXT</span><h2>${esc(lead)}</h2><p>${esc(a?.description||pullQuote(a))}</p></div><div class="section-giant">${esc(name.slice(0,1))}</div></div><div class="page-number">${String(number).padStart(2,"0")}</div></section>`;
}
function renderMagazine(){sync();const s=state.selected;const cover=s[0];$("#cover-dek").textContent=`${s.length} stories · ${state.sources.length} sources · ${state.editorial?.status==="ai"?"AI EDITOR":"RSS EDITOR"}`;$("#mag-cover-title").textContent=storyTitle(cover)||"THE NEWS DESERVES A BETTER INTERFACE.";$("#issue-number").textContent=String(state.editorial?.issueNumber||"036");const activeTopics=[...state.selectedTags,...state.customTags];$("#cover-tags").textContent=activeTopics.length?activeTopics.join(" · "):"TAG MIX · RANDOMIZED";$("#cover-count").textContent=`${s.length} STORIES`;const box=$("#cover-stories");box.innerHTML="";s.slice(0,6).forEach((a,i)=>{const e=document.createElement("button");e.className="mini mini-link";e.innerHTML=`<b>${esc((a.category||"OTHER").toUpperCase())}</b><h4>${esc(storyTitle(a))}</h4><small>${String(i+2).padStart(2,"0")}</small>`;e.onclick=()=>{state.readerPage=0;state._readerTargetStory=i;show("reader");requestAnimationFrame(()=>renderReader())};box.appendChild(e)});const old=$(".cover-image");if(old){const holder=document.createElement("div");holder.innerHTML=coverImage(cover,"cover-image","MAIN FEATURE");old.replaceWith(holder.firstElementChild)}}
// V0.9.6 — Smart page composer: budgets are tuned for the actual single-page canvas.
// Continuation pages intentionally carry much more text than the old 900-char cap.
const PAGE_CHAR_TARGET_DESKTOP=2500;
const PAGE_CHAR_TARGET_TABLET=2100;
const PAGE_CHAR_TARGET_MOBILE=1500;
const PAGE_CHAR_TARGET_FIRST={
  "layout-feature":820,
  "layout-news":900,
  "layout-image":760,
  "layout-quote":700,
  "layout-short":980,
  "layout-dark":820
};
function storyBlocks(a){
  const blocks=Array.isArray(a?.contentBlocks)?a.contentBlocks:[];
  if(blocks.length)return blocks.filter(b=>b&&b.text).map(b=>({type:b.type||"p",text:String(b.text).trim()}));
  // Some generated article feeds have contentText but no structured blocks.
  // Recover that body before falling back to the one-line RSS description.
  if(typeof a?.contentText==="string" && a.contentText.trim()){
    return a.contentText.split(/\n{2,}|(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ])/u).map(t=>t.trim()).filter(t=>t.length>=25).map(text=>({type:"p",text}));
  }
  const fallback=[];
  if(a?.headings?.h1?.length) fallback.push({type:"h1",text:a.headings.h1[0]});
  if(a?.description) fallback.push({type:"p",text:a.description});
  return fallback;
}
function splitLongBlock(b,target){
  const out=[]; let rest=String(b.text||"").trim();
  while(rest.length>target){
    let cut=rest.lastIndexOf(" ",target);
    if(cut<Math.floor(target*.55))cut=target;
    out.push({type:b.type,text:rest.slice(0,cut).trim()});
    rest=rest.slice(cut).trim();
  }
  if(rest)out.push({type:b.type,text:rest});
  return out;
}
function paginateBlocks(blocks,target){
  const pages=[]; let page=[]; let chars=0;
  const pushPage=()=>{if(page.length){pages.push(page);page=[];chars=0}};
  for(const original of blocks){
    if(!original?.text)continue;
    const chunks=original.text.length>target?splitLongBlock(original,target):[original];
    for(const b of chunks){
      const cost=b.text.length+2;
      if(page.length && chars+cost>target)pushPage();
      page.push(b); chars+=cost;
    }
  }
  pushPage();
  return pages.length?pages:[[{type:"p",text:"The source did not expose article text. Read the original article for the complete story."}]];
}
function firstPageBudget(a){
  const type=layoutFor((a?._storyIndex||0));
  return PAGE_CHAR_TARGET_FIRST[type]||340;
}
function pageCharTarget(){
  const width=window.innerWidth||1200;
  if(state.readerView==="spread") return width<=720?1300:1600;
  if(width<=720) return PAGE_CHAR_TARGET_MOBILE;
  if(width<1050) return PAGE_CHAR_TARGET_TABLET;
  return PAGE_CHAR_TARGET_DESKTOP;
}
function articleTextPages(a){
  const blocks=storyBlocks(a);
  const target=pageCharTarget();
  if(!blocks.length)return paginateBlocks(blocks,target);
  const firstBudget=Math.min(firstPageBudget(a), Math.round(target*.48));
  const first=paginateBlocks(blocks,firstBudget);
  if(first.length>1){
    const used=first.reduce((n,p)=>n+p.length,0);
    const restBlocks=[...first.slice(1).flat(),...blocks.slice(used)];
    return [first[0],...paginateBlocks(restBlocks,target)];
  }
  return paginateBlocks(blocks,target);
}
function headlineClassFor(title){
  const n=(title||"").length;
  if(n>110)return " headline-ultra-long";
  if(n>82)return " headline-long";
  if(n>62)return " headline-medium";
  return "";
}
function blockHtml(b){if(b.type==="h1"||b.type==="h2"||b.type==="h3"||b.type==="h4")return `<h3 class="source-body-heading">${esc(b.text)}</h3>`;if(b.type==="blockquote")return `<blockquote class="source-quote">${esc(b.text)}</blockquote>`;return `<p>${esc(b.text)}</p>`}
function articleImages(a){
  const raw=Array.isArray(a?.images)?a.images:[];
  const out=[]; const seen=new Set();
  for(const item of raw){
    const url=typeof item==="string"?item:item?.url;
    if(!url)continue;
    const key=String(url).trim();
    if(!key||seen.has(key))continue;
    seen.add(key); out.push(typeof item==="string"?{url:key,caption:""}:{url:key,caption:String(item?.caption||"")});
  }
  if(!out.length&&a?.image)out.push({url:a.image,caption:""});
  return out;
}
function inlineArticleImage(a,index){
  const imgs=articleImages(a);
  if(index<0||index>=imgs.length)return "";
  const item=imgs[index];
  return `<figure class="reader-inline-image"><img src="${esc(item.url)}" alt="${esc(item.caption||storyTitle(a))}" loading="lazy">${item.caption?`<figcaption>${esc(item.caption)}</figcaption>`:""}<span>ORIGINAL IMAGE</span></figure>`;
}
function readerColumnCount(width){
  const viewport=window.innerWidth||1200;
  return (viewport>=1050 && width>=620 && state.readerView!=="spread") ? 2 : 1;
}
function normalizeColumns(columns){
  if(Array.isArray(columns) && columns.length && Array.isArray(columns[0])) return columns;
  if(Array.isArray(columns)) return [columns];
  return [[]];
}
function columnHtml(blocks){
  return `<div class="source-column">${(blocks||[]).map(blockHtml).join("")}</div>`;
}
function articlePageHtmlFromParts(a,pageIndex,totalPages,globalNumber,columns,imageIndex=-1){
  const first=pageIndex===0; const imgs=articleImages(a); const h=a.headings||{};
  const image=first?coverImage(a,"reader-story-image","ORIGINAL IMAGE"):"";
  const type=layoutFor((a._storyIndex||0)+pageIndex);
  const headlineClass=headlineClassFor(storyTitle(a));
  const quote=esc(pullQuote(a));
  const tags=articleTags(a); const sourceLabel=esc(a.source||"ORIGINAL SOURCE");
  const date=esc((a.published||"").slice(0,10));
  const featureNumber=String((a._storyIndex||0)+1).padStart(2,"0");
  const firstExtras=first && type==="layout-quote" ? `<aside class="pull-quote">“${quote}”</aside>` : "";
  const continuationImage=(!first && imageIndex>=0 && imageIndex<imgs.length)?inlineArticleImage(a,imageIndex):"";
  const cols=normalizeColumns(columns);
  const colCount=cols.length;
  return `<section class="page article-page source-text-page source-cols-${colCount} ${first?"source-first":"source-continuation"} ${type}${headlineClass}">
    <div class="story-running"><span>${sourceLabel}</span><span>${date}</span></div>
    ${first?`<div class="tag">${esc((a.category||"OTHER").toUpperCase())}</div><h2>${esc(storyTitle(a))}</h2><p class="dek">${esc(a.description||h.h1?.[1]||"")}</p>${image}`:`<div class="continued-kicker">CONTINUED · ${String(pageIndex+1).padStart(2,"0")} / ${String(totalPages).padStart(2,"0")}</div>`}
    ${firstExtras}
    ${continuationImage}
    <div class="source-body source-body-grid">${cols.map(columnHtml).join("")}</div>
    ${first&&tags.length?`<div class="tag-row">${tags.map(t=>`<span>${esc(t)}</span>`).join("")}</div>`:""}
    ${pageIndex===totalPages-1?`${otherSourcesHtml(a)}<div class="source-end"><span>END OF STORY · ${featureNumber}</span>${linkButton(a)}</div>`:""}
    <div class="feature-number">${featureNumber}</div><div class="page-number">${String(globalNumber).padStart(2,"0")}</div>
  </section>`;
}
function articlePageHtml(a,pageIndex,totalPages,globalNumber){
  const pages=articleTextPages(a); return articlePageHtmlFromParts(a,pageIndex,totalPages,globalNumber,[pages[pageIndex]||[]],-1);
}
function measurementDimensions(){
  const spread=document.querySelector("#spread");
  let width=0,height=0;
  if(spread && spread.clientWidth){
    width=Math.min(spread.clientWidth, state.readerView==="spread"?Math.floor(spread.clientWidth/2):spread.clientWidth);
    const page=spread.querySelector(".page"); if(page){width=page.clientWidth||width;height=page.clientHeight||0;}
  }
  if(!width) width=Math.min(window.innerWidth>720?760:Math.max(300,window.innerWidth-32),760);
  if(!height) height=state.readerView==="spread"?Math.max(560,Math.min(760,window.innerHeight-250)):Math.round(width*4/3);
  if(document.fullscreenElement || document.querySelector("#reader.reader-fullscreen")) height=Math.max(420,window.innerHeight-105);
  return {width:Math.max(260,Math.round(width)),height:Math.max(420,Math.round(height))};
}
function measureArticleCandidate(a,pageIndex,columns,imageIndex,forceTotal=99){
  const dims=measurementDimensions();
  const host=document.createElement("div");
  host.className="spread single-view weekly-measure-host";
  host.style.cssText=`position:fixed!important;left:-100000px!important;top:0!important;width:${dims.width}px!important;height:${dims.height}px!important;display:block!important;visibility:hidden!important;pointer-events:none!important;overflow:hidden!important;`;
  host.innerHTML=articlePageHtmlFromParts(a,pageIndex,forceTotal,1,columns,imageIndex);
  const page=host.firstElementChild;
  if(!page){host.remove();return {fits:false,scroll:999999,height:dims.height};}
  page.style.width=dims.width+"px"; page.style.height=dims.height+"px"; page.style.maxHeight=dims.height+"px";
  document.body.appendChild(host);
  const columnEls=[...page.querySelectorAll(".source-column")];
  const verticalOverflow=columnEls.some(col=>col.scrollHeight>col.clientHeight+1);
  const horizontalOverflow=page.scrollWidth>page.clientWidth+1;
  const pageOverflow=false;
  const fits=!verticalOverflow && !horizontalOverflow;
  const scroll=Math.max(page.scrollHeight,page.scrollWidth,...columnEls.map(col=>col.scrollHeight));
  host.remove();
  return {fits,scroll,height:dims.height,verticalOverflow,horizontalOverflow,pageOverflow};
}
function expandPaginationBlocks(blocks){
  const out=[];
  for(const b of blocks){
    if(!b?.text)continue;
    const text=String(b.text).trim();
    const max=900;
    if(text.length<=max){out.push({...b,text});continue;}
    let rest=text;
    while(rest.length>max){
      let cut=rest.lastIndexOf(" ",max);
      if(cut<Math.floor(max*.55))cut=max;
      out.push({...b,text:rest.slice(0,cut).trim()});
      rest=rest.slice(cut).trim();
    }
    if(rest)out.push({...b,text:rest});
  }
  return out;
}
function blockFits(a,pageIndex,columns,imageIndex){
  return measureArticleCandidate(a,pageIndex,columns,imageIndex).fits;
}
function fitBlockIntoColumn(a,pageIndex,columns,colIndex,block,imageIndex){
  const target=Array.isArray(columns[colIndex])?columns[colIndex]:[];
  let candidate=[...target,block];
  const test=columns.map((c,i)=>i===colIndex?candidate:c);
  if(blockFits(a,pageIndex,test,imageIndex)) return {ok:true,block,columns:test};
  let text=String(block.text||"");
  if(text.length<120) return {ok:false,columns};
  let lo=60, hi=Math.max(60,text.length-1), best=null;
  while(lo<=hi){
    const mid=Math.floor((lo+hi)/2);
    let cut=text.lastIndexOf(" ",mid);
    if(cut<Math.floor(mid*.55))cut=mid;
    const piece={...block,text:text.slice(0,cut).trim()};
    const probe=columns.map((c,i)=>i===colIndex?[...target,piece]:c);
    if(piece.text && blockFits(a,pageIndex,probe,imageIndex)){best={piece,columns:probe};lo=cut+1;}else hi=cut-1;
  }
  return best?{ok:true,block:best.piece,columns:best.columns,remaining:{...block,text:text.slice(best.piece.text.length).trim()}}:{ok:false,columns};
}
function paginateArticleFast(a){
  const blocks=expandPaginationBlocks(storyBlocks(a));
  if(!blocks.length)return [{columns:[[]],imageIndex:-1}];

  const width=window.innerWidth||1200;
  const cols=(width>=1050 && state.readerView!=='spread')?2:1;
  // Character budgets are deliberately conservative. They are not a visual
  // measurement; they are a deterministic packing rule whose only job is to
  // guarantee that every source block is consumed exactly once.
  const colTarget=cols===2 ? (width>=1300?1550:1400) : (width<=720?1250:1750);
  const firstColTarget=cols===2 ? 1150 : 1350;
  const pages=[];
  let queue=blocks.map(b=>({...b,text:String(b.text||'').trim()})).filter(b=>b.text);
  let pageIndex=0;
  let imageCursor=1;
  const images=articleImages(a);

  while(queue.length){
    const columns=Array.from({length:cols},()=>[]);
    let imageIndex=-1;

    // Continuation images are page-level units. They never replace article text.
    if(pageIndex>0 && imageCursor<images.length){
      imageIndex=imageCursor++;
    }

    for(let ci=0;ci<cols && queue.length;ci++){
      let budget=(pageIndex===0 && ci===0)?firstColTarget:colTarget;
      while(queue.length && budget>0){
        const b=queue[0];
        const text=String(b.text||'').trim();
        if(!text){queue.shift();continue;}
        const cost=text.length+20;
        if(cost<=budget || !columns[ci].length){
          if(cost<=budget){
            columns[ci].push(queue.shift());
            budget-=cost;
          }else{
            // The block is larger than an empty column. Split it by words and
            // keep the remainder at the head of the queue for the next column.
            const take=Math.max(180,budget-20);
            let cut=text.lastIndexOf(' ',Math.min(take,text.length-1));
            if(cut<120)cut=Math.min(text.length,Math.max(180,take));
            const piece=text.slice(0,cut).trim();
            const rest=text.slice(cut).trim();
            if(!piece){
              columns[ci].push(queue.shift());
              budget=0;
            }else{
              columns[ci].push({...b,text:piece});
              if(rest)queue[0]={...b,text:rest}; else queue.shift();
              budget=0;
            }
          }
        }else{
          break;
        }
      }
    }

    // Absolute safety: if a pathological block survived, consume it in a
    // fresh page rather than dropping it or freezing in a retry loop.
    if(columns.every(c=>!c.length) && queue.length){
      const b=queue.shift();
      const text=String(b.text||'');
      const cut=Math.max(1,Math.min(text.length,Math.max(180,colTarget-20)));
      columns[0].push({...b,text:text.slice(0,cut).trim()});
      const rest=text.slice(cut).trim();
      if(rest)queue.unshift({...b,text:rest});
    }

    pages.push({columns,imageIndex});
    pageIndex++;
  }
  return pages.length?pages:[{columns:[[]],imageIndex:-1}];
}

function buildReaderPages(){
  const stories=state.selected.length?state.selected:state.articles; const pages=[]; const articleStarts={};
  if(!stories.length)return {pages,articleStarts};
  const cover=stories[0]; const tags=articleTags(cover);
  pages.push(`<section class="page cover-page">${coverImage(cover,"reader-cover-image","COVER STORY")}<div class="tag">WEEKLY · ${esc((cover?.category||"OTHER").toUpperCase())}</div><h2>${esc(storyTitle(cover))}</h2><p class="dek">${esc(cover?.description||"")}</p><div class="tag-row">${tags.map(t=>`<span>${esc(t)}</span>`).join("")}</div><p class="cover-kicker"><strong>THE WEEKLY / ${state.editorial?.issueNumber||"036"}</strong></p></section>`);
  const tocItems=stories.map((a,i)=>`<button data-reader-target="${i}"><span>${String(i+1).padStart(2,"0")}</span><strong>${esc(storyTitle(a))}</strong><em>${esc((a.category||"OTHER").toUpperCase())}</em></button>`).join("");
  pages.push(`<section class="page index-page"><div class="index-kicker">CONTENTS</div><h2>THIS ISSUE</h2><p class="index-intro">${stories.length} stories · selected from ${candidatePool().length} editorial articles.</p><div class="toc">${tocItems}</div></section>`);
  let physical=2; let lastSection=""; let sectionNumber=0;
  stories.forEach((a,i)=>{
    a._storyIndex=i;
    const section=sectionName(a);
    if(section!==lastSection){
      sectionNumber++;
      pages.push(sectionOpener(a,physical+1));
      physical++;
      lastSection=section;
    }
    articleStarts[i]=physical;
    const parts=paginateArticleFast(a);
    const total=parts.length;
    parts.forEach((part,pi)=>{pages.push(articlePageHtmlFromParts(a,pi,total,physical+1,part.columns,part.imageIndex));physical++});
  });
  pages.push(`<section class="page closing-page"><div class="closing-mark">W</div><div class="closing-copy"><span>END OF ISSUE</span><h2>SEE YOU<br>NEXT WEEK.</h2><p>WEEKLY is built from the sources you chose, arranged into a magazine you can actually sit down and read.</p><div class="closing-meta">${stories.length} STORIES · ${state.sources.length} SOURCES · ${state.editorial?.issueNumber||"036"}</div></div><div class="page-number">${String(physical+1).padStart(2,"0")}</div></section>`);
  return {pages,articleStarts};
}
function totalReaderPages(){const model=state.readerModel||buildReaderPages();return Math.max(1,model.pages.length)}
function totalSpreads(){return Math.max(1,Math.ceil(totalReaderPages()/2))}
function otherSourcesFor(a){
  if(Array.isArray(a?.otherSources)) return a.otherSources;
  const idx=state.articles.indexOf(a);
  const c=state.clusters?.find(x=>Array.isArray(x?.articleIds)&&x.articleIds.includes(idx));
  if(!c)return [];
  return c.articleIds.filter(i=>i!==idx).map(i=>state.articles[i]).filter(Boolean);
}
function otherSourcesHtml(a){
  const others=otherSourcesFor(a); if(!others.length)return "";
  const seen=new Set();
  const items=others.filter(o=>{const k=o.link||o.id||o.source;if(seen.has(k))return false;seen.add(k);return true;}).slice(0,6);
  return `<div class="other-sources"><span>OTHER SOURCES</span><div>${items.map(o=>`<a href="${esc(o.link||'#')}" target="_blank" rel="noopener">${esc(o.source||"SOURCE")}</a>`).join("")}</div></div>`;
}
function linkButton(a){return a?.link?`<a class="source-link" href="${esc(a.link)}" target="_blank" rel="noopener">READ ORIGINAL ↗</a>`:""}
function renderReader(){
  sync();
  if(!state.readerModel){
    const spread=document.querySelector("#spread");
    if(spread && !state.readerBuilding){
      state.readerBuilding=true;
      spread.classList.add("single-view");
      spread.innerHTML=`<section class="page loading-page"><div class="loading-mark">W</div><div class="loading-copy"><span>WEEKLY</span><h2>LOADING<br>MAGAZINE…</h2><p>Composing this week's issue.</p></div></section>`;
      requestAnimationFrame(()=>setTimeout(()=>{
        try{ state.readerModel=buildReaderPages(); }
        finally{ state.readerBuilding=false; renderReader(); }
      },0));
      return;
    }
  }
  const model=state.readerModel||buildReaderPages(); state.readerModel=model; if(Number.isInteger(state._readerTargetStory)){ const t=model.articleStarts[state._readerTargetStory]; if(typeof t==="number"){ state.readerPage=state.readerView==="spread"?Math.floor(t/2)*2:t; } delete state._readerTargetStory; } const pages=model.pages; if(!pages.length)return;
  const total=pages.length;
  state.readerPage=Math.max(0,Math.min(state.readerPage,total-1));
  const spread=document.querySelector("#spread");
  if(state.readerView==="spread") {
    const spreadStart=Math.floor(state.readerPage/2)*2;
    state.readerPage=spreadStart;
    $("#reader-page").textContent=`${String(spreadStart+1).padStart(2,"0")}–${String(Math.min(spreadStart+2,total)).padStart(2,"0")} / ${String(total).padStart(2,"0")}`;
    $("#reader-status").textContent=`SPREAD ${String(Math.floor(spreadStart/2)+1).padStart(2,"0")} / ${String(Math.ceil(total/2)).padStart(2,"0")}`;
    const right=pages[spreadStart+1]||`<section class="page blank-page"><span>WEEKLY</span></section>`;
    spread.classList.remove("single-view"); spread.classList.add("spread-view");
    spread.innerHTML=`${pages[spreadStart]}${right}`;
  } else {
    $("#reader-page").textContent=`${String(state.readerPage+1).padStart(2,"0")} / ${String(total).padStart(2,"0")}`;
    $("#reader-status").textContent=`PAGE ${String(state.readerPage+1).padStart(2,"0")} / ${String(total).padStart(2,"0")}`;
    spread.classList.remove("spread-view"); spread.classList.add("single-view");
    spread.innerHTML=pages[state.readerPage];
  }
  $("#spread").querySelectorAll("[data-reader-target]").forEach(b=>b.onclick=()=>{const idx=Number(b.dataset.readerTarget);const target=model.articleStarts[idx]??0;state.readerPage=state.readerView==="spread"?Math.floor(target/2)*2:target;renderReader()});
  updateReaderViewButtons();
}
function updateReaderViewButtons(){
  document.querySelectorAll("[data-reader-view]").forEach(b=>b.classList.toggle("active",b.dataset.readerView===state.readerView));
}
function setReaderView(view){
  state.readerView=view==="spread"?"spread":"single";
  if(state.readerView==="spread")state.readerPage=Math.floor(state.readerPage/2)*2;
  renderReader();
}

async function loadArticles(){try{const[a,e]=await Promise.all([fetch("data/articles.json?ts="+Date.now()),fetch("data/editorial.json?ts="+Date.now())]);const ad=await a.json();state.articles=ad.articles||[];state.clusters=ad.clusters||[];state.editorial=e.ok?await e.json():null}catch(err){console.warn(err)}state.selected=[];state.readerModel=null;state.articles.forEach(a=>{if(!Array.isArray(a.tags)||!a.tags.length)a.tags=deriveTags(a)});try{const saved=JSON.parse(localStorage.getItem("weekly.selectedTags")||"[]");state.selectedTags=new Set(saved.map(x=>String(x).toUpperCase()))}catch(e){}
try{const savedCustom=JSON.parse(localStorage.getItem("weekly.customTags")||"[]");state.customTags=new Set(savedCustom.map(x=>String(x).toUpperCase()))}catch(e){}}
function updateDash(){$("#source-stat").textContent=`${state.sources.filter(s=>s.enabled!==false).length} SOURCES`;$(`#found-stat`).textContent=`${state.articles.filter(isUsableArticle).length} STORIES`;$(`#selected-stat`).textContent=`${state.selected.length} SELECTED`}
async function load(){await Promise.all([loadArticles(),refreshSources()]);renderAll()}
function renderAll(){renderSources();renderTags();renderArticles();renderMagazine();updateDash()}
document.querySelectorAll("[data-reader-view]").forEach(b=>b.onclick=()=>setReaderView(b.dataset.readerView));document.querySelectorAll(".nav-btn").forEach(b=>b.onclick=()=>show(b.dataset.screen));document.querySelectorAll("[data-go]").forEach(b=>b.onclick=()=>show(b.dataset.go));const topicInput=$("#custom-topic-input");const addTopicBtn=$("#add-custom-topic");if(addTopicBtn&&topicInput){const submitTopic=()=>{if(addCustomTopic(topicInput.value))topicInput.value=""};addTopicBtn.onclick=submitTopic;topicInput.addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();submitTopic()}})}document.querySelectorAll("[data-topic]").forEach(b=>b.onclick=()=>addCustomTopic(b.dataset.topic));$("#generate").onclick=()=>{state.selected=chooseRandomStories(candidatePool());state.shuffled=false;state.readerModel=null;renderArticles();renderMagazine();show("magazine")};$("#reshuffle").onclick=()=>{state.selected=chooseRandomStories(candidatePool());state.shuffled=false;state.readerModel=null;renderArticles();renderMagazine()};$("#back-to-articles").onclick=()=>show("articles");$("#open-reader").onclick=()=>{state.readerPage=0;show("reader");requestAnimationFrame(()=>renderReader())};$("#close-reader").onclick=()=>{if(readerEl.classList.contains("reader-fullscreen"))exitReaderFullscreen();show("magazine")};$("#prev-page").onclick=()=>{const total=totalReaderPages();const step=state.readerView==="spread"?2:1;state.readerPage=(state.readerPage-step+total)%total;if(state.readerView==="spread")state.readerPage=Math.floor(state.readerPage/2)*2;renderReader()};$("#next-page").onclick=()=>{const total=totalReaderPages();const step=state.readerView==="spread"?2:1;state.readerPage=(state.readerPage+step)%total;if(state.readerView==="spread")state.readerPage=Math.floor(state.readerPage/2)*2;renderReader()};$("#add-source").onclick=addSource;$("#refresh-sources").onclick=refreshSources;const readerEl=$("#reader");
const fullscreenBtn=$("#fullscreen-reader");
async function enterReaderFullscreen(){
  readerEl.classList.add("reader-fullscreen");
  try{if(!document.fullscreenElement && readerEl.requestFullscreen) await readerEl.requestFullscreen();}catch(err){console.warn("Fullscreen API unavailable",err)}
  fullscreenBtn.textContent="EXIT FULLSCREEN ✕";
}
async function exitReaderFullscreen(){
  try{if(document.fullscreenElement && document.exitFullscreen) await document.exitFullscreen();}catch(err){console.warn("Could not exit fullscreen",err)}
  readerEl.classList.remove("reader-fullscreen");
  fullscreenBtn.textContent="FULLSCREEN ⛶";
}
fullscreenBtn.onclick=()=>readerEl.classList.contains("reader-fullscreen")?exitReaderFullscreen():enterReaderFullscreen();
document.addEventListener("fullscreenchange",()=>{
  const active=!!document.fullscreenElement;
  readerEl.classList.toggle("reader-fullscreen",active || readerEl.classList.contains("reader-fullscreen"));
  if(!active && !document.fullscreenElement){readerEl.classList.remove("reader-fullscreen");fullscreenBtn.textContent="FULLSCREEN ⛶";}
});
document.addEventListener("keydown",e=>{if(!$("#reader").classList.contains("active"))return;if(e.key==="Escape" && readerEl.classList.contains("reader-fullscreen")){exitReaderFullscreen();return;}if(e.key==="ArrowLeft")$("#prev-page").click();if(e.key==="ArrowRight")$("#next-page").click()});const d=new Date();$("#today").textContent=d.toLocaleDateString("es-CL",{day:"2-digit",month:"short",year:"numeric"}).toUpperCase();$("#issue-date").textContent=$("#today").textContent;load();
