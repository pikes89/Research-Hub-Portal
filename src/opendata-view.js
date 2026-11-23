(function(){
const O=OD,$=id=>document.getElementById(id);let T='',Q='';
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const SRC={wb:'World Bank',owid:'Our World in Data',eurostat:'Eurostat',psa:'PSA OpenSTAT',oecd:'OECD',link:'Link'};
window.odTopicOf=function(k){k=String(k);if(/Insurance/i.test(k))return'InsurancePH';if(/Ransom/i.test(k))return'Ransomware';if(/Warming|gobal/i.test(k))return'GlobalWarming';return k};
window.odCount=function(k){const t=odTopicOf(k);return O.series.filter(s=>s.kind==='data'&&s.status==='ok'&&s.topics.includes(t)).length};
function spark(s){const g=s.h||{},keys=['PHL','WLD'].filter(k=>g[k]&&g[k].length>1);if(!keys.length)return'<span class="note">no PHL/world series</span>';
const all=keys.flatMap(k=>g[k]),xs=all.map(p=>+p[0]),ys=all.map(p=>p[1]),x0=Math.min(...xs),x1=Math.max(...xs),y0=Math.min(...ys),y1=Math.max(...ys);
const X=x=>4+(x-x0)/(x1-x0||1)*152,Y=y=>30-(y-y0)/(y1-y0||1)*26,col={PHL:'var(--teal)',WLD:'var(--violet)'};
return`<svg width="160" height="34" viewBox="0 0 160 34">${keys.map(k=>`<polyline fill="none" stroke="${col[k]}" stroke-width="1.6" points="${g[k].map(p=>X(+p[0]).toFixed(1)+','+Y(p[1]).toFixed(1)).join(' ')}"/>`).join('')}</svg>`}
function last(s,k){const a=(s.h||{})[k];return a&&a.length?a[a.length-1]:null}
function card(s){
if(s.kind==='link')return`<div class="odc"><b><a href="${esc(s.url)}" target="_blank">${esc(s.title)}</a></b><span class="note">Link only · ${esc(s.note)}</span></div>`;
if(s.status!=='ok')return`<div class="odc"><b>${esc(s.title)}</b><span class="note">Not ingested: ${esc(s.status)}</span></div>`;
const p=last(s,'PHL'),w=last(s,'WLD');
return`<div class="odc"><b><a href="${esc(s.url)}" target="_blank">${esc(s.title)}</a></b>${spark(s)}<span class="note">${p?'<i class="ph">PH</i> '+p[1]+' ('+p[0]+') ':''}${w?'<i class="wd">World</i> '+w[1]+' ('+w[0]+')':''}</span><span class="note">${SRC[s.src]} · ${s.n.toLocaleString()} obs · ${s.ymin}–${s.ymax} · fetched ${s.fetched}</span><span class="note lic" title="${esc(s.licence)}">${esc(s.licence)}</span></div>`}
function render(){const L=$('od'),q=Q.toLowerCase().trim();
let ss=O.series.filter(s=>(!T||s.topics.includes(T))&&(!q||(s.title+' '+s.src+' '+s.topics.join(' ')).toLowerCase().includes(q)));
const chips=Object.keys(O.topics).map(k=>{const n=O.series.filter(s=>s.kind==='data'&&s.status==='ok'&&s.topics.includes(k)).length;return`<button class="chip${T===k?' on':''}" data-t="${k}">${esc(O.topics[k])} <span class="note">${n}</span></button>`}).join('');
const ok=O.series.filter(s=>s.kind==='data'&&s.status==='ok');
L.innerHTML=`<div class="odh"><span class="note"><b>${ok.length}</b> open series · <b>${ok.reduce((a,s)=>a+s.n,0).toLocaleString()}</b> observations · ${new Set(ok.map(s=>s.src)).size} sources · built ${esc(O.built)}</span><input id="odq" placeholder="Search open series" value="${esc(Q)}"></div><div class="chips"><button class="chip${T?'':' on'}" data-t="">All</button>${chips}</div><div class="odg">${ss.map(card).join('')||'<span class="note">Nothing matches.</span>'}</div>`;
L.querySelectorAll('.chip').forEach(b=>b.onclick=()=>{T=b.dataset.t;render()});
const i=$('odq');i.oninput=()=>{Q=i.value;const p=i.selectionStart;render();const n=$('odq');n.focus();n.setSelectionRange(p,p)}}
render();if(typeof f==="function")try{f()}catch(e){}
})();
