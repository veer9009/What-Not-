import { readFile, writeFile, mkdir, mkdtemp } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { spawn } from 'node:child_process';

// Local presentation checks only. Recovery responses below are synthetic fixtures.
// No credentials, real email, database writes or backend recovery calls.
const folder = 'docs/security/evidence/combined-auth-review';
await mkdir(folder, { recursive: true });
const profile = await mkdtemp(join(tmpdir(), 'whatnot-auth-check-'));
const chrome = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--no-sandbox', '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], { windowsHide: true, stdio: ['ignore', 'ignore', 'pipe'] });
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
let ws, command;
try {
  let port;
  for (let attempt = 0; attempt < 100; attempt++) {
    try { port = Number((await readFile(join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]); break; } catch { await pause(100); }
  }
  if (!port) throw Error('Chrome startup failed');
  const pages = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  ws = new WebSocket(pages.find(page => page.type === 'page').webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
  let sequence = 0;
  const pending = new Map();
  ws.onmessage = event => { const result = JSON.parse(event.data), waiter = pending.get(result.id); if (waiter) { pending.delete(result.id); result.error ? waiter.reject(Error(result.error.message)) : waiter.resolve(result.result); } };
  command = (method, params = {}) => new Promise((resolve, reject) => { const id = ++sequence; pending.set(id, { resolve, reject }); ws.send(JSON.stringify({ id, method, params })); });
  const evaluate = async expression => { const result = await command('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); if (result.exceptionDetails) throw Error(JSON.stringify(result.exceptionDetails)); return result.result.value; };
  await command('Page.enable');
  await command('Page.addScriptToEvaluateOnNewDocument', { source: 'window.__gpsCalls=0;navigator.geolocation.getCurrentPosition=()=>{window.__gpsCalls++};navigator.geolocation.watchPosition=()=>{window.__gpsCalls++};' });
  await command('Page.addScriptToEvaluateOnNewDocument', { source: `{
    const originalFetch=window.fetch.bind(window);
    window.fetch=(input,options)=>{
      const path=new URL(typeof input==='string'?input:input.url,location.origin).pathname;
      if(path.includes('/auth/password-recovery/')){
        const body=path.endsWith('/request')?{message:'If eligible, a code will be sent.',challenge:'synthetic-preview-challenge',resend_after:60}:path.endsWith('/verify')?{reset_token:'synthetic-preview-reset'}:{message:'Password updated. Sign in again.'};
        return Promise.resolve(new Response(JSON.stringify(body),{status:path.endsWith('/request')?202:200,headers:{'Content-Type':'application/json','Cache-Control':'no-store'}}));
      }
      return originalFetch(input,options);
    };
  }` });
  const results = [];
  async function capture(path, step='initial') {
      await evaluate('Promise.all([...document.querySelectorAll(".login-discovery-art img")].map(i=>innerWidth<=700?Promise.resolve():i.decode().catch(()=>{})))');
      await pause(800);
      await evaluate('document.getAnimations().forEach(animation=>{if(animation.effect?.getTiming().iterations!==Infinity)animation.finish()})');
      await evaluate('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))');
      const geometry = await evaluate(`(()=>{const rect=e=>e.getBoundingClientRect(),visible=e=>rect(e).width>0&&rect(e).height>0;const form=document.querySelector('form'),art=document.querySelector('.login-discovery-art'),image=art.querySelector('picture img');return {width:innerWidth,documentFits:document.documentElement.scrollWidth<=innerWidth,overflow:[...document.querySelectorAll('.community-login,.login-form-wrap,form,aside')].filter(visible).filter(e=>e.scrollWidth>e.clientWidth+1).map(e=>e.className||e.tagName),fieldsContained:[...form.querySelectorAll('input,button,select')].filter(visible).every(e=>rect(e).left>=0&&rect(e).right<=innerWidth&&rect(e).height>=44),formTop:rect(form).top,formProminent:innerWidth>700||rect(form).top<390,artHiddenOnMobile:innerWidth>700||getComputedStyle(art).display==='none',splitLayout:innerWidth<=700||rect(document.querySelector('.login-form-wrap')).left>=rect(document.querySelector('aside')).right-1,imagesLoaded:innerWidth<=700||[...art.querySelectorAll('img')].every(i=>i.complete&&i.naturalWidth>0),neighborhoodUndistorted:innerWidth<=700||Math.abs(rect(image).width/rect(image).height-976/596)<.01,approvedAsset:!!(image.currentSrc||image.src).match(/neighborhood-world/),mapAbsent:![...document.images].some(i=>/india|boundary|country-outline|district-map|state-map/.test(i.currentSrc||i.src)),gpsCalls:window.__gpsCalls,links:[...form.querySelectorAll('a')].map(a=>a.getAttribute('href')),fontFaces:[...document.fonts].map(f=>({family:f.family,status:f.status}))};})()`);
      geometry.path=path;geometry.step=step;
      geometry.passed = geometry.documentFits && !geometry.overflow.length && geometry.fieldsContained && geometry.formProminent && geometry.artHiddenOnMobile && geometry.splitLayout && geometry.imagesLoaded && geometry.neighborhoodUndistorted && geometry.approvedAsset && geometry.mapAbsent && geometry.gpsCalls === 0;
      if (path.startsWith('/login')) geometry.passed &&= ['/forgot-password', '/register', '/register?role=seller'].every(link => geometry.links.includes(link));
      results.push(geometry);
      const screenshot = await command('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
      const name=path.slice(1).replace(/[^a-zA-Z0-9-]/g,'-');
      await writeFile(`${folder}/${name}-${step}-${geometry.width}.png`, Buffer.from(screenshot.data, 'base64'));
      console.log(JSON.stringify(geometry));
  }
  async function waitFor(expression){
    for(let attempt=0;attempt<100;attempt++){if(await evaluate(expression))return;await pause(200);}
    throw Error('Expected UI did not appear: '+expression);
  }
  async function fill(selector,text){await evaluate(`document.querySelector(${JSON.stringify(selector)}).focus()`);await command('Input.insertText',{text});}
  for (const path of ['/login', '/login/buyer', '/login/seller', '/register', '/register?role=seller', '/forgot-password']) {
    for (const width of [390, 768, 1440]) {
      await command('Emulation.setDeviceMetricsOverride', { width, height: 1000, deviceScaleFactor: 1, mobile: width < 600 });
      await command('Page.navigate', { url: `http://127.0.0.1:5173${path}` });
      let ready;
      for (let attempt = 0; attempt < 100; attempt++) { ready = await evaluate('!!document.querySelector(".community-login form input")'); if (ready) break; await pause(200); }
      if (!ready) throw Error(`Form failed to load: ${path}`);
      await capture(path);
      if(path==='/forgot-password'){
        await fill('input[name=email]','preview@example.test');
        await evaluate('document.querySelector("form button").click()');
        await waitFor('!!document.querySelector("input[name=otp]")');await capture(path,'code');
        await fill('input[name=otp]','123456');await evaluate('document.querySelector("form button").click()');
        await waitFor('!!document.querySelector("input[name=new-password]")');await capture(path,'password');
        await fill('input[name=new-password]','Synthetic-preview-password');await fill('input[name=confirm-password]','Synthetic-preview-password');
        await evaluate('document.querySelector("form button").click()');
        await waitFor('document.querySelector("form h2")?.textContent==="Password changed"');await capture(path,'complete');
      }
    }
  }
  await command('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] });
  const reducedMotion = await evaluate('getComputedStyle(document.querySelector(".login-neighborhood")).animationName==="none"');
  await command('Page.navigate', {url:'http://127.0.0.1:5173/forgot-password'});
  await waitFor('!!document.querySelector(".password-recovery-page input[name=email]")');
  await evaluate('document.querySelector("form button").click()'); await pause(200);
  const recoveryValidation = await evaluate('document.querySelector("[role=alert]")?.textContent.includes("Enter a valid email address.")');
  await command('Page.navigate', { url: 'http://127.0.0.1:5173/admin/login' });
  for(let attempt=0;attempt<100;attempt++){if(await evaluate('document.querySelector("h1")?.textContent==="What Not? Administration"'))break;await pause(200);}
  const adminSeparate = await evaluate('!document.querySelector(".login-discovery-art")&&document.querySelector("h1")?.textContent==="What Not? Administration"&&!!document.querySelector("input[aria-label=Email]")');
  const report = { results, reducedMotion, recoveryValidation, adminSeparate, limitations: 'Recovery browser responses are synthetic fixtures; no real mail or backend recovery request. Backend integration tests exercise security and revocation. Browser fonts may use system fallback. Live proxy configuration is not inspected.' };
  await writeFile(`${folder}/results.json`, JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ reducedMotion, recoveryValidation, adminSeparate }));
  if (results.some(result => !result.passed) || !reducedMotion || !recoveryValidation || !adminSeparate) process.exitCode = 1;
} finally {
  if (command) await command('Browser.close').catch(() => {});
  ws?.close(); chrome.stderr.destroy(); chrome.unref(); if (chrome.exitCode === null) chrome.kill();
}
