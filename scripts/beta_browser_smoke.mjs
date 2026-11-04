// Dependency-free CDP smoke runner. All accounts and data come from isolated pytest.
import {spawn} from 'node:child_process';
import {mkdtemp,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
const chunks=[];for await(const chunk of process.stdin)chunks.push(chunk);
const fixture=JSON.parse(Buffer.concat(chunks).toString());
const profile=await mkdtemp(join(tmpdir(),'whatnot-beta-edge-'));
const edge=spawn('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',[
  '--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check',
  '--disable-background-timer-throttling','--disable-renderer-backgrounding',
  '--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'
],{windowsHide:true,stdio:'ignore'});
const sockets=[];let browser;
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function connect(url){
  const ws=new WebSocket(url);sockets.push(ws);
  await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});
  let sequence=0;const calls=new Map();
  ws.onmessage=event=>{const value=JSON.parse(event.data);if(value.id){const item=calls.get(value.id);calls.delete(value.id);value.error?item.reject(new Error(value.error.message)):item.resolve(value.result);}};
  return(method,params={})=>new Promise((resolve,reject)=>{const id=++sequence;calls.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
}
async function evaluate(cdp,expression){const r=await cdp('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error(r.exceptionDetails.text);return r.result.value;}
async function wait(cdp,expression){for(let i=0;i<100;i++){if(await evaluate(cdp,expression))return;await sleep(100);}throw new Error('Browser condition timed out: '+expression+'; page text: '+(await evaluate(cdp,'document.body.innerText')).slice(0,2000));}
async function text(cdp,value){await wait(cdp,`document.body.textContent.includes(${JSON.stringify(value)})`);}
async function click(cdp,label,tag='button'){
  const selector=JSON.stringify(tag),name=JSON.stringify(label);
  await wait(cdp,`[...document.querySelectorAll(${selector})].some(e=>e.textContent.trim()===${name}&&!e.disabled)`);
  await evaluate(cdp,`[...document.querySelectorAll(${selector})].find(e=>e.textContent.trim()===${name}).click()`);
}
async function fill(cdp,selector,value){
  await wait(cdp,`Boolean(document.querySelector(${JSON.stringify(selector)}))`);
  await evaluate(cdp,`(()=>{const e=document.querySelector(${JSON.stringify(selector)});const prototype=e.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:e.tagName==='SELECT'?HTMLSelectElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(prototype,'value').set.call(e,${JSON.stringify(value)});e.dispatchEvent(new Event(e.tagName==='SELECT'?'change':'input',{bubbles:true}));})()`);
}
async function navigate(cdp,path){
  // Navigating to an already mounted route is not a data refresh. Exercise an
  // actual leave/return as a user would, preserving memory-held authentication.
  if(await evaluate(cdp,`location.pathname===${JSON.stringify(path)}`)){
    const away=path.startsWith('/seller')?'/seller/notifications':path.startsWith('/admin')?'/admin/notifications':'/buyer/notifications';
    await evaluate(cdp,`(()=>{history.pushState({},'',${JSON.stringify(away)});window.dispatchEvent(new PopStateEvent('popstate'));})()`);await sleep(100);
  }
  await evaluate(cdp,`(()=>{history.pushState({},'',${JSON.stringify(path)});window.dispatchEvent(new PopStateEvent('popstate'));})()`);await sleep(100);
}
async function page(role,name){
  const result=await browser('Target.createTarget',{url:`http://127.0.0.1:8000/${role==='ADMIN'?'admin/login':'login/'+role.toLowerCase()}`});
  const targets=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  const target=targets.find(t=>t.id===result.targetId);const cdp=await connect(target.webSocketDebuggerUrl);
  await fill(cdp,'input[name=email]',name.toLowerCase()+'@browser.example.com');
  await fill(cdp,'input[name=password]',fixture.password);await click(cdp,'Sign in');await text(cdp,role.toLowerCase()+' workspace');return cdp;
}
let port;
try{
  for(let i=0;i<100;i++){try{port=Number((await readFile(join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]);break;}catch{await sleep(100);}}
  if(!port)throw new Error('Headless Edge debugging did not start');
  const version=await(await fetch(`http://127.0.0.1:${port}/json/version`)).json();browser=await connect(version.webSocketDebuggerUrl);
  const buyer=await page('BUYER','Buyer'),other=await page('BUYER','OtherBuyer'),seller=await page('SELLER','Seller'),otherSeller=await page('SELLER','OtherSeller'),admin=await page('ADMIN','Admin');
  // Five distinct real browser tabs and actual database-backed authentication.
  await navigate(other,`/buyer/orders/${fixture.orders[0]}`);await text(other,'You do not have permission');
  await navigate(otherSeller,`/seller/orders/${fixture.orders[0]}`);await text(otherSeller,'You do not have permission');
  for(const [index,id] of fixture.orders.entries()){
    await navigate(seller,`/seller/orders/${id}`);await click(seller,'Accept order');await click(seller,'View delivery details');await text(seller,'Synthetic delivery lane');
    await click(seller,'Start preparing');await click(seller,'Out for delivery');await click(seller,'Mark delivered');
    await navigate(buyer,`/buyer/orders/${id}`);await click(buyer,index===0?'Yes, I received it':'Report not received');await text(buyer,index===0?'Completed':'Delivery disputed');
  }
  await navigate(admin,'/admin/operations');await fill(admin,'textarea[aria-label="Investigation reason"]','Browser investigated synthetic delivery');await click(admin,`Resolve cancelled #${fixture.orders[1]}`);await text(admin,'Action recorded');
  await navigate(buyer,'/buyer/notifications');await text(buyer,'Order update');await click(buyer,'Mark all as read');await text(buyer,'0 unread');
  console.log('PASS: order seller progression, scoped fulfillment, buyer completion/dispute, admin resolution, notifications, outsider denial');
  await navigate(buyer,`/buyer/properties/${fixture.property}`);await text(buyer,'Browser sale home');
  if(await evaluate(buyer,"document.body.innerText.includes('Synthetic private property lane')"))throw new Error('Property address leaked before appointment');
  await fill(buyer,'textarea', 'Browser enquiry');await click(buyer,'Send enquiry');await text(buyer,'Saved.');
  const appointment=new Date(Date.now()+86400000).toISOString().slice(0,16);await fill(buyer,'input[type="datetime-local"]',appointment);await click(buyer,'Request visit');await text(buyer,'Saved.');
  await navigate(seller,'/seller/properties/requests');await text(seller,'Browser enquiry');await fill(seller,'textarea','Browser reply');await click(seller,'Send response');await click(seller,'ACCEPT');await text(seller,'CONFIRMED');
  await navigate(buyer,'/buyer/properties/requests');await text(buyer,'Browser reply');await click(buyer,'View appointment address');await text(buyer,'Synthetic private property lane');
  await navigate(seller,'/seller/properties');await click(seller,'Mark sold');await text(seller,'Saved.');await click(buyer,'Reload requests');await text(buyer,'CANCELLED');
  if(await evaluate(buyer,"document.body.innerText.includes('Synthetic private property lane')"))throw new Error('Sold appointment address remained visible');
  console.log('PASS: sale enquiry/reply, visit confirmation, private-address gate and sale revocation');
  await navigate(buyer,'/buyer/creative');await text(buyer,'Browser video edit');await fill(buyer,'textarea[name=text]','Browser edit please');await click(buyer,'Send private enquiry');await text(buyer,'Saved.');
  await navigate(seller,'/seller/creative');await text(seller,'Browser edit please');await fill(seller,'textarea[name=terms]','Browser immutable agreed scope');await fill(seller,'form:has(textarea[name=terms]) input[name=amount]','100');await click(seller,'Send quote');await text(seller,'Saved.');
  await navigate(buyer,'/buyer/creative');await click(buyer,'Accept these terms');await text(buyer,'Agreed: INR 100.00');
  await navigate(seller,'/seller/creative');await click(seller,'Mark delivered');await text(seller,'DELIVERED');
  await navigate(buyer,'/buyer/creative');await click(buyer,'Confirm received and complete');await fill(buyer,'textarea[name=review]','Browser completed work review');await click(buyer,'Submit review');await text(buyer,'Review saved.');
  console.log('PASS: Creative RFQ/quote/acceptance/delivery/buyer completion/review in real browser');
  // Check live coarse discovery and public copy against the production bundle.
  await navigate(buyer,'/buyer');await click(buyer,'Use Browser home for discovery');await text(buyer,'Browser vase');
  if(await evaluate(buyer,"document.querySelector('.buyer-grid')?.innerText.includes('km away')"))throw new Error('Exact distance visible');
  console.log('PASS: production-bundle locality discovery without numeric point distance');
  await click(buyer,'View Browser vase','a');await click(buyer,'Add to Cart');await click(buyer,'View cart','a');
  await fill(buyer,'select[aria-label="Delivery address"]',fixture.address);await click(buyer,'Place orders');
  await wait(buyer,"[...document.querySelectorAll('a')].some(e=>/^View order [0-9]+$/.test(e.textContent.trim()))");
  await text(buyer,'Your local basket is empty');
  console.log('PASS: discovery-to-cart checkout with saved address and current-price confirmation');
}catch(error){console.error(String(error));process.exitCode=1;}
finally{
  if(browser){try{await browser('Browser.close');}catch{}}
  for(const socket of sockets)socket.close();
  if(edge.exitCode===null)edge.kill();
  await sleep(1000);
  const checked=resolve(profile);if(!checked.startsWith(resolve(tmpdir())+'\\whatnot-beta-edge-'))throw new Error('Unexpected browser profile path');
  await rm(checked,{recursive:true,force:true,maxRetries:10,retryDelay:100});
}
