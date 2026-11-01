// Deliberately conservative: consecutive long lines or repeated multi-line blocks.
export class LoopDetector {
  constructor() { this.buffer = ''; this.sinceCheck = 0; }
  push(delta) {
    this.buffer = (this.buffer + delta).slice(-20000);
    this.sinceCheck += delta.length;
    if (this.sinceCheck < 64 && !delta.includes('\n') && !delta.includes('\\n')) return null;
    this.sinceCheck = 0;
    // Tool-call streams contain JSON-escaped newlines until the call completes.
    const text = this.buffer.replace(/\\r\\n|\\n/g, '\n');
    const lines = text.split(/\r?\n/).slice(0, -1).map(line => line.trim());
    const tail = lines.slice(-100);
    for (let size = 1; size <= 4; size++) {
      const need = size === 1 ? 12 : 8;
      // Check near the end, including the first few lines after a repeated block.
      for (let offset = 0; offset <= Math.min(4, tail.length - size * need); offset++) {
        const end = tail.length - offset;
        const block = tail.slice(end - size, end);
        const signature = block.join('\n');
        if (signature.replace(/[\s{}\[\](),;"'`]/g, '').length < 12) continue;
        if (signature.length * need < 240) continue;
        let count = 1;
        while (end - size * (count + 1) >= 0 && tail.slice(end - size * (count + 1), end - size * count).join('\n') === signature) count++;
        if (count >= need) return { repeats: count, blockLines: size };
      }
    }
    return null;
  }
}
