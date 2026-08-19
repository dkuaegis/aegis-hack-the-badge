const BAUD_RATE = 115200;
const MAX_COMMAND_BYTES = 191;
const MAX_OUTPUT_CHARS = 250000;
const encoder = new TextEncoder();
const decoder = new TextDecoder();

const $ = (id) => document.getElementById(id);
const connectButton = $('connect');
const commandInput = $('command');
const sendButton = $('send');
const output = $('output');

let port = null;
let reader = null;
let readTask = null;
let closing = false;
let sending = false;
let rxBytes = 0;
let txBytes = 0;

function appendOutput(text) {
  output.textContent = (output.textContent + text).slice(-MAX_OUTPUT_CHARS);
  output.scrollTop = output.scrollHeight;
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
  commandInput.placeholder = '1-4 | hint | status | help | exit';
  sendButton.disabled = false;
  commandInput.focus();
}

async function readSerial(activePort) {
  try {
    while (activePort.readable) {
      const activeReader = activePort.readable.getReader();
      reader = activeReader;
      try {
        while (true) {
          const { value, done } = await activeReader.read();
          if (done) break;
          rxBytes += value.byteLength;
          appendOutput(decoder.decode(value, { stream: true }));
          updateTraffic();
        }
      } catch (error) {
        if (!closing) appendSystem(`READ ERROR: ${error.message}`);
      } finally {
        activeReader.releaseLock();
        if (reader === activeReader) reader = null;
      }
    }
  } finally {
    if (!closing && port === activePort) {
      port = null;
      readTask = null;
      try { await activePort.close(); } catch {}
      showDisconnected('Serial 연결이 종료되었습니다.');
      appendSystem('USB DISCONNECTED');
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
    connectButton.disabled = false;
  }
}

async function disconnect(message = '사용자가 연결을 종료했습니다.') {
  if (!port || closing) return;
  closing = true;
  connectButton.disabled = true;
  const activePort = port;
  const activeTask = readTask;
  port = null;
  try {
    if (reader) await reader.cancel();
    if (activeTask) await activeTask;
    await activePort.close();
  } catch (error) {
    appendSystem(`DISCONNECT WARNING: ${error.message}`);
  } finally {
    reader = null;
    readTask = null;
    closing = false;
    connectButton.disabled = false;
    showDisconnected(message);
    appendSystem('USB DISCONNECTED');
  }
}

connectButton.addEventListener('click', () => port ? disconnect() : connect());

$('clear').addEventListener('click', () => {
  output.textContent = '';
  commandInput.focus();
});

$('shell').addEventListener('submit', async (event) => {
  event.preventDefault();
  const command = commandInput.value.trim();
  if (!port || !command || sending) return;
  const payload = encoder.encode(`${command}\n`);
  if (encoder.encode(command).byteLength > MAX_COMMAND_BYTES) {
    appendSystem(`INPUT ERROR: 최대 ${MAX_COMMAND_BYTES} UTF-8 bytes`);
    return;
  }

  sending = true;
  sendButton.disabled = true;
  appendOutput(`> ${command}\n`);
  commandInput.value = '';
  try {
    const writer = port.writable.getWriter();
    try { await writer.write(payload); } finally { writer.releaseLock(); }
    txBytes += payload.byteLength;
    updateTraffic();
  } catch (error) {
    appendSystem(`WRITE ERROR: ${error.message}`);
    await disconnect('쓰기 오류로 연결이 종료되었습니다.');
  } finally {
    sending = false;
    sendButton.disabled = !port;
    commandInput.focus();
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
