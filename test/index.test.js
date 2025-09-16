const test = require('node:test');
const assert = require('node:assert');
const { promisify } = require('node:util');
const { execFile } = require('node:child_process');

const execFileAsync = promisify(execFile);

async function runCli(args) {
  const { stdout } = await execFileAsync(process.execPath, ['index.js', ...args]);
  return stdout.trim();
}

test('greets with the provided name', async () => {
  const output = await runCli(['Alice']);
  assert.strictEqual(output, 'Hello, Alice!');
});

test('uppercases the greeting when --shout is provided', async () => {
  const output = await runCli(['Alice', '--shout']);
  assert.strictEqual(output, 'HELLO, ALICE!');
});

test('treats --shout as a name after --', async () => {
  const output = await runCli(['--', '--shout']);
  assert.strictEqual(output, 'Hello, --shout!');
});
