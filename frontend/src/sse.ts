export type ResearchEvent = { type: string; data: any };

/** SSE frames may span chunks, UTF-8 code points and multiple data lines. */
export async function* readEvents(body: ReadableStream<Uint8Array>): AsyncGenerator<ResearchEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  function parse(frame: string): ResearchEvent | undefined {
    const data = frame.split(/\r?\n/).filter(line => line.startsWith('data:'))
      .map(line => line.slice(5).replace(/^ /, '')).join('\n');
    if (!data) return;
    const value = JSON.parse(data);
    if (typeof value.type !== 'string') throw new Error('Invalid research event.');
    return value;
  }
  try {
    while (true) {
      const { done, value } = await reader.read();
      buffer += done ? decoder.decode() : decoder.decode(value, { stream: true });
      if (buffer.length > 2_000_000) throw new Error('Research response exceeds the supported size.');
      let match: RegExpExecArray | null;
      while ((match = /\r?\n\r?\n/.exec(buffer))) {
        const frame = buffer.slice(0, match.index);
        buffer = buffer.slice(match.index + match[0].length);
        const event = parse(frame);
        if (event) yield event;
      }
      if (done) {
        if (buffer.trim()) throw new Error('Research connection ended before the final event was complete.');
        break;
      }
    }
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}
