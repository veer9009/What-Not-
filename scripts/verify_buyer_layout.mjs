// Offline browser geometry using actual React markup, synthetic records, no API.
import { readFile, mkdtemp, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { spawn } from 'node:child_process';

const baseline=process.argv.includes('--baseline-css');
const profile=await mkdtemp(join(tmpdir(),'whatnot-buyer-layout-'));
const chrome=spawn('C:/Program Files/Google/Chrome/Application/chrome.exe',[
  '--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-extensions',
  '--no-sandbox','--disable-gpu-sandbox','--disable-background-networking','--disable-component-update',
  '--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank',
],{windowsHide:true,stdio:['ignore','ignore','pipe']});
let diagnostics='';chrome.stderr.on('data',chunk=>{diagnostics+=String(chunk);});
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
let socket,command,stage='startup';
try{
  let port;
  for(let i=0;i<100;i++){
    try{port=Number((await readFile(join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]);break;}
    catch{if(chrome.exitCode!==null)throw new Error('Layout Chrome startup failed');await pause(100);}
  }
  if(!port)throw new Error('Layout Chrome startup timed out');
  const pages=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  socket=new WebSocket(pages.find(page=>page.type==='page').webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
  let sequence=0;const pending=new Map();
  socket.onmessage=event=>{const response=JSON.parse(event.data),p=pending.get(response.id);if(p){clearTimeout(p.timer);pending.delete(response.id);response.error?p.reject(new Error(response.error.message)):p.resolve(response.result);}};
  socket.onclose=()=>{for(const p of pending.values()){clearTimeout(p.timer);p.reject(new Error('Layout Chrome connection closed'));}pending.clear();};
  command=(method,params={})=>new Promise((resolve,reject)=>{
    const id=++sequence,timer=setTimeout(()=>{pending.delete(id);reject(new Error('Layout Chrome command timed out'));},20000);
    pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params}));
  });
  stage='enable page';await command('Page.enable');stage='enable network';await command('Network.enable');stage='block network';await command('Network.setBlockedURLs',{urls:['*']});
  const css=await readFile('src/styles/index.css','utf8')+(baseline?'':'\n'+await readFile('src/styles/buyer-checkout.css','utf8'));
  const markup=await readFile('docs/security/evidence/buyer-layout-fixture.html','utf8');
  const html=`<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>${css}</style></head><body>${markup}</body></html>`;
  const results=[];
  for(const width of [1440,1280,1024,768,390,320]){
    stage=`viewport ${width}`;
    await command('Emulation.setDeviceMetricsOverride',{width,height:1200,deviceScaleFactor:1,mobile:width<600});
    const tree=await command('Page.getFrameTree');await command('Page.setDocumentContent',{frameId:tree.frameTree.frame.id,html});
    const {result}=await command('Runtime.evaluate',{expression:`(()=>{
      const cart=document.querySelector('.cart-layout'),list=cart.querySelector('.cart-list'),summary=cart.querySelector('.order-card'),form=document.querySelector('.address-form'),select=cart.querySelector('select');
      const rect=e=>e.getBoundingClientRect(),s=rect(summary),l=rect(list),f=rect(form),dropdown=rect(select),link=rect(cart.querySelector('.checkout-address .text-link'));
      const controls=[...form.querySelectorAll('input:not([type=checkbox])')];
      const containers=[cart,form,...cart.querySelectorAll('.cart-item,.order-card,.checkout-address'),...form.querySelectorAll('.form-grid,.address-location')];
      return {width:innerWidth,summaryWidth:s.width,
        layoutCorrect:innerWidth>1100?s.left>=l.right&&s.width>=320&&s.width<=380:s.top>=l.bottom&&Math.abs(s.width-l.width)<2,
        documentFits:document.documentElement.scrollWidth<=innerWidth,
        containersFit:containers.every(e=>e.scrollWidth<=e.clientWidth+1),
        controlsContained:controls.every(e=>rect(e).left>=f.left&&rect(e).right<=f.right&&rect(e).width>100),
        addressColumnsCorrect:getComputedStyle(form.querySelector('.form-grid')).gridTemplateColumns.split(' ').length===(innerWidth<=600?1:2),
        dropdownContained:dropdown.left>=s.left&&dropdown.right<=s.right&&dropdown.width>=s.width-80,
        manageLinkBelow:link.top>=dropdown.bottom,
        quantityTouchTargets:[...cart.querySelectorAll('.quantity button')].every(e=>rect(e).width>=40&&rect(e).height>=40),
        buttonFullWidth:rect(summary.querySelector('.wide')).width>=s.width-80,
        checkboxCompact:rect(form.querySelector('input[type=checkbox]')).width<30};
    })()`,returnByValue:true});
    const value=result.value;
    value.passed=Object.entries(value).filter(([key])=>!['width','summaryWidth'].includes(key)).every(([,entry])=>entry===true);
    results.push(value);
    if(!baseline&&[1440,390].includes(width)){
      const shot=await command('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
      await writeFile(`docs/security/evidence/buyer-layout-${width}.png`,Buffer.from(shot.data,'base64'));
    }
  }
  await writeFile(`docs/security/evidence/buyer-layout${baseline?'-baseline':''}.json`,JSON.stringify({kind:'Actual React markup, synthetic records, offline Chrome geometry',results},null,2));
  console.log(JSON.stringify(results));if(results.some(result=>!result.passed))process.exitCode=1;
}catch(error){
  console.error(JSON.stringify({stage,error:String(error),chromeExitCode:chrome.exitCode,diagnostics}));process.exitCode=1;
}finally{
  if(command)await Promise.race([command('Browser.close').catch(()=>{}),pause(1500)]);
  socket?.close();if(chrome.exitCode===null)chrome.kill();
}
