import { readFileSync, realpathSync } from 'node:fs';
import { createRequire } from 'node:module';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

// Guard against reintroducing the dependency versions identified by the
// 2026-11-14 audit. A fresh advisory scan is still required before release.
const root = process.cwd();
const jsdomRequire = createRequire(realpathSync(resolve(root, 'node_modules/jsdom/package.json')));
const versionAt = (path) =>
  JSON.parse(readFileSync(path, 'utf8')).version.split('.').map(Number);
const atLeast = (version, minimum) => {
  for (let i = 0; i < minimum.length; i++) {
    if (version[i] !== minimum[i]) return version[i] > minimum[i];
  }
  return true;
};

describe('audited dependency security floors', () => {
  it('uses the patched Vite 8 release line', () => {
    const version = versionAt(resolve(root, 'node_modules/vite/package.json'));
    expect(version[0]).toBe(8);
    expect(atLeast(version, [8, 3, 8])).toBe(true);
  });

  it('resolves jsdom HTTP requests through patched undici 8', () => {
    const version = versionAt(jsdomRequire.resolve('undici/package.json'));
    expect(version[0]).toBe(8);
    expect(atLeast(version, [8, 12, 2])).toBe(true);
  });

  it('resolves CSS source maps through the patched source-map-js line', () => {
    const cssRequire = createRequire(jsdomRequire.resolve('css-tree'));
    const version = versionAt(cssRequire.resolve('source-map-js/package.json'));
    expect(version[0]).toBe(1);
    expect(atLeast(version, [1, 2, 2])).toBe(true);
  });
});
