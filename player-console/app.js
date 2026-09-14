const BAUD_RATE = 115200;
const MAX_COMMAND_BYTES = 191;
const MAX_OUTPUT_CHARS = 250000;
const encoder = new TextEncoder();

const $ = (id) => document.getElementById(id);
const connectButton = $('connect');
const commandInput = $('command');
const sendButton = $('send');
const output = $('output');

let port = null;
let reader = null;
let writer = null;
let readTask = null;
let closing = false;
let rxBytes = 0;
let txBytes = 0;
let pendingOutput = '';
let outputFrame = null;

function appendOutput(text) {
  pendingOutput = (pendingOutput + text).slice(-MAX_OUTPUT_CHARS);
  if (outputFrame !== null) return;
  outputFrame = requestAnimationFrame(() => {
    output.textContent = (output.textContent + pendingOutput).slice(-MAX_OUTPUT_CHARS);
    pendingOutput = '';
    outputFrame = null;
    output.scrollTop = output.scrollHeight;
    updateTraffic();
  });
}

function appendSystem(text) {
  appendOutput(`\n[${text}]\n`);
}

function updateTraffic() {
  $('traffic').textContent = `RX ${rxBytes} B // TX ${txBytes} B`;
}

function showDisconnected(message = '') {
  $('device-name').textContent = 'NO DEVICE';
  $('device-info').textContent = message;
  $('connection-status').textContent = 'OFFLINE';
  $('connection-status').className = 'offline';
  connectButton.textContent = 'CONNECT USB';
  commandInput.disabled = true;
  commandInput.placeholder = 'CONNECT USB FIRST';
  sendButton.disabled = true;
}

function showConnected(activePort) {
  const info = activePort.getInfo();
  const hex = (value) => value === undefined ? 'UNKNOWN' : `0x${value.toString(16).toUpperCase().padStart(4, '0')}`;
  $('device-name').textContent = 'USB SERIAL';
  $('device-info').textContent = `VID ${hex(info.usbVendorId)} // PID ${hex(info.usbProductId)}`;
  $('connection-status').textContent = 'ONLINE';
  $('connection-status').className = 'online';
  connectButton.textContent = 'DISCONNECT';
  commandInput.disabled = false;
  commandInput.placeholder = 'COMMAND OR FLAG';
  sendButton.disabled = false;
  commandInput.focus();
}

async function readSerial(activePort) {
  try {
    while (!closing && port === activePort && activePort.readable) {
      const decoder = new TextDecoder();
      const activeReader = activePort.readable.getReader();
      reader = activeReader;
      try {
        while (!closing && port === activePort) {
          const { value, done } = await activeReader.read();
          // A cancelled/closed stream may remain readable until port.close().
          // Exit both loops so it cannot spin on immediately resolved reads.
          if (done) {
            appendOutput(decoder.decode());
            return;
          }
          if (closing || port !== activePort) return;
          rxBytes += value.byteLength;
          appendOutput(decoder.decode(value, { stream: true }));
        }
      } catch (error) {
        if (!closing) {
          appendSystem(`READ ERROR: ${error.message}`);
          // Give UI events time to run even if replacement streams keep failing.
          await new Promise((resolve) => setTimeout(resolve, 100));
        }
      } finally {
        activeReader.releaseLock();
        if (reader === activeReader) reader = null;
      }
    }
  } catch (error) {
    if (!closing) appendSystem(`READ ERROR: ${error.message}`);
  } finally {
    if (!closing && port === activePort) {
      // disconnect() waits for this task, so do not await it from this task.
      void disconnect('Serial 연결이 종료되었습니다.');
    }
  }
}

async function connect() {
  connectButton.disabled = true;
  try {
    const selectedPort = await navigator.serial.requestPort();
    await selectedPort.open({ baudRate: BAUD_RATE, dataBits: 8, stopBits: 1, parity: 'none', flowControl: 'none' });
    port = selectedPort;
    rxBytes = 0;
    txBytes = 0;
    updateTraffic();
    showConnected(selectedPort);
    appendSystem('USB CONNECTED // 115200 BAUD');
    readTask = readSerial(selectedPort);
  } catch (error) {
    if (error.name !== 'NotFoundError') {
      appendSystem(`CONNECT ERROR: ${error.message}`);
    }
  } finally {
    connectButton.disabled = closing;
  }
}

async function disconnect(message = '사용자가 연결을 종료했습니다.') {
  if (!port || closing) return;
  closing = true;
  connectButton.disabled = true;
  connectButton.textContent = 'DISCONNECTING…';
  commandInput.disabled = true;
  sendButton.disabled = true;
  const activePort = port;
  const activeTask = readTask;
  const activeWriter = writer;
  port = null;
  try {
    const results = await Promise.allSettled([reader?.cancel(), activeWriter?.abort()]);
    for (const result of results) {
      if (result.status === 'rejected') appendSystem(`DISCONNECT WARNING: ${result.reason}`);
    }
    if (activeTask) await activeTask;
    activeWriter?.releaseLock();
    await activePort.close();
  } catch (error) {
    appendSystem(`DISCONNECT WARNING: ${error.message}`);
  } finally {
    reader = null;
    writer = null;
    readTask = null;
    closing = false;
    connectButton.disabled = false;
    showDisconnected(message);
    appendSystem('USB DISCONNECTED');
  }
}

connectButton.addEventListener('click', () => port ? disconnect() : connect());

$('clear').addEventListener('click', () => {
  pendingOutput = '';
  output.textContent = '';
  commandInput.focus();
});

$('shell').addEventListener('submit', async (event) => {
  event.preventDefault();
  const command = commandInput.value.trim();
  if (!port || closing || !command || writer) return;
  const payload = encoder.encode(`${command}\n`);
  if (encoder.encode(command).byteLength > MAX_COMMAND_BYTES) {
    appendSystem(`INPUT ERROR: 최대 ${MAX_COMMAND_BYTES} UTF-8 bytes`);
    return;
  }

  const activePort = port;
  sendButton.disabled = true;
  appendOutput(`> ${command}\n`);
  commandInput.value = '';
  try {
    const activeWriter = activePort.writable.getWriter();
    writer = activeWriter;
    try { await activeWriter.write(payload); } finally {
      activeWriter.releaseLock();
      if (writer === activeWriter) writer = null;
    }
    if (port === activePort) {
      txBytes += payload.byteLength;
      updateTraffic();
    }
  } catch (error) {
    if (port === activePort && !closing) {
      appendSystem(`WRITE ERROR: ${error.message}`);
      await disconnect('쓰기 오류로 연결이 종료되었습니다.');
    }
  } finally {
    if (port === activePort && !closing) {
      sendButton.disabled = false;
      commandInput.focus();
    }
  }
});

if ('serial' in navigator && window.isSecureContext) {
  $('browser-status').textContent = 'WEB SERIAL: READY';
  connectButton.disabled = false;
  navigator.serial.addEventListener('disconnect', (event) => {
    if (event.target === port) void disconnect('USB 장치가 분리되었습니다.');
  });
} else {
  $('browser-status').textContent = 'WEB SERIAL: UNAVAILABLE';
  connectButton.disabled = true;
  showDisconnected('현재 브라우저 환경에서는 연결할 수 없습니다.');
}

window.addEventListener('pagehide', () => { void disconnect(); });
