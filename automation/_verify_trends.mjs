import puppeteer from "puppeteer-core";
const URL = "https://www.opsoai.com/trends/";
async function html(u){ const r=await fetch(u,{cache:"no-store"}); return await r.text(); }
let ok=false;
for (let i=1;i<=35;i++){
  const h=await html(URL+"?cb="+i);
  if (h.includes("assets/js/trends.js")) { console.log(`trends deployed ~${i*20}s`); ok=true; break; }
  await new Promise(r=>setTimeout(r,20000));
}
if(!ok){ console.log("not deployed"); process.exit(1); }
const b=await puppeteer.launch({executablePath:"/usr/bin/google-chrome",headless:"new",args:["--no-sandbox"]});
const p=await b.newPage();
await p.goto(URL+"?f=1",{waitUntil:"networkidle2",timeout:60000});
await new Promise(r=>setTimeout(r,3500));
const info=await p.evaluate(()=>({
  canvasesDrawn: [...document.querySelectorAll('canvas')].filter(c=>c.width>0 && c.getContext('2d')).length,
  total: (document.getElementById('st-total')||{}).textContent,
  orgs: (document.getElementById('st-orgs')||{}).textContent,
  month: (document.getElementById('st-month')||{}).textContent,
}));
console.log("TRENDS:", JSON.stringify(info));
// sidebar check on home
await p.goto("https://www.opsoai.com/?x=1",{waitUntil:"networkidle2",timeout:60000});
const nav=await p.evaluate(()=>document.querySelector('#sidebar')?document.querySelector('#sidebar').innerText:document.body.innerText);
console.log("sidebar has CATEGORIES:", /categories/i.test(nav), "| TOOLS:", /tools/i.test(nav), "| TRENDS:", /trends/i.test(nav), "| UPDATES:", /updates/i.test(nav));
await b.close();
