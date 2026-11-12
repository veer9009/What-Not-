// Targeted sRGB contrast verification against the actual stylesheet. Not a WCAG certification.
import {readFileSync} from 'node:fs';
const css=readFileSync(new URL('../src/styles/index.css',import.meta.url),'utf8');
const token=name=>{const match=css.match(new RegExp(`--color-${name}:(#[0-9a-f]{6})`,'i'));if(!match)throw new Error(`Missing token ${name}`);return match[1];};
function luminance(hex){return hex.slice(1).match(/../g).map(h=>parseInt(h,16)/255).map(c=>c<=.04045?c/12.92:((c+.055)/1.055)**2.4).reduce((n,c,i)=>n+c*[.2126,.7152,.0722][i],0);}
function ratio(fg,bg){const values=[luminance(fg),luminance(bg)].sort((a,b)=>b-a);return (values[0]+.05)/(values[1]+.05);}
const whatsapp=css.match(/\.whatsapp a\{background:(#[0-9a-f]{6})\}/i)?.[1];
const footer=css.match(/\.legal-footer p,footer small\{color:(#[0-9a-f]{6})\}/i)?.[1];
const controlBorder=css.match(/--color-control-border:(#[0-9a-f]{6})/i)?.[1]??token('border');
if(!whatsapp||!footer)throw new Error('Missing reviewed control/footer styles');
const pairs=[
 ['body',token('text'),token('background'),4.5],['muted on white',token('text-muted'),'#ffffff',4.5],
 ['muted on cream',token('text-muted'),token('background'),4.5],['orange button','#ffffff',token('primary'),4.5],
 ['orange link',token('primary'),token('background'),4.5],['notice',token('text'),token('primary-soft'),4.5],
 ['success',token('success'),'#e2eee4',4.5],['warning',token('warning'),'#fff0c7',4.5],
 ['error',token('error'),'#fff0ee',4.5],['footer small',footer,'#18231e',4.5],
 ['WhatsApp icon','#ffffff',whatsapp,3],['focus on white',token('primary'),'#ffffff',3],
 ['focus on soft',token('primary'),token('primary-soft'),3],['footer focus','#ffba80','#18231e',3],
 ['control border on white',controlBorder,'#ffffff',3],['control border on cream',controlBorder,token('background'),3],
];
const checks=pairs.map(([name,fg,bg,target])=>({name,fg,bg,target,ratio:Number(ratio(fg,bg).toFixed(2)),pass:ratio(fg,bg)>=target}));
console.log(JSON.stringify({checks,priorFindings:[
 {name:'old footer small',ratio:Number(ratio('#718079','#18231e').toFixed(2)),target:4.5},
 {name:'old WhatsApp icon',ratio:Number(ratio('#ffffff','#25d366').toFixed(2)),target:3},
]},null,2));
if(checks.some(check=>!check.pass))process.exitCode=1;
