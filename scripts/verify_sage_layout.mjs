// Offline Chrome geometry checks. Uses real rendered components and synthetic records.
import { readFile, writeFile, mkdir, mkdtemp } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { spawn } from 'node:child_process';

const folder='docs/security/evidence/sage';
await mkdir(folder,{recursive:true});
const profile=await mkdtemp(join(tmpdir(),'whatnot-sage-'));
const chrome=spawn('C:/Program Files/Google/Chrome/Application/chrome.exe',[
  '--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check',
  '--disable-extensions','--no-sandbox','--disable-gpu-sandbox',
  '--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank',
],{windowsHide:true,stdio:['ignore','ignore','pipe']});
let diagnostics='';chrome.stderr.on('data',chunk=>diagnostics+=chunk);
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
let socket,command;
try {
  let port;
  for(let i=0;i<100;i++) {
    try { port=Number((await readFile(join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]); break; }
    catch { if(chrome.exitCode!==null) throw Error('Chrome failed to start'); await pause(100); }
  }
  if(!port) throw Error('Chrome startup timed out');
  const pages=await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  socket=new WebSocket(pages.find(p=>p.type==='page').webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
  let sequence=0;const pending=new Map();
  socket.onmessage=event=>{const response=JSON.parse(event.data),p=pending.get(response.id);if(p){clearTimeout(p.timer);pending.delete(response.id);response.error?p.reject(Error(response.error.message)):p.resolve(response.result);}};
  command=(method,params={})=>new Promise((resolve,reject)=>{const id=++sequence,timer=setTimeout(()=>{pending.delete(id);reject(Error(`Timed out: ${method}`));},20000);pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params}));});
  await command('Page.enable');
  const css=(await Promise.all(['index','properties','buyer-checkout','admin-workspace','product-images','marketplace'].map(name=>readFile(`src/styles/${name}.css`,'utf8')))).join('\n');
  const fixtures=[
    ...['home','login','register','product-form','product-detail','seller-location','seller-dashboard','admin-products'].map(name=>[name,`${folder}/${name}.html`]),
    ['buyer-cart-address','docs/security/evidence/buyer-layout-fixture.html'],
    ['buyer-discovery','docs/security/evidence/discovery-layout-fixture.html'],
    ['properties','docs/security/evidence/property-layout-fixture.html'],
    ['admin-operations','docs/security/evidence/admin-operations-populated.html'],
    ['admin-services','docs/security/evidence/admin-creative-populated.html'],
  ];
  const results=[];
  for(const [name,file] of fixtures) {
    const markup=await readFile(file,'utf8');
    for(const width of [360,390,768,1024,1440]) {
      await command('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:width<600});
      const {frameTree}=await command('Page.getFrameTree');
      await command('Page.setDocumentContent',{frameId:frameTree.frame.id,html:`<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700&display=swap" rel="stylesheet"><style>${css}</style></head><body>${markup}</body></html>`});
      await command('Runtime.evaluate',{expression:'Promise.race([document.fonts.ready,new Promise(r=>setTimeout(r,1500))])',awaitPromise:true});
      const {result}=await command('Runtime.evaluate',{expression:`(()=>{
        const rect=e=>e.getBoundingClientRect();
        const visible=e=>rect(e).width>0&&rect(e).height>0;
        const overflow=[...document.querySelectorAll('main,section,article,form,.panel,.product-card,.product-body,.form-grid,.page-top')].filter(visible).filter(e=>e.scrollWidth>e.clientWidth+2).map(e=>e.className||e.tagName);
        const outside=[...document.querySelectorAll('input:not([type=checkbox]):not([type=radio]),textarea,select')].filter(visible).filter(e=>rect(e).left<0||rect(e).right>innerWidth+1).map(e=>e.name||e.tagName);
        const cards=[...document.querySelectorAll('.product-card .product-image')];
        return {width:innerWidth,documentFits:document.documentElement.scrollWidth<=innerWidth+1,overflow,controlsOutside:outside,imageRatiosCorrect:cards.every(e=>Math.abs(rect(e).width/rect(e).height-4/3)<.02),bodyFont:getComputedStyle(document.body).fontFamily,headingFont:document.querySelector('h1,h2')?getComputedStyle(document.querySelector('h1,h2')).fontFamily:null,fontFaces:[...document.fonts].map(f=>({family:f.family,status:f.status}))};
      })()`,returnByValue:true});
      const value={page:name,...result.value};
      value.passed=value.documentFits&&!value.overflow.length&&!value.controlsOutside.length&&value.imageRatiosCorrect;
      results.push(value);
      if([390,1440].includes(width)&&['home','buyer-discovery','buyer-cart-address','product-form','admin-operations'].includes(name)) {
        await command('Runtime.evaluate',{expression:'Promise.race([Promise.all([...document.images].map(i=>i.complete?Promise.resolve():new Promise(r=>{i.onload=r;i.onerror=r}))),new Promise(r=>setTimeout(r,3000))])',awaitPromise:true});
        const shot=await command('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
        await writeFile(`${folder}/${name}-${width}.png`,Buffer.from(shot.data,'base64'));
      }
      console.log(`${name} ${width}: ${value.passed?'PASS':'FAIL'} ${JSON.stringify({overflow:value.overflow,outside:value.controlsOutside})}`);
    }
  }
  await writeFile(`${folder}/layout-results.json`,JSON.stringify({kind:'Chrome geometry; synthetic records; no backend writes',limitations:'External font and image requests may be unavailable in static fixtures. Empty fontFaces means geometry was checked with fallback fonts, not downloaded Inter/Jakarta.',results},null,2));
  if(results.some(r=>!r.passed))process.exitCode=1;
} catch(error) {
  console.error(JSON.stringify({error:String(error),diagnostics}));process.exitCode=1;
} finally {
  if(command)await Promise.race([command('Browser.close').catch(()=>{}),pause(1500)]);
  socket?.close();if(chrome.exitCode===null)chrome.kill();
}
