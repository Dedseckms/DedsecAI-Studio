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
  await call('Page.navigate',{url:(process.env.STUDIO_URL||'http://127.0.0.1:1240')+'/#library'});
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
  await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1100,deviceScaleFactor:1,mobile:false});
  await evaluate("document.getElementById('family-filter').value='';document.getElementById('family-filter').dispatchEvent(new Event('change'));location.hash='overview'");
  await evaluate("openProfile(state.models.find(x=>x.native_ctx>=32768))");
  if(!await evaluate("document.getElementById('profile-dialog').open&&Number(document.getElementById('profile-context').max)>=32768"))throw Error('Context controls missing');
  shot=await call('Page.captureScreenshot',{format:'png'});await writeFile('/tmp/dedsecai-context.png',Buffer.from(shot.data,'base64'));
  await evaluate("document.getElementById('profile-close').click();location.hash='images'");await new Promise(r=>setTimeout(r,600));
  if(!await evaluate("!document.getElementById('images-view').hidden&&document.getElementById('overview').hidden"))throw Error('Image route failed');
  await evaluate("document.getElementById('image-tab-catalog').click()");
  for(let i=0;i<80;i++){if(await evaluate("document.querySelectorAll('.image-model-card').length>=3"))break;await new Promise(r=>setTimeout(r,100));}
  if(!await evaluate("document.querySelectorAll('.image-model-card').length>=3&&!document.getElementById('image-advanced').open&&document.getElementById('image-pick').textContent.includes('Выбрать файл')"))throw Error('Simple image library missing');
  await evaluate("document.getElementById('image-library-search').value='SDXL';document.getElementById('image-library-search').dispatchEvent(new Event('input'))");
  if(!await evaluate("document.querySelectorAll('.image-model-card').length===1"))throw Error('Image search failed');
  await evaluate("document.getElementById('image-library-search').value='';document.getElementById('image-library-search').dispatchEvent(new Event('input'))");
  if(!await evaluate("document.getElementById('resource-text')&&document.getElementById('resource-image')"))throw Error('Resource status missing');
  await evaluate("document.getElementById('image-uncensored').checked=true;document.getElementById('image-uncensored').dispatchEvent(new Event('change'))");
  if(!await evaluate("document.querySelectorAll('.image-model-card').length>=4&&[...document.querySelectorAll('.image-model-card h3')].every(n=>n.textContent.includes('Uncensored'))"))throw Error('Uncensored catalog filter failed');
  await evaluate("document.getElementById('image-uncensored').checked=false;document.getElementById('image-uncensored').dispatchEvent(new Event('change'))");
  await evaluate("document.getElementById('image-tab-hub').click();document.getElementById('image-hub-query').value='abenzerps/Qwen-Image-2.1-Uncensored-Quantized';document.getElementById('image-hub-search').click()");
  for(let i=0;i<120;i++){if(await evaluate("!document.getElementById('image-hub-files').hidden&&document.getElementById('image-hub-variant').options.length>=4"))break;await new Promise(r=>setTimeout(r,100));}
  if(!await evaluate("document.getElementById('image-hub-variant').options.length>=4&&[...document.getElementById('image-hub-variant').options].every(o=>!o.textContent.includes('MLX'))"))throw Error('Image HF variants or format filtering failed');
  await evaluate("document.getElementById('image-tab-catalog').click()");
  if(!process.env.STUDIO_URL){
    await evaluate("document.querySelector('[data-gallery-delete=\"ffffffffffffffffffffffffffffffff.png\"]').click()");
    if(!await evaluate("document.getElementById('gallery-delete-dialog').open"))throw Error('Delete confirmation missing');
    await evaluate("document.getElementById('gallery-delete-cancel').click()");
    if(!await evaluate("document.querySelector('[data-gallery-delete=\"ffffffffffffffffffffffffffffffff.png\"]')"))throw Error('Cancel removed fixture');
    await evaluate("document.querySelector('[data-gallery-delete=\"ffffffffffffffffffffffffffffffff.png\"]').click();document.getElementById('gallery-delete-confirm').click()");
    for(let i=0;i<80;i++){if(await evaluate("!document.getElementById('gallery-delete-dialog').open&&!document.querySelector('[data-gallery-delete=\"ffffffffffffffffffffffffffffffff.png\"]')"))break;await new Promise(r=>setTimeout(r,100));}
    if(!await evaluate("!document.querySelector('[data-gallery-delete=\"ffffffffffffffffffffffffffffffff.png\"]')"))throw Error('Gallery delete failed');
    await evaluate("document.getElementById('gallery-trash-toggle').click();[...document.querySelectorAll('.gallery-card')].find(c=>c.textContent.includes('QA gallery lifecycle fixture')).querySelector('button').click()");
    for(let i=0;i<80;i++){if(await evaluate("![...document.querySelectorAll('.gallery-card')].some(c=>c.textContent.includes('QA gallery lifecycle fixture'))"))break;await new Promise(r=>setTimeout(r,100));}
    await evaluate("document.getElementById('gallery-trash-toggle').click()");
    if(!await evaluate("document.querySelector('[data-gallery-delete=\"ffffffffffffffffffffffffffffffff.png\"]')"))throw Error('Gallery restore failed');
  }
  shot=await call('Page.captureScreenshot',{format:'png'});await writeFile('/tmp/dedsecai-images.png',Buffer.from(shot.data,'base64'));
  await evaluate("location.hash='chat'");await new Promise(r=>setTimeout(r,400));
  if(!await evaluate("document.getElementById('chat-images').accept.includes('image/png')"))throw Error('Image attachments missing');
  shot=await call('Page.captureScreenshot',{format:'png'});await writeFile('/tmp/dedsecai-chat-next.png',Buffer.from(shot.data,'base64'));
  await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  for(const route of ['chat','images','memory','system','overview']){await evaluate("location.hash="+JSON.stringify(route));await new Promise(r=>setTimeout(r,150));if(!await evaluate('document.documentElement.scrollWidth<=innerWidth'))throw Error('Mobile overflow on '+route);}
  console.log(JSON.stringify({branding:true,catalog:true,kimiTooLarge:true,hfVariants:true,filterSettings:true,hardware:true,mobileOverflow:false}));
}finally{if(ws)ws.close();chrome.kill('SIGTERM');await log.close();}
