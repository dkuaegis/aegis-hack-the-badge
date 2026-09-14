import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('./app.js', import.meta.url), 'utf8');
const tick = () => new Promise((resolve) => setImmediate(resolve));

function serialPort(writeMode = 'normal') {
  return {
    closeCount: 0,
    abortCount: 0,
    writes: [],
    getInfo: () => ({ usbVendorId: 0x303a }),
    async open() {
      this.replaceReadable();
      this.writable = new WritableStream({
        write: (bytes, controller) => {
          this.writes.push(bytes);
          if (writeMode === 'error') throw new Error('write failed');
          if (writeMode === 'pending') {
            // Web Serial interrupts the OS write when the stream is aborted.
            return new Promise((resolve, reject) => {
              controller.signal.addEventListener('abort', () => {
                this.abortCount++;
                reject(controller.signal.reason);
              }, { once: true });
            });
          }
        },
      });
    },
    replaceReadable() {
      this.readable = new ReadableStream({
        start: (controller) => { this.input = controller; },
        // Keep the closed stream on the port until close(), including while
        // cancellation is pending. Re-reading it must not starve this task.
        cancel: tick,
      });
    },
    async close() {
      assert.ok(!this.readable?.locked, 'reader must release its lock');
      assert.ok(!this.writable?.locked, 'writer must release its lock');
      this.closeCount++;
      this.readable = this.writable = null;
    },
  };
}

function consoleApp(selectedPort = serialPort()) {
  const elements = new Map();
  const frames = new Map();
  const serialEvents = {};
  const windowEvents = {};
  let frameId = 0;
  const element = (id) => {
    if (!elements.has(id)) {
      elements.set(id, {
        textContent: '', value: '', disabled: false, handlers: {},
        focus() {},
        addEventListener(type, handler) { this.handlers[type] = handler; },
      });
    }
    return elements.get(id);
  };
  const context = vm.createContext({
    TextEncoder, TextDecoder, setTimeout,
    document: { getElementById: element },
    window: {
      isSecureContext: true,
      addEventListener(type, handler) { windowEvents[type] = handler; },
    },
    navigator: { serial: {
      requestPort: async () => selectedPort,
      addEventListener(type, handler) { serialEvents[type] = handler; },
    } },
    requestAnimationFrame(callback) { frames.set(++frameId, callback); return frameId; },
  });
  vm.runInContext(source, context);
  return {
    context, element, frames, serialEvents, windowEvents, port: selectedPort,
    click: () => element('connect').handlers.click(),
    send(command) {
      element('command').value = command;
      return element('shell').handlers.submit({ preventDefault() {} });
    },
    render() {
      const callbacks = [...frames.values()];
      frames.clear();
      callbacks.forEach((callback) => callback());
    },
  };
}

test('disconnect cancels a pending read and allows repeated reconnects', async () => {
  const app = consoleApp();
  for (let i = 0; i < 20; i++) {
    await app.click();
    assert.equal(app.element('connection-status').textContent, 'ONLINE');
    const closing = app.click();
    assert.equal(app.element('command').disabled, true);
    assert.equal(app.element('send').disabled, true);
    await closing;
    assert.equal(app.port.closeCount, i + 1);
    assert.equal(app.element('connection-status').textContent, 'OFFLINE');
    assert.equal(app.element('connect').disabled, false);
  }
  app.render();
  assert.doesNotMatch(app.element('output').textContent, /WARNING|ERROR/);
});

test('EOF exits both read loops and closes the port', async () => {
  const app = consoleApp();
  await app.click();
  app.port.input.close();
  await tick();
  assert.equal(app.port.closeCount, 1);
  assert.equal(app.element('connection-status').textContent, 'OFFLINE');
});

test('disconnect aborts an in-flight write before closing the port', async () => {
  const app = consoleApp(serialPort('pending'));
  await app.click();
  const sending = app.send('aegis');
  await tick();
  await app.click();
  await sending;
  assert.equal(app.port.abortCount, 1);
  assert.equal(app.port.closeCount, 1);
  assert.equal(app.element('send').disabled, true);
  app.render();
  assert.doesNotMatch(app.element('output').textContent, /WARNING|ERROR/);
});

test('write failure uses the same cleanup and permits reconnecting', async () => {
  const app = consoleApp(serialPort('error'));
  await app.click();
  await app.send('aegis');
  assert.equal(app.port.closeCount, 1);
  app.render();
  assert.match(app.element('output').textContent, /WRITE ERROR: write failed/);
  await app.click();
  assert.equal(app.element('send').disabled, false);
  await app.click();
});

test('USB removal and page exit clean up the active connection', async () => {
  const app = consoleApp();
  await app.click();
  app.serialEvents.disconnect({ target: {} });
  assert.equal(app.port.closeCount, 0);
  app.serialEvents.disconnect({ target: app.port });
  await tick();
  assert.equal(app.port.closeCount, 1);
  await app.click();
  app.windowEvents.pagehide();
  await tick();
  assert.equal(app.port.closeCount, 2);
});

test('recoverable read errors yield to UI events and resume on the new stream', async () => {
  const app = consoleApp();
  await app.click();
  app.port.input.error(new Error('framing error'));
  app.port.replaceReadable();
  app.port.input.enqueue(new TextEncoder().encode('recovered'));
  await new Promise((resolve) => setTimeout(resolve, 150));
  app.render();
  assert.match(app.element('output').textContent, /framing error.*recovered/s);
  assert.equal(app.port.closeCount, 0);
  // An errored stream that stays on the port must still allow a disconnect.
  app.port.input.error(new Error('persistent read error'));
  await tick();
  await app.click();
  assert.equal(app.port.closeCount, 1);
});

test('fatal read errors close the port without a second disconnect', async () => {
  const app = consoleApp();
  await app.click();
  app.port.input.error(new Error('device lost'));
  app.port.readable = null;
  await new Promise((resolve) => setTimeout(resolve, 150));
  assert.equal(app.port.closeCount, 1);
  assert.equal(app.element('connect').disabled, false);
});

test('split UTF-8 survives chunk boundaries but cannot leak into a new connection', async () => {
  const app = consoleApp();
  const bytes = new TextEncoder().encode('배지');
  await app.click();
  app.port.input.enqueue(bytes.slice(0, 1));
  app.port.input.enqueue(bytes.slice(1));
  await tick();
  app.render();
  assert.match(app.element('output').textContent, /배지/);
  app.port.input.enqueue(bytes.slice(0, 1));
  await tick();
  await app.click();
  await app.click();
  app.element('clear').handlers.click();
  app.port.input.enqueue(new TextEncoder().encode('fresh'));
  await tick();
  app.render();
  assert.equal(app.element('output').textContent, 'fresh');
  await app.click();
});

test('large bursts share one render and cap both pending and displayed output', async () => {
  const app = consoleApp();
  await app.click();
  for (let i = 0; i < 1000; i++) app.port.input.enqueue(new Uint8Array(1024).fill(120));
  await tick();
  assert.equal(app.frames.size, 1);
  assert.equal(app.element('output').textContent, '');
  assert.equal(vm.runInContext('pendingOutput.length', app.context), 250000);
  app.render();
  assert.equal(app.element('output').textContent.length, 250000);
  assert.equal(app.element('traffic').textContent, 'RX 1024000 B // TX 0 B');
  app.port.input.enqueue(new TextEncoder().encode('cleared before rendering'));
  await tick();
  app.element('clear').handlers.click();
  app.render();
  assert.equal(app.element('output').textContent, '');
  await app.click();
});

test('commands retain their UTF-8 byte limit and traffic accounting', async () => {
  const app = consoleApp();
  await app.click();
  await app.send('배'.repeat(64));
  assert.equal(app.port.writes.length, 0);
  await app.send('aegis');
  assert.equal(new TextDecoder().decode(app.port.writes[0]), 'aegis\n');
  assert.equal(app.element('traffic').textContent, 'RX 0 B // TX 6 B');
  await app.click();
});
