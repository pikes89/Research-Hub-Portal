const CAP=__CAP__;
const NAMES={AI:'Artificial Intelligence',DataMining:'Data Mining',PrivateInsurancePH:'Private Insurance PH',GovernmentInsurancePH:'Government Insurance PH',ForeignInsurancePH:'Foreign Insurance PH',AIInHealthcare:'AI in Healthcare'};
function nm(k){return NAMES[k]||k.replace(/([a-z])([A-Z])/g,'$1 $2')}
let TOP='',YR='',STF='',REG='',SHOW={},OP={};
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function stOf(r){return r.got==2?(r.nas&&r.cloud?'On NAS · Drive':r.nas?'On NAS':r.cloud?'On Drive':'On Mac'):(r.got?'Partial':'Missing')}
function row(r){const L=(f,l)=>f?`<a href="${SMB}${encodeURI(f)}">${l}</a>`:'';
return `<tr><td>${r.u?`<a href="https://portal.example.com/statistics/${r.u.split('/')[0]}/" target="_blank">${esc(r.t)}</a>`:esc(r.t)}</td><td class="st${r.got==2?' ok':''}">${stOf(r)}</td><td class="note">${L(r.pdf,'PDF')} ${L(r.xlsx,'XLSX')} <a href="${PL}/documents?query=${encodeURIComponent(r.t)}" target="_blank">Paperless</a></td></tr>`}
function tbl(rows){return `<table><thead><tr><th>Title</th><th>Status</th><th>Open</th></tr></thead><tbody>${rows.map(row).join('')}</tbody></table>`}
function more(key,total,shown){return total>shown?`<button class="btn sm" onclick="SHOW['${key}']=(SHOW['${key}']||25)+25;f()">Show ${Math.min(25,total-shown)} more (${total-shown} left)</button>`:''}
function f(){
const q=document.getElementById('s').value.toLowerCase().trim(),L=document.getElementById('lib'),day=Date.now()/1000-86400;
if(q){const m=D.filter(r=>(r.t+' '+r.topic+' '+r.tags+' '+r.reg+' '+r.ctry+' '+r.ind).toLowerCase().includes(q)).sort((a,b)=>b.added-a.added),n=SHOW.q||25;
L.innerHTML=`<div class="crumb">Search “${esc(q)}” · ${m.length} found</div>`+tbl(m.slice(0,n))+more('q',m.length,n);return}
if(!TOP){const DR=REG?D.filter(r=>r.reg===REG||r.ctry&&(REGC[REG]||[]).includes(r.ctry)):D,by={};DR.forEach(r=>{(by[r.topic]=by[r.topic]||[]).push(r)});
const recent=DR.filter(r=>r.added).sort((a,b)=>b.added-a.added).slice(0,10),regs=['Worldwide',...REGS.filter(x=>x!=='Worldwide')].filter(x=>D.some(r=>r.reg===x||r.ctry&&(REGC[x]||[]).includes(r.ctry)));
const card=k=>{const a=by[k],n=Math.max(a.filter(r=>r.pdf).length,a.filter(r=>r.xlsx).length),today=a.filter(r=>r.added>day).length,miss=a.filter(r=>r.got<2).length,pct=Math.min(100,Math.round(n/CAP*100));
return `<div class="tcard" onclick="TOP='${k}';YR='';STF='';SHOW={};f()"><b>${esc(nm(k))}</b><span class="note">${n} / ${CAP} statistics${today?` · <i class="new">+${today} new</i>`:''}</span><div class="pb"><u style="width:${pct}%"></u></div><span class="note">${miss?miss+' incomplete':'complete'} · ${typeof odCount==='function'?odCount(k):0} open series</span></div>`};
const ind={};Object.keys(by).forEach(k=>{const i=by[k][0].ind||'Other';(ind[i]=ind[i]||[]).push(k)});
const order=[...IND,'Other'].filter(i=>ind[i]);
L.innerHTML=`<div class="filters"><select onchange="REG=this.value;f()"><option value="">All regions</option>${regs.map(x=>`<option${x===REG?' selected':''}>${x}</option>`).join('')}</select><span class="note">Region › Industry › Topic</span></div><div class="sub2">Recently added</div>`+tbl(recent)+order.map(i=>`<div class="sub2">${esc(i)}</div><div class="tgrid">${ind[i].sort((a,b)=>by[b].length-by[a].length).map(card).join('')}</div>`).join('');return}
const all=D.filter(r=>r.topic===TOP),yrs=[...new Set(all.map(r=>r.y))].sort().reverse();
const rows=all.filter(r=>(!REG||r.reg===REG||r.ctry&&(REGC[REG]||[]).includes(r.ctry))&&(!YR||r.y===YR)&&(!STF||(STF==='miss'?r.got<2:STF==='nonas'?!r.nas:!r.cloud))).sort((a,b)=>b.added-a.added);
const g={};rows.forEach(r=>{(g[r.y]=g[r.y]||[]).push(r)});const gy=Object.keys(g).sort().reverse();
L.innerHTML=`<div class="crumb"><a href="#" onclick="TOP='';f();return false">All topics</a> › <b>${esc(nm(TOP))}</b> · ${rows.length} of ${all.length}</div>`+
`<div class="filters"><select onchange="YR=this.value;SHOW={};f()"><option value="">All years</option>${yrs.map(y=>`<option${y===YR?' selected':''}>${y}</option>`).join('')}</select>`+
`<select onchange="STF=this.value;SHOW={};f()"><option value="">Any status</option><option value="miss"${STF==='miss'?' selected':''}>Missing PDF or XLSX</option><option value="nonas"${STF==='nonas'?' selected':''}>Not on NAS</option><option value="nocloud"${STF==='nocloud'?' selected':''}>Not on Drive</option></select></div>`+
gy.map((y,i)=>{const n=SHOW[TOP+y]||25,key=TOP+y,open=key in OP?OP[key]:(i===0||!!YR);
return `<details${open?' open':''} ontoggle="OP['${key}']=this.open"><summary>${y} <span class="note">· ${g[y].length}</span></summary>${tbl(g[y].slice(0,n))}${more(key,g[y].length,n)}</details>`}).join('')}
