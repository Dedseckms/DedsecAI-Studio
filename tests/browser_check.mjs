import {spawn} from 'node:child_process';
import {writeFile,open} from 'node:fs/promises';
const log=await open('/tmp/qwen-panel-cdp.log','w');
const chrome=spawn('/usr/bin/google-chrome-stable',['--headless','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-port=19236','--remote-debugging-address=127.0.0.1','--user-data-dir=/tmp/qwen-panel-cdp','about:blank'],{stdio:['ignore',log.fd,log.fd]});
let ws;
try {
  let target;
  for(let i=0;i<60;i++){try{const pages=await(await fetch('http://127.0.0.1:19236/json/list')).json();target=pages.find(p=>p.type==='page');if(target)break;}catch{}await new Promise(r=>setTimeout(r,100));}
  if(!target)throw Error('Chrome did not start');
  ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});
  let id=0;const pending=new Map();
  ws.onmessage=event=>{const d=JSON.parse(event.data);if(d.method==='Runtime.exceptionThrown')console.log('browser exception',JSON.stringify(d.params.exceptionDetails));if(d.id&&pending.has(d.id)){const [r,j]=pending.get(d.id);pending.delete(d.id);d.error?j(Error(JSON.stringify(d.error))):r(d.result);}};
  function call(method,params={}){return new Promise((r,j)=>{const n=++id;pending.set(n,[r,j]);ws.send(JSON.stringify({id:n,method,params}));});}
  async function evaluate(expression){const result=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(result.exceptionDetails)throw Error(JSON.stringify(result.exceptionDetails));return result.result.value;}
  await call('Page.enable');await call('Runtime.enable');
  await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1100,deviceScaleFactor:1,mobile:false});
  await call('Page.navigate',{url:'http://127.0.0.1:1240/#library'});
  for(let i=0;i<100;i++){if(await evaluate("document.querySelectorAll('.model-card').length>=36"))break;await new Promise(r=>setTimeout(r,100));}
  if(!await evaluate("document.title.includes('DedsecAI Studio')"))throw Error('Branding missing');
  if(!await evaluate("document.querySelectorAll('.model-card').length>=36"))throw Error('Catalog missing');
  for(let i=0;i<40;i++){if(await evaluate("[...document.getElementById('family-filter').options].some(x=>x.value==='Kimi')"))break;await new Promise(r=>setTimeout(r,100));}
  await evaluate("document.getElementById('family-filter').value='Kimi';document.getElementById('family-filter').dispatchEvent(new Event('change'))");
  console.log('filter state',await evaluate("({cards:document.querySelectorAll('.model-card').length,value:document.getElementById('family-filter').value,options:[...document.getElementById('family-filter').options].map(o=>o.value),text:document.getElementById('models').textContent.slice(0,400)})"));
  if(!await evaluate("document.querySelectorAll('.model-card').length===3&&document.getElementById('models').textContent.includes('СЛИШКОМ ВЕЛИКА')"))throw Error('Kimi sizing/filter failed');
  let shot=await call('Page.captureScreenshot',{format:'png'});await writeFile('/tmp/dedsecai-catalog.png',Buffer.from(shot.data,'base64'));
  await evaluate("document.getElementById('add-model').click();document.getElementById('hub-query').value='unsloth/DeepSeek-R1-0528-Qwen3-8B-GGUF';document.getElementById('hub-search').click()");
  for(let i=0;i<150;i++){if(await evaluate("!document.getElementById('hub-files').hidden&&document.getElementById('hub-variant').options.length>1"))break;await new Promise(r=>setTimeout(r,100));}
  if(!await evaluate("document.getElementById('hub-variant').options.length>1"))throw Error('HF inspect UI failed');
  shot=await call('Page.captureScreenshot',{format:'png'});await writeFile('/tmp/dedsecai-import.png',Buffer.from(shot.data,'base64'));
  await evaluate("document.getElementById('close-import').click();location.hash='filters'");
  for(let i=0;i<80;i++){if(await evaluate("document.querySelectorAll('#policy-topics input').length===5"))break;await new Promise(r=>setTimeout(r,100));}
  if(!await evaluate("!document.getElementById('filters-view').hidden&&document.querySelectorAll('#policy-topics input').length===5"))throw Error('Filter settings missing');
  shot=await call('Page.captureScreenshot',{format:'png'});await writeFile('/tmp/dedsecai-filters.png',Buffer.from(shot.data,'base64'));
  await evaluate("location.hash='system'");await new Promise(r=>setTimeout(r,200));
  if(!await evaluate("document.querySelectorAll('.hardware-card').length===4"))throw Error('Hardware missing');
  await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  if(!await evaluate('document.documentElement.scrollWidth<=innerWidth'))throw Error('Mobile overflow');
  console.log(JSON.stringify({branding:true,catalog:true,kimiTooLarge:true,hfVariants:true,filterSettings:true,hardware:true,mobileOverflow:false}));
}finally{if(ws)ws.close();chrome.kill('SIGTERM');await log.close();}
