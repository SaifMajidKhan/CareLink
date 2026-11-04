// Root npm commands validate Neon tooling and the existing Python backend.
// The Flutter app and the team's web portal keep their own build commands.
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { spawnSync } from 'node:child_process';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const backend = join(root, 'backend');
const venvPython = process.platform === 'win32'
  ? join(backend, '.venv', 'Scripts', 'python.exe')
  : join(backend, '.venv', 'bin', 'python');
const python = existsSync(venvPython)
  ? venvPython
  : (process.platform === 'win32' ? 'python' : 'python3');

await import(pathToFileURL(join(root, 'neon.ts')).href);
console.log('Neon configuration loaded successfully.');

const testing = process.argv.includes('--test');
const result = spawnSync(python, testing
  ? ['-m', 'pytest', 'tests', '-q']
  : ['-m', 'compileall', '-q', 'app'], { cwd: backend, stdio: 'inherit' });
if (result.error) {
  console.error('Could not start Python. Install backend requirements in backend/.venv first.');
}
if (result.status !== 0) process.exit(result.status ?? 1);
console.log(testing ? 'Backend tests passed.' : 'Python backend compilation passed.');
