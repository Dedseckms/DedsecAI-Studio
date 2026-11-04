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
  await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
  await call('Page.navigate',{url:'http://127.0.0.1:1240/#chat'});
  for(let i=0;i<100;i++){if(await evaluate("typeof state!=='undefined'&&state&&typeof cOpen==='function'"))break;await new Promise(r=>setTimeout(r,100));}
  await evaluate("cOpen('11111111111111111111111111111111')");
  for(let i=0;i<80;i++){if(await evaluate("document.querySelectorAll('.chat-message').length===140"))break;await new Promise(r=>setTimeout(r,100));}
  await new Promise(r=>setTimeout(r,200));
  console.log('layout',await evaluate("({body:document.documentElement.scrollHeight,viewport:innerHeight,main:document.getElementById('chat-view').getBoundingClientRect().toJSON(),list:[document.getElementById('conversation-list').clientHeight,document.getElementById('conversation-list').scrollHeight],messages:[document.getElementById('chat-messages').clientHeight,document.getElementById('chat-messages').scrollHeight]})"));
  if(!await evaluate("document.documentElement.scrollHeight<=innerHeight+1&&document.getElementById('chat-messages').scrollHeight>document.getElementById('chat-messages').clientHeight&&document.getElementById('conversation-list').scrollHeight>document.getElementById('conversation-list').clientHeight"))throw Error('Chat is not bounded with independent overflow');
  await evaluate("document.getElementById('conversation-list').scrollTop=200;document.getElementById('chat-messages').scrollTop=600");await new Promise(r=>setTimeout(r,1100));
  if(!await evaluate("document.getElementById('conversation-list').scrollTop===200&&Math.abs(document.getElementById('chat-messages').scrollTop-600)<2&&scrollY===0"))throw Error('Polling reset independent scroll positions');
  const point=await evaluate("(()=>{const r=document.getElementById('chat-messages').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})()");
  await call('Input.dispatchMouseEvent',{type:'mouseWheel',...point,deltaY:500,deltaX:0});await new Promise(r=>setTimeout(r,300));
  if(!await evaluate("document.getElementById('conversation-list').scrollTop===200&&document.getElementById('chat-messages').scrollTop>600&&scrollY===0"))throw Error('Message wheel moved conversation list or document');
  await evaluate("document.getElementById('chat-messages').scrollTop=document.getElementById('chat-messages').scrollHeight");
  await call('Input.dispatchMouseEvent',{type:'mouseWheel',...point,deltaY:500,deltaX:0});await new Promise(r=>setTimeout(r,200));
  if(!await evaluate("scrollY===0&&document.getElementById('conversation-list').scrollTop===200"))throw Error('Scroll chained to page');
  await evaluate("document.querySelector('[data-conversation-delete=\"11111111111111111111111111111111\"]').click()");
  if(!await evaluate("document.getElementById('chat-delete-dialog').open"))throw Error('Delete confirmation absent');
  await evaluate("document.getElementById('chat-delete-cancel').click()");
  if(!await evaluate("document.querySelector('[data-conversation-delete=\"11111111111111111111111111111111\"]')"))throw Error('Cancel deleted chat');
  await evaluate("document.querySelector('[data-conversation-delete=\"11111111111111111111111111111111\"]').click();document.getElementById('chat-delete-confirm').click()");
  for(let i=0;i<80;i++){if(await evaluate("!document.getElementById('chat-delete-dialog').open&&!document.querySelector('[data-conversation-delete=\"11111111111111111111111111111111\"]')"))break;await new Promise(r=>setTimeout(r,100));}
  if(!await evaluate("cCurrent!=='11111111111111111111111111111111'&&!document.querySelector('[data-conversation-delete=\"11111111111111111111111111111111\"]')"))throw Error('Active chat deletion failed');
  if(!await evaluate("cGet('/api/chat/search?q='+encodeURIComponent('суперчатбезповтора')).then(d=>d.results.length===0)"))throw Error('Deleted chat leaked into search');
  await evaluate("document.getElementById('chat-trash-open').click()");
  for(let i=0;i<60;i++){if(await evaluate("document.querySelector('#chat-trash-list button')"))break;await new Promise(r=>setTimeout(r,100));}
  await evaluate("document.querySelector('#chat-trash-list button').click()");
  for(let i=0;i<60;i++){if(await evaluate("document.querySelector('[data-conversation-delete=\"11111111111111111111111111111111\"]')"))break;await new Promise(r=>setTimeout(r,100));}
  await evaluate("document.getElementById('chat-trash-close').click();cOpen('11111111111111111111111111111111')");
  for(let i=0;i<60;i++){if(await evaluate("document.querySelectorAll('.chat-message').length===140"))break;await new Promise(r=>setTimeout(r,100));}
  if(!await evaluate("document.querySelectorAll('.chat-message').length===140"))throw Error('Restore lost messages');
  let shot=await call('Page.captureScreenshot',{format:'png'});await writeFile('/tmp/dedsecai-chat-scroll-desktop.png',Buffer.from(shot.data,'base64'));
  await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await new Promise(r=>setTimeout(r,250));
  if(!await evaluate("document.documentElement.scrollWidth<=innerWidth&&getComputedStyle(document.getElementById('conversation-sidebar')).visibility==='hidden'&&document.querySelector('.chat-composer').getBoundingClientRect().bottom<=innerHeight+1"))throw Error('Mobile chat layout or composer failed');
  await evaluate("document.getElementById('chat-list-toggle').click()");
  if(!await evaluate("document.querySelector('.chat-workspace').classList.contains('chats-open')"))throw Error('Mobile chat drawer failed');
  await evaluate("document.querySelector('.conversation-entry').click()");
  if(!await evaluate("!document.querySelector('.chat-workspace').classList.contains('chats-open')"))throw Error('Mobile drawer did not close on selection');
  shot=await call('Page.captureScreenshot',{format:'png'});await writeFile('/tmp/dedsecai-chat-scroll-mobile.png',Buffer.from(shot.data,'base64'));
  console.log(JSON.stringify({independentScrolling:true,pollingPreservesScroll:true,deleteConfirmation:true,deleteAndRestore:true,deletedSearchExcluded:true,mobileDrawer:true}));
}finally{if(ws)ws.close();chrome.kill('SIGTERM');await log.close();}
