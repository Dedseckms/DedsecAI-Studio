'use strict';
const $ = id => document.getElementById(id);
let state = null, modelSignature = '', lastJob = '', recentSignature = '', polling = false;
let toastTimer;
const jobTitles = {image_download_preset:'Скачиваем image-модель и компоненты',text_stop:'Выгружаем модель собеседника',image_hf_download:'Скачиваем image-модель из Hugging Face',image_use:'Подготавливаем image-модель: скачивание, запуск и проверка',image_pick:'Выбери файл image-модели',profile:'Применяем контекст',image_setup:'Устанавливаем движок изображений',image_start:'Загружаем image-модель',image_stop:'Останавливаем image-сервер',image_generate:'Рисуем изображение',chat:'Собеседник отвечает',start:'Запускаем сервер',stop:'Останавливаем сервер',restart:'Перезапускаем сервер',use:'Переключаем модель',download:'Скачиваем и проверяем модель',bench:'Измеряем скорость',choose:'Выбери папку проекта',choose_file:'Выбери GGUF',hf_download:'Скачиваем GGUF из Hugging Face',url_download:'Скачиваем GGUF по ссылке',local_import:'Добавляем локальную модель',setup_runtime:'Устанавливаем llama.cpp',setup_pi:'Устанавливаем Pi',pi:'Открываем Pi'};
function toast(message, error = false) { const el=$('toast'); el.textContent=message; el.className='toast'+(error?' error':''); el.hidden=false; clearTimeout(toastTimer); toastTimer=setTimeout(()=>el.hidden=true,6000); }
function node(tag, className, text) { const el=document.createElement(tag); if(className)el.className=className; if(text!==undefined)el.textContent=text; return el; }
function button(text, callback, cls='secondary') { const el=node('button','button '+cls,text); el.type='button'; el.dataset.jobButton='true'; el.addEventListener('click',callback); return el; }
async function action(name, args={}) {
  if(!state) return;
  try {
    const r=await fetch('/api/action',{method:'POST',headers:{'Content-Type':'application/json','X-Qwen-Token':state.csrf},body:JSON.stringify({action:name,...args})});
    const data=await r.json(); if(!r.ok)throw new Error(data.error||'Не удалось выполнить действие.');
    state.job=data.job; renderJob(); disableActions(); await refresh();
  } catch(error) { if($('project-dialog').open)$('project-error').textContent=error.message; else toast(error.message,true); }
}
function renderModels() {
  const signature=JSON.stringify([state.selected,state.models,document.getElementById('model-search')?.value,document.getElementById('family-filter')?.value,document.getElementById('fit-filter')?.checked]);
  if(signature===modelSignature)return; modelSignature=signature;
  const fragment=document.createDocumentFragment();
  const needle=(document.getElementById('model-search')?.value||'').toLowerCase();const family=document.getElementById('family-filter')?.value||'';const fits=document.getElementById('fit-filter')?.checked;let visibleCount=0;
  for(const m of state.models) {
    if(needle&&!m.name.toLowerCase().includes(needle))continue;if(family&&m.family!==family)continue;if(fits&&m.tier==='too_large')continue;visibleCount++;
    const chosen=m.id===state.selected;
    const card=node('article','model-card'+(chosen?' selected':''));
    const top=node('div','card-top'); top.append(node('span','model-kind',(m.family||'Custom')+' · '+(m.tier==='too_large'?'СЛИШКОМ ВЕЛИКА':m.tier==='cpu'?'CPU':m.cpu_risk?'GPU + CPU':'GPU')));
    top.append(node('span','badge'+(chosen?' selected':m.cpu_risk?' risk':''),chosen?'Выбрана':m.installed?'Установлена':m.cpu_risk?'Компромисс':'Доступна для загрузки')); card.append(top);
    card.append(node('h3','',m.name),node('div','model-meta',`${m.gib.toLocaleString('ru-RU')} ГиБ · контекст ${(m.ctx/1024).toLocaleString('ru-RU')}K · KV ${m.cache==='q8_0'?'Q8':'Q4'}`),node('p','model-why',m.why));
    const bottom=node('div','card-bottom'); bottom.append(node('span','model-speed',m.speed));
    if(!m.installed){const b=button(m.disk_fits?'↓ Скачать':'Мало места',()=>action('download',{id:m.id}));b.dataset.diskBlocked=String(!m.disk_fits);bottom.append(b);}
    else if(m.kind==='image')bottom.append(button('В изображения',()=>action('image_import',{path:m.path})));
    else if(chosen)bottom.append(button('↗ Замерить',()=>action('bench')));
    else {const b=button(m.tier==='too_large'?'Не помещается':m.cpu_risk?'Выбрать с CPU':'Выбрать',()=>action('use',{id:m.id,allow_cpu:m.cpu_risk}),'light');b.dataset.diskBlocked=String(m.tier==='too_large');bottom.append(b);}
    bottom.append(button('Настроить',()=>openProfile(m)));card.append(bottom); const details=node('details'); details.append(node('summary','','Для каких задач'),node('p','',m.tasks));card.append(details);fragment.append(card);
  }
  $('models').replaceChildren(fragment);$('model-count').textContent=state.models.length;document.getElementById('catalog-count').textContent=visibleCount+' из '+state.models.length;
}
function renderProjects() {
  const sig=JSON.stringify(state.projects);if(sig===recentSignature)return;recentSignature=sig;
  const fragment=document.createDocumentFragment();
  if(!state.projects.length)fragment.append(node('p','recent-empty','Открытые проекты появятся здесь.'));
  for(const path of state.projects) {const b=node('button','recent-project','▱  '+path);b.title=path;b.addEventListener('click',()=>{$('project-path').value=path;$('project-error').textContent='';});fragment.append(b);}
  $('recent-projects').replaceChildren(fragment);
}
function disableActions() {
  const busy=['running','cancelling'].includes(state?.job?.status);
  for(const id of ['choose-folder','launch-pi'])$(id).disabled=busy;
  $('start').disabled=busy||state.running;$('stop').disabled=false;$('restart').disabled=false;
  for(const b of document.querySelectorAll('[data-job-button]'))b.disabled=b.dataset.diskBlocked==='true';
}
function renderJob() {
  const j=state.job;$('operation').hidden=!j||(!['running','cancelling'].includes(j.status)&&Date.now()/1000-(j.finished||0)>15);if(!j)return;
  const running=['running','cancelling'].includes(j.status);$('job-title').textContent=running?jobTitles[j.action]:j.status==='error'?'Операция не завершена':j.status==='cancelled'?'Отменено':'Готово';
  $('job-dot').className='pulse'+(running?'':j.status==='error'?' error':' done');
  $('job-time').textContent=Math.round((j.finished||Date.now()/1000)-j.started)+' с';
  $('job-message').textContent=j.error||(running?'Можно остановить операцию или выбрать другую модель.':j.result?.message||'Операция завершена.');
  $('job-log').textContent=state.operation_log||'Журнал пока пуст.';
  const key=j.id+':'+j.status;
  if(key!==lastJob && !running) {
    lastJob=key;
    if(j.action==='choose'&&j.status==='done'&&j.result?.path){$('project-path').value=j.result.path;$('project-error').textContent='';$('project-path').focus();}
    if(j.action==='pi'&&j.status==='done'){$('project-dialog').close();toast('Pi открыт в папке '+j.result.path);}
    if(j.status==='error'){toast(j.error,true);if($('project-dialog').open)$('project-error').textContent=j.error;}
  }
}
function render() {
  const m=state.models.find(m=>m.id===state.selected);
  $('server-status').textContent=state.running?'● Собеседник работает':state.resources?.image?.state==='ready'?'● Работает генератор':'○ Модели выгружены';$('server-status').className='status'+(state.running?' online':'');
  $('active-model').textContent=m?.name||'Модель не выбрана';$('active-description').textContent=m?.tasks||'';
  $('context').textContent=m?m.ctx.toLocaleString('ru-RU')+' токенов':'—';$('speed').textContent=m?.speed||'—';
  $('speed-note').textContent=m?.speed.includes('ЗАМЕР')?'Результат короткого запроса на твоём ПК':'Предварительная оценка; сделай замер после запуска';
  const g=state.gpu;
  $('gpu-memory').replaceChildren(document.createTextNode(g?(g.used/1024).toFixed(1)+' ГБ ':'— '),node('small','',g?'/ '+(g.total/1024).toFixed(0)+' ГБ':''));
  $('gpu-bar').value=g?g.used/g.total*100:0;$('gpu-name').textContent=g?g.name+(g.temp==null?'':' · '+g.temp+' °C'):'Дискретная VRAM не обнаружена — доступен CPU';$('gpu-load').textContent=g?g.load+'% нагрузки':'';
  $('server-log').textContent=state.server_log||'Сервер ещё не записал журнал.';
  renderModels();renderProjects();renderJob();disableActions();window.dispatchEvent(new Event("dedsecai-state"));
}
async function refresh() {
  if(polling)return;polling=true;
  try {const response=await fetch('/api/state');if(!response.ok)throw new Error('Панель недоступна');state=await response.json();render();}
  catch(error){$('server-status').textContent='Нет связи с панелью';$('server-status').className='status';}
  finally{polling=false;}
}
function openProject() {if(!state)return;$('project-error').textContent='';if(!$('project-path').value)$('project-path').value=state.projects[0]||state.default_project;$('project-dialog').showModal();}
$('start').addEventListener('click',()=>action('start'));$('stop').addEventListener('click',()=>action('stop'));$('restart').addEventListener('click',()=>action('restart'));
$('open-pi').addEventListener('click',openProject);$('side-pi').addEventListener('click',openProject);
$('close-dialog').addEventListener('click',()=>$('project-dialog').close());$('cancel-dialog').addEventListener('click',()=>$('project-dialog').close());
$('choose-folder').addEventListener('click',()=>{$('project-error').textContent='';action('choose');});
$('launch-pi').addEventListener('click',()=>{const path=$('project-path').value.trim();if(!path){$('project-error').textContent='Сначала выбери папку проекта.';return;}action('pi',{path});});
$('project-path').addEventListener('keydown',event=>{if(event.key==='Enter')$('launch-pi').click();});
refresh();setInterval(refresh,2000);
