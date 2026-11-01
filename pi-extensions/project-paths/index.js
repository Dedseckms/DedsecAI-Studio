import {checkedPaths, failedPath, hint, inventory, missingPath, resultText, simpleTokens, trimFailedHistory} from './guard.mjs';

export default function projectPaths(pi) {
  let enabled = true, strict = false, misses = 0, stopped = false;
  const counted = new Set();
  const discover = process.platform === 'win32' ? 'Get-Location и Get-ChildItem -LiteralPath .' : 'pwd и ls -la .';
  const local = ctx => ctx.model?.provider === 'lmstudio';
  function failure(id, ctx) {
    if (counted.has(id)) return;
    counted.add(id); misses++;
    if (strict && misses >= 4 && !stopped) {
      stopped = true;
      if (ctx.hasUI) ctx.ui.notify('Остановлен перебор несуществующих путей: 4 ошибки подряд. Проверь выбранную папку проекта и продолжи с точным путём.', 'warning');
      queueMicrotask(() => ctx.abort());
    }
  }
  pi.on('before_agent_start', (event, ctx) => {
    misses = 0; stopped = false; counted.clear();
    if (!enabled || !local(ctx)) return;
    return {systemPrompt:event.systemPrompt + `\n\nФАЙЛОВАЯ СИСТЕМА — ПРОВЕРЕННЫЕ ДАННЫЕ\nРабочая папка проекта: ${JSON.stringify(ctx.cwd)}\nРеальные имена в ней (ограниченный список): ${inventory(ctx.cwd)}\nНачинай с ${discover} Используй пути относительно этой папки. Кириллица, регистр и пробелы значимы. Не сокращай и не переводи имена папок. После ENOENT один раз проверь существующего родителя; не пробуй новые выдуманные варианты. Если найти цель не удалось, остановись и кратко уточни путь у пользователя. Для нового файла можно создать новый путь через write; отсутствующий необязательный файл не обязательно является проблемой. Ошибка пути не повод вызывать rm.`};
  });
  pi.on('tool_call', (event, ctx) => {
    if (!enabled || !strict || !local(ctx)) return;
    if (stopped) return {block:true,terminate:true,reason:'Перебор путей остановлен. Нужен точный путь от пользователя.'};
    for (const candidate of checkedPaths(event)) {
      const missing = missingPath(candidate, ctx.cwd);
      if (!missing) continue;
      failure(event.toolCallId, ctx);
      return {block:true,terminate:stopped,reason:hint(ctx.cwd,missing)};
    }
  });
  pi.on('tool_result', (event, ctx) => {
    if (!enabled || !local(ctx)) return;
    if (failedPath(event)) {
      failure(event.toolCallId, ctx);
      const missing = checkedPaths(event).map(p => missingPath(p, ctx.cwd)).find(Boolean);
      return {isError:true,content:[{type:'text',text:missing ? hint(ctx.cwd,missing) : resultText(event.content).slice(0,500)+'\nРабочая папка: '+JSON.stringify(ctx.cwd)+'. Реальные имена: '+inventory(ctx.cwd,16)+'. Не перебирай написания.'}]};
    }
    const tokens = event.toolName === 'bash' ? simpleTokens(event.input.command) : null;
    if (!event.isError && (['read','edit','ls','find','grep'].includes(event.toolName) || ['ls','pwd'].includes(tokens?.[0]))) misses = 0;
  });
  // /reload can leave an older model object alive. Neutralize only the exact
  // superseded sampling profile; do not override unrelated custom sampling.
  pi.on('before_provider_request', (event,ctx) => {
    const p = event.payload;
    if (local(ctx) && p && typeof p === 'object' && p.repeat_penalty === 1.05 && p.dry_multiplier === 0.3) {
      return {...p, repeat_penalty:1.0, dry_multiplier:0.0};
    }
  });
  pi.on('context', (event,ctx) => enabled && local(ctx) ? trimFailedHistory(event.messages) : undefined);
  pi.registerCommand('pathguard', {
    description:'Подсказки путей: /pathguard on, /pathguard off; /pathguard strict — остановка после 4 ошибок',
    handler:async (args,ctx) => {
      if (args.trim()==='off') enabled=false;
      if (args.trim()==='on') {enabled=true;strict=false;}
      if (args.trim()==='strict') {enabled=true;strict=true;}
      misses=0;stopped=false;counted.clear();
      if (ctx.hasUI)ctx.ui.notify('Защита путей: '+(enabled?(strict?'строгая':'подсказки и сокращение ошибок'):'выключена'),'info');
    },
  });
}
