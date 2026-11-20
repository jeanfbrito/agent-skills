#!/usr/bin/env node
// Optional smoke test. Use an existing Playwright installation and Chromium browser.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
async function save(page, selector, target) {
  const [d] = await Promise.all([page.waitForEvent('download'), page.locator(selector).click()]);
  await d.saveAs(target); assert.equal(await d.failure(), null); return fs.readFile(target);
}
async function prepare(page) {
  await page.locator('#prepare').click(); await page.locator('#result').waitFor({state:'visible'});
}
async function smoke(page, dir) {
  const by = id => page.locator('#'+id), href = () => by('live').getAttribute('href');
  await page.goto(pathToFileURL(path.join(__dirname,'reference.html')).href);
  assert.equal(await by('prepare').isDisabled(),true);
  for (const url of ['javascript:void(0)','https://www.google.com.example.org/maps/','https://example.org@www.google.com/maps/']) {
    await by('maps').fill(url); assert.equal(await href(),null); assert.equal(await by('saveView').isDisabled(),true);
  }
  const short='https://maps.app.goo.gl/example'; await by('maps').fill(short); assert.equal(await href(),short);
  const url='https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=0%2C0&heading=72&pitch=-8&fov=76';
  await by('maps').fill(url); assert.match(await by('viewInfo').textContent(),/heading = 72.*pitch = -8.*fov = 76/);
  const shortcut=await save(page,'#saveView',path.join(dir,'test.url'));
  assert.equal(shortcut.toString(),'[InternetShortcut]\r\nURL='+url+'\r\n');
  await by('maps').fill(''); await by('bookmark').setInputFiles(path.join(dir,'test.url'));
  await page.waitForFunction(value=>document.querySelector('#live').getAttribute('href')===value,url);
  const encoded=await page.evaluate(()=>{const c=document.createElement('canvas');c.width=360;c.height=180;const k=c.getContext('2d'),a=k.createImageData(360,180);
    for(let y=0;y<180;y++)for(let x=0;x<360;x++){const i=4*(y*360+x);a.data.set([Math.round(255*x/359),Math.round(255*y/179),90,255],i)}k.putImageData(a,0,0);return c.toDataURL().split(',')[1]});
  await by('file').setInputFiles({name:'calibration.png',mimeType:'image/png',buffer:Buffer.from(encoded,'base64')});
  await by('pano').check(); await by('yaw').fill('90'); await by('pitch').fill('45'); await by('fov').fill('90'); await prepare(page);
  const pix=await page.evaluate(()=>Array.from(document.querySelector('#preview').getContext('2d').getImageData(480,270,1,1).data));
  assert.ok(Math.abs(pix[0]-191)<=2 && Math.abs(pix[1]-64)<=2 && pix[2]===90, `Incorrect camera center: ${pix}`);
  const png=await save(page,'#png',path.join(dir,'perspective.png'));
  assert.equal(png.readUInt32BE(16),960); assert.equal(png.readUInt32BE(20),540);
  const record=JSON.parse(await save(page,'#record',path.join(dir,'perspective.json')));
  assert.equal(record.camera.yaw,90); assert.equal(record.camera.pitch,45); assert.equal(record.camera.horizontalFov,90); assert.equal(record.comparisonView,url);
  await by('yaw').fill('181'); await by('prepare').click(); assert.equal(await by('png').getAttribute('href'),null);
  await by('yaw').fill('90'); await prepare(page); assert.deepEqual(await save(page,'#png',path.join(dir,'repeat.png')),png);
  await by('file').setInputFiles({name:'not-media.txt',mimeType:'text/plain',buffer:Buffer.from('text')});
  assert.equal(await by('prepare').isDisabled(),true); assert.equal(await by('record').getAttribute('href'),null);
}
module.exports={smoke,save,prepare};
if(require.main===module){(async()=>{const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
  const b=await chromium.launch({executablePath:process.env.CHROME_BIN||undefined}); const d=await fs.mkdtemp(path.join(os.tmpdir(),'view-frame-check-'));
  try{await smoke(await b.newPage({acceptDownloads:true}),d);console.log('PASS: links, bookmarks, local 360 projection, repeatability, and invalid inputs.')}finally{await b.close();await fs.rm(d,{recursive:true,force:true})}
})().catch(e=>{console.error(e);process.exitCode=1})}
