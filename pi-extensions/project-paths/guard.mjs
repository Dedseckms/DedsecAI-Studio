import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

export const missingError = text => /\bENOENT\b|\bPATH_NOT_FOUND\b|no such file or directory|нет такого файла или каталога|не удается найти указанный путь|cannot access.*not found/i.test(text);
export const resultText = content => (content || []).filter(c => c.type === 'text').map(c => c.text).join('\n');
export function failedPath(result) {
  const text = resultText(result.content);
  return missingError(text) && (result.isError || /Command exited with code [1-9]/.test(text));
}
export function expandPath(value, cwd) {
  if (typeof value !== 'string' || !value || value.includes('\0')) return null;
  value = value.replace(/^@(?=\/)/, '').replace(/^~(?=\/|$)/, os.homedir()).replace(/^\$HOME(?=\/|$)|^\$\{HOME\}(?=\/|$)/, os.homedir());
  if (/[$*?{}\[\]`]/.test(value)) return null;
  return path.resolve(cwd, value);
}
export function missingPath(value, cwd) {
  const resolved = expandPath(value, cwd);
  if (!resolved) return null;
  try { fs.statSync(resolved); return null; }
  catch (error) { return ['ENOENT', 'ENOTDIR'].includes(error.code) ? resolved : null; }
}
export function inventory(directory, limit = 24) {
  try {
    const entries = fs.readdirSync(directory, {withFileTypes: true})
      .filter(e => !e.name.startsWith('.') || e.name === '.git')
      .sort((a,b) => Number(b.isDirectory()) - Number(a.isDirectory()) || a.name.localeCompare(b.name, 'ru'));
    return entries.slice(0, limit).map(e => JSON.stringify(e.name + (e.isDirectory() ? '/' : ''))).join(', ') + (entries.length > limit ? ', …' : '');
  } catch { return '(список недоступен)'; }
}
export function hint(cwd, missing) {
  let base = missing;
  for (let i = 0; i < 64; i++) {
    try { if (fs.statSync(base).isDirectory()) break; } catch {}
    const parent = path.dirname(base); if (parent === base) break; base = parent;
  }
  return `PATH_NOT_FOUND: ${JSON.stringify(missing)}. Рабочая папка: ${JSON.stringify(cwd)}. Используй относительные пути и точные имена; не перебирай варианты написания. Ближайшая существующая папка ${JSON.stringify(base)}: ${inventory(base, 12)}. В проекте: ${inventory(cwd, 16)}.`;
}
// Only parse simple commands. Compound shell syntax is never rewritten or evaluated.
export function simpleTokens(command) {
  if (typeof command !== 'string' || /[;|&<>\n`]/.test(command) || command.includes('$(')) return null;
  const parts = []; let token = '', quote = '', started = false;
  for (let i=0;i<command.length;i++) {
    const ch = command[i];
    if (ch === '\\' && quote !== "'") { if (++i >= command.length) return null; token += command[i]; started = true; }
    else if (quote) { if (ch === quote) quote = ''; else token += ch; started = true; }
    else if (ch === '"' || ch === "'") { quote = ch; started = true; }
    else if (/\s/.test(ch)) { if (started) {parts.push(token);token='';started=false;} }
    else {token+=ch;started=true;}
  }
  if (quote) return null;
  if (started) parts.push(token);
  return parts;
}
export function checkedPaths(event) {
  if (['read', 'edit', 'ls', 'find', 'grep'].includes(event.toolName)) return typeof event.input.path === 'string' ? [event.input.path] : [];
  if (event.toolName !== 'bash') return [];
  const tokens = simpleTokens(event.input.command);
  if (!tokens?.length || !['ls','cd','cat','stat','file','rmdir','unlink','rm'].includes(path.basename(tokens[0]))) return [];
  // -I/-T/--format etc may take values that are not paths: leave those commands to the actual tool.
  if (tokens.slice(1).some(t => /^--[^=]+$/.test(t) && !['--','--all','--long','--directory','--recursive'].includes(t))) return [];
  if (tokens.slice(1).some(t => /^-[A-Z]/.test(t))) return [];
  return tokens.slice(1).filter(t => !t.startsWith('-'));
}
export function trimFailedHistory(messages) {
  const failures = messages.filter(m => m.role === 'toolResult' && failedPath(m));
  if (failures.length <= 3) return null;
  const removed = new Set(failures.slice(1, -2).map(m => m.toolCallId));
  const first = failures[0].toolCallId;
  const output = [];
  for (const message of messages) {
    if (message.role === 'toolResult' && removed.has(message.toolCallId)) continue;
    if (message.role === 'assistant') {
      const content = message.content.filter(c => c.type !== 'toolCall' || !removed.has(c.id));
      if (!content.length) continue;
      output.push({...message, content});
    } else if (message.role === 'toolResult' && message.toolCallId === first) {
      output.push({...message, structuredContent:undefined, content:[{type:'text',text:`PATH_NOT_FOUND: ${removed.size} однотипных ошибочных обращений к несуществующим путям опущено в контексте. Полная история сохранена на диске. Не перебирай варианты имён: проверь pwd и реальные имена через ls -la .`}]});
    } else output.push(message);
  }
  return {messages:output};
}
