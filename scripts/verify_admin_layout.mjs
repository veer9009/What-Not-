// Offline Chrome checks of actual React output. Fixtures never create live records.
import { readFile, mkdtemp, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { spawn } from 'node:child_process';

const profile=await mkdtemp(join(tmpdir(),'whatnot-admin-layout-'));
const chrome=spawn('C:/Program Files/Google/Chrome/Application/chrome.exe',[
  '--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check',
  '--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank',
],{windowsHide:true,stdio:'ignore'});
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
let socket,command;
try {
  let port;
  for(let i=0;i<100;i++){
    try{port=Number((await readFile(join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]);break;}
    catch{if(chrome.exitCode!==null)throw new Error('Offline Chrome startup failed');await pause(100);}
  }
  if(!port)throw new Error('Offline Chrome startup timed out');
  const pages=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  socket=new WebSocket(pages.find(p=>p.type==='page').webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
  let sequence=0;const pending=new Map();
  socket.onmessage=event=>{const value=JSON.parse(event.data),p=pending.get(value.id);if(p){clearTimeout(p.timer);pending.delete(value.id);value.error?p.reject(new Error(value.error.message)):p.resolve(value.result);}};
  socket.onclose=()=>{for(const p of pending.values()){clearTimeout(p.timer);p.reject(new Error('Offline Chrome closed'));}pending.clear();};
  command=(method,params={})=>new Promise((resolve,reject)=>{
    if(socket.readyState!==WebSocket.OPEN){reject(new Error('Offline Chrome unavailable'));return;}
    const id=++sequence,timer=setTimeout(()=>{pending.delete(id);reject(new Error('Offline Chrome command timed out'));},20000);
    pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params}));
  });
  await command('Page.enable');await command('Network.enable');await command('Network.setBlockedURLs',{urls:['*']});
  const css=(await readFile('src/styles/index.css','utf8'))+'\n'+await readFile('src/styles/admin-workspace.css','utf8');
  const results=[];
  for(const scenario of ['creative-populated','creative-empty','operations-populated','operations-empty']){
    const markup=await readFile(`docs/security/evidence/admin-${scenario}.html`,'utf8');
    const banner='<div style="padding:.75rem 1rem;background:#fff0c7;color:#35271d;font:14px system-ui;text-align:center">OFFLINE UI TEST FIXTURE · Synthetic data only · No account or service records created</div>';
    for(const width of [1440,1024,768,390,320]){
      await command('Emulation.setDeviceMetricsOverride',{width,height:1100,deviceScaleFactor:1,mobile:width<600});
      const tree=await command('Page.getFrameTree');
      await command('Page.setDocumentContent',{frameId:tree.frameTree.frame.id,html:`<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>${css}</style></head><body>${banner}${markup}</body></html>`});
      const measurement=await command('Runtime.evaluate',{returnByValue:true,expression:`(()=>{
        const root=document.querySelector('.admin-workspace'),bound=root.getBoundingClientRect(),controls=[...root.querySelectorAll('button,input,textarea,select')];
        const grids=[...root.querySelectorAll('.admin-record-grid')];
        const fields=[...root.querySelectorAll('.admin-field textarea,.admin-field input,.admin-field select')];
        const records=[...root.querySelectorAll('.admin-record')];
        const email=root.querySelector('.admin-email-status');
        return {width:innerWidth,documentFits:document.documentElement.scrollWidth<=innerWidth,
          controlsContained:controls.every(e=>{const r=e.getBoundingClientRect(),p=e.closest('.panel,.admin-record,nav')?.getBoundingClientRect()??bound;return r.left>=p.left-.5&&r.right<=p.right+.5&&r.width>0}),
          controlsStyled:fields.every(e=>{const s=getComputedStyle(e);return parseFloat(s.borderRadius)>=8&&parseFloat(s.paddingTop)>=12}),
          buttonsStyled:controls.filter(e=>e.tagName==='BUTTON').every(e=>e.classList.contains('btn')&&e.getBoundingClientRect().height>=44),
          labelsAbove:fields.every(e=>e.getBoundingClientRect().top>=e.closest('label').getBoundingClientRect().top+14),
          mobileColumns:innerWidth>760||grids.every(e=>getComputedStyle(e).gridTemplateColumns.split(' ').length===1),
          desktopColumns:innerWidth<1440||grids.every(e=>getComputedStyle(e).gridTemplateColumns.split(' ').length>=2),
          recordsContained:records.every(e=>{const r=e.getBoundingClientRect();return r.left>=bound.left&&r.right<=bound.right+.5}),
          emailCompact:!email||email.getBoundingClientRect().height<550};
      })()`});
      const result={scenario,...measurement.result.value};
      result.passed=Object.entries(result).filter(([key])=>!['scenario','width'].includes(key)).every(([,value])=>value===true);
      results.push(result);
      if([1440,390].includes(width)){
        const shot=await command('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
        await writeFile(`docs/security/evidence/admin-${scenario}-${width}.png`,Buffer.from(shot.data,'base64'));
      }
    }
  }
  await writeFile('docs/security/evidence/admin-layout.json',JSON.stringify({kind:'Real components, offline Chrome, synthetic test data; no live account/service records',results},null,2));
  console.log(JSON.stringify({passed:results.filter(r=>r.passed).length,failed:results.filter(r=>!r.passed)},null,2));
  if(results.some(r=>!r.passed))process.exitCode=1;
} finally {
  if(command)await Promise.race([command('Browser.close').catch(()=>{}),pause(1500)]);
  socket?.close();if(chrome.exitCode===null)chrome.kill();
}
