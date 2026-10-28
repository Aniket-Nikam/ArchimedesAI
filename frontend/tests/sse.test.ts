import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readEvents } from '../src/sse.ts';

const encode = (text: string) => new TextEncoder().encode(text);
function stream(chunks: Uint8Array[]) {
  return new ReadableStream<Uint8Array>({ start(controller) { chunks.forEach(chunk => controller.enqueue(chunk)); controller.close(); } });
}
async function collect(chunks: Uint8Array[]) {
  const result = [];
  for await (const item of readEvents(stream(chunks))) result.push(item);
  return result;
}

test('preserves a JSON frame and unicode split at every byte boundary', async () => {
  const expected = { type: 'complete', data: { title: 'Évidence 🧬', session_id: 42 } };
  const bytes = encode(`data: ${JSON.stringify(expected)}\r\n\r\n`);
  for (let split = 1; split < bytes.length; split++) {
    assert.deepEqual(await collect([bytes.slice(0, split), bytes.slice(split)]), [expected]);
  }
  assert.deepEqual(await collect(Array.from(bytes, byte => new Uint8Array([byte]))), [expected]);
});
test('supports coalesced events, comments, CRLF and multiline data', async () => {
  const text = ': ping\r\n\r\ndata: {"type":"log",\r\ndata: "data":"Searching"}\r\n\r\ndata: {"type":"complete","data":{}}\n\n';
  assert.equal((await collect([encode(text)])).length, 2);
});
test('rejects truncated and malformed frames rather than claiming completion', async () => {
  await assert.rejects(collect([encode('data: {"type":"complete"')]), /ended before/);
  await assert.rejects(collect([encode('data: {oops}\n\n')]));
});
test('cancels the reader when a consumer stops', async () => {
  let cancelled = false;
  const body = new ReadableStream<Uint8Array>({
    start(controller) { controller.enqueue(encode('data: {"type":"log","data":"Searching"}\n\n')); },
    cancel() { cancelled = true; },
  });
  for await (const _event of readEvents(body)) break;
  assert.equal(cancelled, true);
});
