import { LoopDetector } from './detector.mjs';

export default function antiLoop(pi) {
  let enabled = true;
  let stopped = false;
  let detectors = new Map();
  pi.on('message_start', (event) => {
    if (event.message.role === 'assistant') { detectors = new Map(); stopped = false; }
  });
  pi.on('message_update', (event, ctx) => {
    if (!enabled || stopped || event.message.role !== 'assistant' || event.message.provider !== 'lmstudio') return;
    const e = event.assistantMessageEvent;
    if (!['text_delta', 'thinking_delta', 'toolcall_delta'].includes(e.type) || typeof e.delta !== 'string') return;
    const key = e.type + ':' + e.contentIndex;
    if (!detectors.has(key)) detectors.set(key, new LoopDetector());
    const loop = detectors.get(key).push(e.delta);
    if (!loop) return;
    stopped = true;
    if (ctx.hasUI) ctx.ui.notify('Модель зациклилась: одинаковый фрагмент повторён ' + loop.repeats + ' раз. Ответ прерван. Уточни запрос или начни новую сессию. /loopguard off отключает эту защиту.', 'warning');
    ctx.abort();
  });
  pi.registerCommand('loopguard', {
    description: 'Защита от зацикливания: /loopguard on или /loopguard off',
    handler: async (args, ctx) => {
      const value = args.trim();
      if (value === 'off') enabled = false;
      else if (value === 'on') enabled = true;
      if (ctx.hasUI) ctx.ui.notify('Защита от повторов: ' + (enabled ? 'включена' : 'выключена'), 'info');
    },
  });
}
