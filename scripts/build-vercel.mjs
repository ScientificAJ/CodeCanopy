import { chmod, copyFile, mkdir, readFile, stat, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const runtime = join(root, '.runtime');
if (process.platform !== 'linux') {
  throw new Error('Build GREPO deployment on Linux so the bundled renderer runtime matches Vercel.');
}

await mkdir(runtime, { recursive: true });
const node = join(runtime, 'node');
await copyFile(process.execPath, node);
await chmod(node, 0o755);
execFileSync(node, ['--version'], { stdio: 'inherit' });

// Preserve the license from the build image's Node distribution. Some images
// place it outside bin/; use the exact upstream release as a fallback.
let license;
for (const candidate of [join(dirname(process.execPath), '..', 'LICENSE'),
  join(dirname(process.execPath), '..', 'share', 'doc', 'node', 'LICENSE')]) {
  try { license = await readFile(candidate); break; } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }
}
if (!license) {
  const response = await fetch(`https://raw.githubusercontent.com/nodejs/node/${process.version}/LICENSE`, {
    signal: AbortSignal.timeout(20_000),
  });
  if (!response.ok) throw new Error(`Could not package Node license (${response.status}).`);
  license = Buffer.from(await response.arrayBuffer());
}
await writeFile(join(runtime, 'NODE-LICENSE'), license);
await writeFile(join(runtime, 'node-version.txt'), `${process.version}\n`);
console.log(`Packaged renderer runtime: ${Math.round((await stat(node)).size / 1024 / 1024)} MiB`);

execFileSync('npm', ['run', 'build', '--prefix', 'frontend'], {
  cwd: root,
  stdio: 'inherit',
  env: { ...process.env, VITE_API_BASE_URL: '' },
});
