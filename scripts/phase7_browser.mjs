// Live browser checks using installed Chrome and Node's native WebSocket only.
// Credentials arrive over stdin and remain in memory. Errors emit fixed stage labels.
import assert from 'node:assert/strict';
import { browserRoute } from './phase7_network.mjs';
let input='';for await(const chunk of process.stdin)input+=chunk;
const config=JSON.parse(input);
const ws=new WebSocket(config.ws);
await new Promise((resolve,reject)=>{ws.addEventListener('open',resolve,{once:true});ws.addEventListener('error',reject,{once:true});});
let sequence=0;let stage='initialization';let lastCheck='page state';let runtimeErrors=0;
const waiting=new Map();const requests=[];
const networkFailures=[];
function command(method,params={}){
  const id=++sequence;
  return new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>{waiting.delete(id);reject(new Error('Protocol timeout'));},20000);
    waiting.set(id,{resolve,reject,timer});ws.send(JSON.stringify({id,method,params}));
  });
}
ws.addEventListener('message',event=>{
  const message=JSON.parse(event.data);
  if(message.id){const pending=waiting.get(message.id);if(!pending)return;waiting.delete(message.id);clearTimeout(pending.timer);message.error?pending.reject(new Error('Protocol operation failed')):pending.resolve(message.result);}
  if(message.method==='Runtime.exceptionThrown')runtimeErrors++;
  if(message.method==='Network.loadingFailed'&&/^net::[A-Z_]+$/.test(message.params.errorText))networkFailures.push(message.params.errorText);
  if(message.method==='Network.requestWillBeSent'){
    const request=message.params.request;
    requests.push({path:new URL(request.url).pathname,method:request.method});
  }
  if(message.method==='Fetch.requestPaused'){
    const {requestId,request}=message.params;
    const route=browserRoute(request.url,config);
    const action=route.action==='block'
      ?command('Fetch.failRequest',{requestId,errorReason:'BlockedByClient'})
      :command('Fetch.continueRequest',{requestId,...(route.action==='redirect'?{url:route.url}:{})});
    action.catch(()=>{});
  }
});
async function evaluate(expression){
  const response=await command('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true,userGesture:true});
  if(response.exceptionDetails)throw new Error('Browser evaluation failed');
  return response.result.value;
}
async function until(expression,description='page state'){
  lastCheck=description;
  const deadline=Date.now()+15000;
  while(Date.now()<deadline){if(await evaluate(expression))return;await new Promise(resolve=>setTimeout(resolve,60));}
  throw new Error('Expected browser state unavailable');
}
const text=value=>`document.body.textContent.includes(${JSON.stringify(value)})`;
async function settle(){await evaluate('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))');}
async function click(label){
  const expression=`(()=>{const el=[...document.querySelectorAll('button,a')].find(el=>el.textContent.trim()===${JSON.stringify(label)}&&!el.disabled);if(!el)return false;el.click();return true;})()`;
  await until(expression,`click ${label}`);
  await settle();
}
async function fill(label,value,scope='document'){
  const expression=`(()=>{const el=${scope}.querySelector('input[aria-label=${JSON.stringify(label)}]');if(!el)return false;Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el,${JSON.stringify(value)});el.dispatchEvent(new Event('input',{bubbles:true}));return true;})()`;
  await until(expression,`input ${label}`);
  await settle();
}
async function navigate(path){await command('Page.navigate',{url:config.ui+path});await until("document.readyState==='complete'");}
async function login(role,email){
  await navigate(`/login/${role}`);await fill('Email address',email);await fill('Password',config.password);await click('Sign in');await until(text('Log out'));
}
async function api(method,path,body,token){
  const response=await fetch(config.api+'/api/v1'+path,{method,headers:{'Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{})},body:body===undefined?undefined:JSON.stringify(body)});
  if(!response.ok)throw new Error('API operation failed');
  return response.json();
}
async function sizes(){
  for(const [width,height]of [[1280,900],[768,1024],[390,844],[320,800]]){
    await command('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false});
    await evaluate('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))');
    assert(await evaluate('document.documentElement.scrollWidth<=innerWidth+1'),'Viewport overflow');
  }
  await command('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
}
async function manual(latitude,longitude){await fill('Latitude',String(latitude));await fill('Longitude',String(longitude));await click('Use for discovery');}
const discoveryCount=()=>requests.filter(r=>r.path==='/api/v1/discovery/products').length;
try{
  await command('Page.enable');await command('Runtime.enable');await command('Network.enable');
  await command('Fetch.enable',{patterns:[{urlPattern:'*',requestStage:'Request'}]});
  await command('Network.setBlockedURLs',{urls:['https://*']});
  await command('Page.addScriptToEvaluateOnNewDocument',{source:"window.locationRequests=0;const original=navigator.geolocation?.getCurrentPosition.bind(navigator.geolocation);if(original)navigator.geolocation.getCurrentPosition=(...args)=>{window.locationRequests++;return original(...args);};"});
  stage='real API setup';
  for(const [role,name]of [['SELLER','Seller'],['BUYER','Buyer']]){
    await api('POST','/auth/register',{name,email:`${name.toLowerCase()}.phase7@example.com`,phone:`phase7-${name.toLowerCase()}`,password:config.password,role});
  }
  const seller=(await api('POST','/auth/login',{email:'seller.phase7@example.com',password:config.password})).access_token;
  const buyer=(await api('POST','/auth/login',{email:'buyer.phase7@example.com',password:config.password})).access_token;
  const admin=(await api('POST','/auth/login',{email:'admin.phase7@example.com',password:config.adminPassword})).access_token;
  await api('POST','/sellers/me',{shop_name:'Phase 7 maker',phone:'phase7-seller',latitude:0,longitude:0},seller);
  const product=await api('POST','/products',{name:'Phase 7 vase',description:'Isolated handmade product',price:'250.00',stock_quantity:5,category:'Crafts',delivery_radius_km:1},seller);
  await api('POST',`/admin/products/${product.id}/approve`,undefined,admin);
  const source={location:{latitude:0,longitude:.001}};
  assert.deepEqual(await api('POST','/discovery/products',source,buyer),[],'Unconfirmed seller must be hidden');
  await api('POST','/addresses',{label:'Home',address_line1:'Test dispatch lane',city:'Test city',state:'Test state',pincode:'400001',latitude:0,longitude:.001,is_default:true},buyer);
  stage='seller login';await login('seller','seller.phase7@example.com');
  stage='seller profile';await click('Shop profile');await until(text('Dispatch location not confirmed'));
  assert.equal(await evaluate('window.locationRequests'),0);
  stage='seller confirmation';await click('Set dispatch location');await click('Confirm dispatch location');await until(text('Dispatch location confirmed'));
  stage='seller responsive profile';await sizes();
  stage='buyer login';
  await login('buyer','buyer.phase7@example.com');await until(text('Location not set'));
  stage='buyer no silent GPS or discovery';
  assert.equal(await evaluate('window.locationRequests'),0);
  assert.equal(discoveryCount(),0);
  stage='buyer manual point submission';
  await manual(0,.001);await until(text('Phase 7 vase'));
  stage='buyer responsive discovery';await sizes();
  const visible=await api('POST','/discovery/products',source,buyer);
  assert.equal(visible.length,1);
  assert(!['latitude','longitude','phone','user_id','seller','dispatch_location_confirmed_at'].some(key=>key in visible[0]));
  stage='saved address selection';
  await click('Use Home for discovery');await until(text('Phase 7 vase'));
  stage='eligible detail navigation';await click('View Phase 7 vase');await until(text('Checkout unavailable'));
  assert(await evaluate("[...document.querySelectorAll('button')].some(b=>b.textContent==='Checkout unavailable'&&b.disabled)"));
  assert(!await evaluate("[...document.querySelectorAll('button')].some(b=>/add to cart/i.test(b.textContent))"));
  stage='detail responsive layout';await sizes();
  stage='return with same discovery source';await click('Back to discovery');await until(text('Phase 7 vase'));
  stage='browser GPS draft and permission states';
  await command('Browser.grantPermissions',{permissions:['geolocation'],origin:config.ui});
  await command('Emulation.setGeolocationOverride',{latitude:0,longitude:.001,accuracy:1});
  const before=discoveryCount();await click('Use current location');await until(text('Location acquired'));
  assert.equal(discoveryCount(),before,'GPS draft must not trigger discovery');
  await click('Use for discovery');await until(text('Phase 7 vase'));
  await evaluate("navigator.geolocation.getCurrentPosition=(_success,error)=>error({code:1})");
  await click('Use current location');await until(text('Location permission was denied'));
  await evaluate("Object.defineProperty(navigator,'geolocation',{value:undefined,configurable:true})");
  await click('Use current location');await until(text('Browser geolocation is unavailable'));
  stage='radius exclusion and dispatch changes';
  await manual(0,1);await until(text('No products nearby'));
  await api('PATCH','/sellers/me/dispatch-location',{latitude:1,longitude:1},seller);
  await click('Use Home for discovery');await until(text('No products nearby'));
  await api('PATCH','/sellers/me/dispatch-location',{latitude:0,longitude:0},seller);
  await click('Refresh nearby products');await until(text('Phase 7 vase'));
  stage='session privacy and checkout guard';
  assert.equal(await evaluate('localStorage.length+sessionStorage.length'),0);
  await click('Log out');await until(text('Welcome back'));
  assert(!requests.some(r=>r.path==='/api/v1/orders'&&r.method==='POST'));
  assert.equal(runtimeErrors,0);
  console.log('Browser checks passed: real seller confirmation; manual/address/GPS discovery; denied/unsupported states; radius/dispatch changes; detail checkout guard; session privacy; 4 widths x 3 screens.');
}catch(failure){
  console.log(`Browser check failed at fixed stage: ${stage}.`);
  console.log(`Last browser check: ${lastCheck}.`);
  const safeMessages=['Viewport overflow','Browser evaluation failed','Protocol operation failed','Protocol timeout','Expected browser state unavailable','API operation failed'];
  if(safeMessages.includes(failure.message))console.log(`Diagnostic: ${failure.message}.`);
  console.log(`Browser network error categories: ${[...new Set(networkFailures)].join(', ')||'none'}.`);
  process.exitCode=1;
}finally{
  try{await command('Browser.close');}catch{}
  for(const pending of waiting.values()){clearTimeout(pending.timer);pending.reject(new Error('Browser closed'));}
  waiting.clear();ws.close();
}
