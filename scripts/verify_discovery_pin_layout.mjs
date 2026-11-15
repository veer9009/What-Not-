// Layout-only Chrome check: actual stylesheet, synthetic markup, no app/API/DB.
import { readFile, mkdtemp, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { spawn } from 'node:child_process';

const profile = await mkdtemp(join(tmpdir(), 'whatnot-pin-layout-'));
const chrome = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', [
  '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
  '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank',
], { windowsHide:true, stdio:'ignore' });
const pause = ms => new Promise(resolve => setTimeout(resolve,ms));
let cdp; let socket;
function connect(url) {
  return new Promise((resolve,reject) => {
    socket = new WebSocket(url); let id=0; const pending=new Map();
    socket.onerror=()=>reject(new Error('Layout browser connection failed'));
    socket.onmessage=event=>{const value=JSON.parse(event.data);if(value.id){const p=pending.get(value.id);pending.delete(value.id);value.error?p.reject(new Error(value.error.message)):p.resolve(value.result);}};
    socket.onopen=()=>resolve((method,params={})=>new Promise((resolve,reject)=>{
      const ticket=++id; pending.set(ticket,{resolve,reject}); socket.send(JSON.stringify({id:ticket,method,params}));
    }));
  });
}
try {
  let port;
  for(let attempt=0;attempt<100;attempt++) {
    try {port=Number((await readFile(join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]);break;}
    catch {if(chrome.exitCode!==null)throw new Error('Owned layout Chrome exited before startup');await pause(100);}
  }
  if(!port)throw new Error('Owned layout Chrome startup timed out');
  const pages=await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  const page=pages.find(page=>page.type==='page');
  if(!page)throw new Error('Owned layout browser has no page');
  cdp=await connect(page.webSocketDebuggerUrl);
  await cdp('Page.enable');await cdp('Network.enable');
  await cdp('Network.setBlockedURLs',{urls:['*']});
  const css=await readFile('src/styles/index.css','utf8');
  const markup=await readFile('docs/security/evidence/discovery-layout-fixture.html','utf8');
  const html=`<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><style>${css}</style></head><body>${markup}</body></html>`;
  const results=[];
  for(const width of [1440,1024,768,390,320]) {
    await cdp('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:width<600});
    const tree=await cdp('Page.getFrameTree');
    await cdp('Page.setDocumentContent',{frameId:tree.frameTree.frame.id,html});
    const measurement=await cdp('Runtime.evaluate',{expression:`(()=>{const input=document.querySelector('input[name=pincode]'),label=input.closest('label'),r=input.getBoundingClientRect(),l=label.getBoundingClientRect(),p=input.closest('section').getBoundingClientRect(),s=getComputedStyle(input),ls=getComputedStyle(label);return {viewport:innerWidth,inputHeight:r.height,inputWidth:r.width,leftPadding:parseFloat(s.paddingLeft),labelGap:parseFloat(ls.rowGap)||0,labelDisplay:ls.display,contained:r.left>=p.left&&r.right<=p.right,documentFits:document.documentElement.scrollWidth<=innerWidth,labelAboveInput:r.top>=l.top+16}})()`,returnByValue:true});
    const value=measurement.result.value;
    const extra=await cdp('Runtime.evaluate',{expression:`(()=>{const panel=document.querySelector('.discovery-location'),bounds=panel.getBoundingClientRect(),inputs=[...panel.querySelectorAll('input')].map(e=>e.getBoundingClientRect()),buttons=[...panel.querySelectorAll('button.btn')].map(e=>e.getBoundingClientRect()),radius=[...panel.querySelectorAll('.radius-select button')].map(e=>e.getBoundingClientRect()),pin=panel.querySelector('[name=pincode]').getBoundingClientRect(),help=document.querySelector('#discovery-pin-help').getBoundingClientRect(),cards=[...document.querySelectorAll('#homemade-catalogue .product-card')].map(e=>e.getBoundingClientRect());return {controlsContained:[...inputs,...buttons,...radius].every(r=>r.left>=bounds.left&&r.right<=bounds.right),buttonWidthsConsistent:buttons.every(r=>Math.abs(r.width-buttons[0].width)<1),touchTargets:[...buttons,...radius].every(r=>r.height>=44),radiusControls:radius.length===3&&radius.every(r=>r.width>=44),coordinatesAligned:innerWidth<=520?inputs[1].top>=inputs[0].bottom:Math.abs(inputs[0].top-inputs[1].top)<1,helperBelow:help.top>=pin.bottom+8,savedActionLeft:Math.abs(buttons[2].left-inputs[2].left)<1,cardsAligned:cards.length===2&&(innerWidth<=520?cards[1].top>=cards[0].bottom:Math.abs(cards[0].top-cards[1].top)<1&&Math.abs(cards[0].height-cards[1].height)<1)}})()`,returnByValue:true});
    Object.assign(value,extra.result.value);
    value.passed=value.inputHeight>=44&&value.leftPadding>=12&&value.labelGap>=8&&value.labelDisplay==='grid'&&value.contained&&value.documentFits&&value.labelAboveInput&&value.inputWidth>=200&&Object.values(extra.result.value).every(Boolean);
    results.push(value);
  }
  const result={kind:'Chrome geometry of actual React-rendered synthetic fixture; blocked network, no live API/database/browser interaction',results,passed:results.every(result=>result.passed)};
  await writeFile('docs/security/evidence/chrome-pin-layout.json',JSON.stringify(result,null,2));
  console.log(JSON.stringify(result,null,2));
  if(!result.passed)process.exitCode=1;
} finally {
  // Chrome may close the websocket before replying to Browser.close.
  // Bound shutdown so a successful measurement cannot leave top-level await unsettled.
  if(cdp)await Promise.race([cdp('Browser.close').catch(()=>{}),pause(1500)]);
  socket?.close();
  // Stop only the browser process created above if protocol shutdown failed.
  if(chrome.exitCode===null)chrome.kill();
  // Keep the generated temporary profile; no filesystem cleanup/deletion.
}
