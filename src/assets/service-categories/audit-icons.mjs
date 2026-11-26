// Dependency-free deterministic PNG audit compositor. Does not edit deliveries.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { inflateSync, deflateSync } from 'node:zlib';
const root = path.dirname(fileURLToPath(import.meta.url));
const names = ['photography','videography','video-editing','graphic-design','animation-and-vfx','fashion-design','logo-and-branding-design','advertisement-production','promotional-video-production','digital-marketing','travel-video-editing','influencer-reel-editing','vfx','website-development','mobile-application-development','custom-software-development','portfolio-development','e-commerce-development','crm-and-erp-solutions','ai-and-automation','cloud-and-devops','software-maintenance','it-consulting','cybersecurity-services','api-development-and-integration'];
const paeth = (a,b,c) => {const p=a+b-c, x=Math.abs(p-a), y=Math.abs(p-b), z=Math.abs(p-c); return x<=y&&x<=z?a:y<=z?b:c;};
function decode(file) {
  const data=fs.readFileSync(file), width=data.readUInt32BE(16), height=data.readUInt32BE(20);
  if(data[24]!==8||data[25]!==6||data[28]!==0) throw Error('Expected non-interlaced RGBA8 PNG: '+file);
  const parts=[];
  for(let offset=8;offset<data.length;){const length=data.readUInt32BE(offset), type=data.toString('ascii',offset+4,offset+8);if(type==='IDAT')parts.push(data.subarray(offset+8,offset+8+length));offset+=length+12;}
  const raw=inflateSync(Buffer.concat(parts)), stride=width*4, pixels=Buffer.alloc(stride*height);
  for(let y=0;y<height;y++){const filter=raw[y*(stride+1)];for(let x=0;x<stride;x++){const index=y*stride+x, left=x>=4?pixels[index-4]:0, above=y?pixels[index-stride]:0, diagonal=y&&x>=4?pixels[index-stride-4]:0;const predictor=[0,left,above,Math.floor((left+above)/2),paeth(left,above,diagonal)][filter];if(predictor===undefined)throw Error('PNG filter');pixels[index]=(raw[y*(stride+1)+x+1]+predictor)&255;}}
  return {width,height,pixels,bytes:data.length};
}
function crc32(data){let crc=0xffffffff;for(const byte of data){crc^=byte;for(let bit=0;bit<8;bit++)crc=(crc>>>1)^((crc&1)?0xedb88320:0);}return (crc^0xffffffff)>>>0;}
function chunk(type,payload){const name=Buffer.from(type), size=Buffer.alloc(4), crc=Buffer.alloc(4);size.writeUInt32BE(payload.length);crc.writeUInt32BE(crc32(Buffer.concat([name,payload])));return Buffer.concat([size,name,payload,crc]);}
function encode(width,height,pixels){const header=Buffer.alloc(13);header.writeUInt32BE(width);header.writeUInt32BE(height,4);header[8]=8;header[9]=6;const scanlines=Buffer.alloc(height*(width*4+1));for(let y=0;y<height;y++)pixels.copy(scanlines,y*(width*4+1)+1,y*width*4,(y+1)*width*4);return Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]),chunk('IHDR',header),chunk('IDAT',deflateSync(scanlines)),chunk('IEND',Buffer.alloc(0))]);}
const images=names.map(name=>decode(path.join(root,name+'-256.png')));
for(const size of [128,64]){
  const pixels=Buffer.alloc(640*640*4,255);
  images.forEach((image,index)=>{const left=index%5*128+(128-size)/2, top=Math.floor(index/5)*128+(128-size)/2;for(let y=0;y<size;y++)for(let x=0;x<size;x++){const input=(Math.floor((y+.5)*image.height/size)*image.width+Math.floor((x+.5)*image.width/size))*4, output=((top+y)*640+left+x)*4, alpha=image.pixels[input+3]/255;for(let color=0;color<3;color++)pixels[output+color]=Math.round(image.pixels[input+color]*alpha+255*(1-alpha));}});
  fs.writeFileSync(path.join(root,'originals',`audit-white-${size}.png`),encode(640,640,pixels));
}
console.log(JSON.stringify({count:images.length,totalBytes:images.reduce((sum,image)=>sum+image.bytes,0),all256:images.every(image=>image.width===256&&image.height===256),allTransparentCorners:images.every(image=>image.pixels[3]===0),audits:[128,64]}));
