import { createRequire } from 'node:module';
import { mkdir } from 'node:fs/promises';
import assert from 'node:assert/strict';
const require=createRequire(import.meta.url);
const { chromium }=require(process.env.WHATNOT_PLAYWRIGHT_MODULE);
let input='';for await(const chunk of process.stdin)input+=chunk;
const config=JSON.parse(input);
const browser=await chromium.launch({headless:true,...(process.env.WHATNOT_BROWSER_EXECUTABLE?{executablePath:process.env.WHATNOT_BROWSER_EXECUTABLE}:{})});
const context=await browser.newContext({viewport:{width:1280,height:900}});
const page=await context.newPage();
const errors=[];page.on('pageerror',error=>errors.push(error.name));
const requests=[];
await context.route('**/*',async route=>{
  const url=new URL(route.request().url());
  if(url.origin===config.ui)return route.continue();
  if(url.origin==='http://127.0.0.1:8000'){
    const path=url.pathname;requests.push({path,method:route.request().method()});
    // Built default API origin is redirected to this run's isolated server.
    // The request method/body/headers and actual FastAPI response are preserved.
    const result=await route.fetch({url:config.api+path});
    return route.fulfill({response:result});
  }
  // Keep this check offline except for the owned local servers.
  return route.abort();
});
const out='docs/phase6/screenshots';await mkdir(out,{recursive:true});
async function sizes(name){
  for(const [label,width,height] of [['desktop',1280,900],['tablet',768,1024],['mobile',390,844]]){
    await page.setViewportSize({width,height});
    await page.evaluate(()=>document.fonts.ready);
    const dimensions=await page.evaluate(()=>({body:document.documentElement.scrollWidth,viewport:innerWidth}));
    assert(dimensions.body<=dimensions.viewport+1,`${name}/${label} overflows horizontally`);
    const primary=page.locator('button.btn-primary:visible').first();
    if(await primary.count()){
      const colors=await primary.evaluate(element=>({text:getComputedStyle(element).color,bg:getComputedStyle(element).backgroundColor}));
      function luminance(color){const values=color.match(/[\d.]+/g).slice(0,3).map(Number).map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);return values[0]*.2126+values[1]*.7152+values[2]*.0722;}
      const a=luminance(colors.text),b=luminance(colors.bg);assert((Math.max(a,b)+.05)/(Math.min(a,b)+.05)>=4.5,`${name}/${label} primary contrast`);
    }
    await page.screenshot({path:`${out}/${name}-${label}.png`,fullPage:true});
  }
  await page.setViewportSize({width:1280,height:900});
}
async function login(email,password){await page.getByLabel('Email address').fill(email);await page.getByLabel('Password',{exact:true}).fill(password);await page.getByRole('button',{name:'Sign in',exact:true}).click();await page.getByRole('button',{name:'Log out',exact:true}).waitFor();}
async function logout(){await page.getByRole('button',{name:'Log out',exact:true}).click();await page.getByRole('heading',{name:'Welcome back',exact:true}).waitFor();assert.equal(await page.evaluate(()=>localStorage.length+sessionStorage.length),0);}
try{
  await page.goto(config.ui+'/register');await sizes('registration');
  await page.getByLabel('Name',{exact:true}).fill('Ravi');await page.getByLabel('Email address').fill('seller.phase6@example.com');await page.getByLabel('Phone',{exact:true}).fill('phase6-seller');await page.getByLabel('Password',{exact:true}).fill(config.password);await page.getByLabel('Account type').selectOption('SELLER');await page.getByRole('button',{name:'Create account',exact:true}).click();await page.getByRole('status').filter({hasText:'Account created'}).waitFor();
  await page.getByRole('link',{name:'Sign in',exact:true}).last().click();await page.getByRole('link',{name:'Continue as seller'}).click();await login('seller.phase6@example.com',config.password);
  await page.getByRole('link',{name:'Create seller profile'}).click();await page.getByLabel('Shop name').fill('Ravi Studio');await page.getByLabel('Phone',{exact:true}).fill('phase6-seller');await page.getByLabel('Latitude').fill('19');await page.getByLabel('Longitude').fill('72');await page.getByRole('button',{name:'Save profile'}).click();await page.getByRole('status').filter({hasText:'Profile saved'}).waitFor();await page.getByRole('heading',{name:'Seller profile',exact:true}).waitFor();await sizes('seller-profile');
  await page.getByRole('link',{name:'Add product',exact:true}).click();await page.getByLabel('Product Name').fill('Ravi Candle');await page.getByLabel('Description',{exact:true}).fill('A handmade local candle.');await page.getByLabel('Price (₹)').fill('250.00');await page.getByLabel('Available Quantity').fill('3');await page.getByRole('button',{name:'Submit for Admin Approval'}).click();await page.getByText('Ravi Candle',{exact:true}).waitFor();await page.getByText('Pending',{exact:true}).waitFor();await sizes('seller-products');
  await logout();await login('admin.phase6@example.com',config.adminPassword);await page.getByText('Ravi Candle',{exact:true}).waitFor();await sizes('admin-pending');await page.getByRole('button',{name:'Approve',exact:true}).click();await page.getByText('Approval queue is clear').waitFor();
  await logout();await login('seller.phase6@example.com',config.password);await page.getByText('Approved',{exact:true}).waitFor();await page.getByRole('button',{name:'Deactivate',exact:true}).click();await page.getByText('Inactive',{exact:true}).waitFor();await logout();
  await page.getByRole('link',{name:'Create account',exact:true}).click();await page.getByLabel('Name',{exact:true}).fill('Buyer');await page.getByLabel('Email address').fill('buyer.phase6@example.com');await page.getByLabel('Phone',{exact:true}).fill('phase6-buyer');await page.getByLabel('Password',{exact:true}).fill(config.password);await page.getByRole('button',{name:'Create account',exact:true}).click();await page.getByRole('status').filter({hasText:'Account created'}).waitFor();await page.getByRole('link',{name:'Sign in',exact:true}).last().click();await page.getByRole('link',{name:'Continue as buyer'}).click();await login('buyer.phase6@example.com',config.password);
  await page.getByRole('link',{name:'Addresses',exact:true}).click();await page.getByRole('button',{name:'Add address',exact:true}).click();for(const [label,value] of [['Label','Home'],['Address line 1','Maker Lane'],['City','Mumbai'],['State','Maharashtra'],['Pincode','400001'],['Latitude','19'],['Longitude','72']])await page.getByLabel(label,{exact:true}).fill(value);await page.getByRole('button',{name:'Save address',exact:true}).click();await page.getByText('Maker Lane',{exact:true}).waitFor();await page.getByRole('button',{name:'Make default',exact:true}).click();await page.getByText('Default address',{exact:true}).waitFor();await sizes('addresses');
  await page.getByRole('link',{name:'Orders',exact:true}).click();await page.getByText('No orders yet',{exact:true}).waitFor();await sizes('buyer-orders');
  await page.getByRole('link',{name:'Sample discovery',exact:true}).click();await sizes('sample-discovery');assert(await page.getByText(/Sample catalogue/).isVisible());
  await page.getByRole('link',{name:'Sample cart',exact:true}).click();await page.getByText('Your local basket is empty').waitFor();
  // A real full reload deliberately loses the memory-only credential.
  await page.reload();await page.getByRole('heading',{name:'Welcome back',exact:true}).waitFor();
  assert(!requests.some(request=>request.path==='/api/v1/products'&&request.method==='GET'));
  assert(!requests.some(request=>request.path==='/api/v1/orders'&&request.method==='POST'));
  assert.equal(errors.length,0,'Browser runtime errors');
  console.log('Live isolated-backend browser smoke passed; 7 screens x 3 viewports, primary-button contrast >= 4.5, no horizontal page overflow, no geographic discovery or checkout requests.');
}finally{await context.close();await browser.close();}
