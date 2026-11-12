// Preserve direct runtime notices from installed packages; no network or package changes.
import {createRequire} from 'node:module';
import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {dirname,join} from 'node:path';
const require=createRequire(import.meta.url);
const routerRequire=createRequire(require.resolve('react-router-dom/package.json'));
const parts=['Direct runtime dependency notices. Copied from installed package licences on 12 November 2026.'];
for(const name of ['react','react-dom','react-router','react-router-dom','lucide-react']){
  const resolver=name==='react-router'?routerRequire:require;
  const root=dirname(resolver.resolve(`${name}/package.json`));
  const file=['LICENSE','LICENSE.md'].map(n=>join(root,n)).find(existsSync);
  if(!file)throw new Error(`Missing licence: ${name}`);
  parts.push(name,readFileSync(file,'utf8'));
}
writeFileSync(new URL('../docs/THIRD_PARTY_NOTICES.txt',import.meta.url),parts.join('\n\n'));
console.log('Preserved direct runtime licence notices.');
