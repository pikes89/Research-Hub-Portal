var HN={'mac-b':"Mac B (alternate)",'mac-a':"Mac A (primary)"};
function hostName(h){return h?(HN[h]||h):'-'}
(function(){
var esc=function(s){return String(s).replace(/[&<>]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;'}[c]})};
var top=document.querySelector('main .top'),bar=document.createElement('div');bar.id='hostbar';if(top)top.parentNode.insertBefore(bar,top);
function ago(t){var s=Math.max(0,Math.floor(Date.now()/1000-t));return s<90?s+' s':s<5400?Math.round(s/60)+' min':Math.round(s/3600)+' h'}
function chip(h,b,d,me){
 var lk=d.lock,run=lk&&lk.host===h&&(Date.now()/1000-lk.renewed)<1500,off=!b||(Date.now()/1000-b.ts)>1200,bad=b&&b.issues&&b.issues.length,cls=run?'run':off?'off':bad?'bad':'',
 st=run?'Running now'+((lk.since)?' · '+ago(lk.since):''):off?'Offline (no heartbeat)':bad?'Problem: '+esc(b.issues[0]):'Idle · ready';
 var lr=b&&b.last_run?'Last run '+ago((b.last_run.finished||b.last_run.started)/1000)+' ago: '+esc(b.last_run.result)+', '+b.last_run.files+' files':'No run yet';
 return'<div class="hc '+cls+(me?' me':'')+'"><b>'+esc(hostName(h))+'</b><span class="st"><span class="dot"></span>'+st+'</span><small>'+(b?(b.role||'')+' · ':'')+lr+'</small></div>'}
function f(){fetch('/api/bots').then(function(r){return r.json()}).then(function(d){
 if(!d.me)return;document.documentElement.dataset.host=d.me;try{localStorage.setItem('rh_host',d.me)}catch(e){}
 var S=window.RH_STATUS||{};if(S.state==='running'&&d.mine){d.lock={host:d.me,renewed:Date.now()/1000,since:(S.started||0)/1000||null}}
 var first=d.me,second=d.peer;
 bar.innerHTML=chip(first,d.mine,d,true)+(second?chip(second,d.theirs,d,false):'')}).catch(function(){})}
f();setInterval(f,10000)})();
