// Actual React markup + project CSS in Chrome; network blocked, synthetic data.
import { readFile, mkdtemp, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { spawn } from 'node:child_process';

const profile = await mkdtemp(join(tmpdir(), 'whatnot-property-layout-'));
const chrome = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', [
  '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
  '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank',
], { windowsHide: true, stdio: 'ignore' });
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
let socket, command;
try {
  let port;
  for (let i=0; i<100; i++) {
    try { port=Number((await readFile(join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]); break; }
    catch { if(chrome.exitCode!==null) throw new Error('Layout Chrome startup failed'); await pause(100); }
  }
  if (!port) throw new Error('Layout Chrome startup timed out');
  const pages=await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  socket=new WebSocket(pages.find(p=>p.type==='page').webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
  let sequence=0; const pending=new Map();
  socket.onmessage=event=>{const value=JSON.parse(event.data),p=pending.get(value.id);if(p){clearTimeout(p.timer);pending.delete(value.id);value.error?p.reject(new Error(value.error.message)):p.resolve(value.result);}};
  socket.onclose=()=>{for(const p of pending.values()){clearTimeout(p.timer);p.reject(new Error('Layout Chrome connection closed'));}pending.clear();};
  command=(method,params={})=>new Promise((resolve,reject)=>{
    if(socket.readyState!==WebSocket.OPEN){reject(new Error('Layout Chrome is unavailable'));return;}
    const id=++sequence;
    const timer=setTimeout(()=>{pending.delete(id);reject(new Error('Layout Chrome command timed out'));},20000);
    pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params}));
  });
  await command('Page.enable');await command('Network.enable');
  await command('Network.setBlockedURLs',{urls:['*']});
  const css=(await readFile('src/styles/index.css','utf8'))+'\n'+await readFile('src/styles/properties.css','utf8');
  const markup=await readFile('docs/security/evidence/property-layout-fixture.html','utf8');
  const html=`<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>${css}</style></head><body>${markup}</body></html>`;
  const results=[];
  for (const width of [1440,1024,768,390,320]) {
    await command('Emulation.setDeviceMetricsOverride',{width,height:1200,deviceScaleFactor:1,mobile:width<600});
    const tree=await command('Page.getFrameTree');
    await command('Page.setDocumentContent',{frameId:tree.frameTree.frame.id,html});
    const measurement=await command('Runtime.evaluate',{expression:`(()=>{
      const forms=[...document.querySelectorAll('form')],controls=[...document.querySelectorAll('.property-workspace input:not([type=checkbox]),.property-workspace select,.property-workspace textarea')];
      const grids=forms.map(f=>getComputedStyle(f.querySelector('.form-grid')).gridTemplateColumns.split(' ').length);
      return {width:innerWidth,forms:forms.length,columnsCorrect:grids.every(n=>n===(innerWidth<=760?1:2)),
        controlsContained:controls.every(e=>{const r=e.getBoundingClientRect(),p=e.closest('.panel').getBoundingClientRect();return r.left>=p.left&&r.right<=p.right&&r.width>100}),
        controlsStyled:controls.every(e=>{const s=getComputedStyle(e);return parseFloat(s.borderRadius)>=8&&parseFloat(s.paddingTop)>=12}),
        labelsAbove:controls.every(e=>e.getBoundingClientRect().top>=e.closest('label').getBoundingClientRect().top+14),
        documentFits:document.documentElement.scrollWidth<=innerWidth,
        checkboxCompact:document.querySelector('input[type=checkbox]').getBoundingClientRect().width<30};
    })()`,returnByValue:true});
    const result=measurement.result.value;
    result.passed=result.forms===2&&['columnsCorrect','controlsContained','controlsStyled','labelsAbove','documentFits','checkboxCompact'].every(key=>result[key]);
    results.push(result);
    if([1440,390].includes(width)){
      const shot=await command('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
      await writeFile(`docs/security/evidence/property-layout-${width}.png`,Buffer.from(shot.data,'base64'));
    }
  }
  await writeFile('docs/security/evidence/property-layout.json',JSON.stringify({kind:'Offline Chrome geometry; actual React forms, synthetic data; no GPS, live API or Google Maps',results},null,2));
  console.log(JSON.stringify(results));
  if(results.some(r=>!r.passed))process.exitCode=1;
} finally {
  if(command)await Promise.race([command('Browser.close').catch(()=>{}),pause(1500)]);
  socket?.close();
  if(chrome.exitCode===null)chrome.kill();
}
