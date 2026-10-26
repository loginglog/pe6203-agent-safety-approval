// Print-sized scientific figures from the frozen analysis, with no model calls.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath, pathToFileURL} from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(path.join(root, 'results/raw/analysis_build_20261019/context.cjs'));
const sharp = (await import(pathToFileURL(require.resolve('sharp')).href)).default;
const data = JSON.parse(await fs.readFile(path.join(root, 'results/analysis_20261019/analysis.json'), 'utf8'));
const out = path.join(root, 'report/figures');
await fs.mkdir(out, {recursive:true});
const strategies = ['full-approve', 'full-escalate', 'candidate'];
const names = ['FullApprove', 'FullEscalate', 'Candidate v0.4.0'];
const colors = ['#2864B4', '#C77525', '#087F72'];
const escape = s => String(s).replaceAll('&','&amp;').replaceAll('<','&lt;');
const text = (x,y,s,size=14,color='#24364D',anchor='start',weight='normal') => `<text x="${x}" y="${y}" font-size="${size}" fill="${color}" text-anchor="${anchor}" font-weight="${weight}">${escape(s)}</text>`;
const line = (x1,y1,x2,y2,c='#DDE4EB',w=1,d='') => `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${c}" stroke-width="${w}" ${d?`stroke-dasharray="${d}"`:''}/>`;
const rect = (x,y,w,h,c) => `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${c}"/>`;
async function save(name,body,height){
  const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="720" height="${height}" viewBox="0 0 720 ${height}"><rect width="100%" height="100%" fill="white"/><g font-family="Arial,Helvetica,sans-serif">${body}</g></svg>`;
  await fs.writeFile(path.join(out,name+'.svg'),svg);
  await sharp(Buffer.from(svg)).resize(2160,height*3).png().toFile(path.join(out,name+'.png'));
}
const legend = () => names.map((n,i)=>line(60+i*222,60,83+i*222,60,colors[i],3)+text(91+i*222,65,n,14)).join('');
let body=text(50,27,'Normal tasks excluding development used task28',17,'#14263D','start','bold')+legend();
const x=[100,360,620], y0=300, ph=205;
for(let p=0;p<=100;p+=20)body+=line(65,y0-p/100*ph,660,y0-p/100*ph)+text(55,y0-p/100*ph+5,p+'%',13,'#41546B','end');
for(let i=0;i<3;i++)body+=text(x[i],325,String(i),14,'#24364D','middle');
body+=text(360,355,'Review budget k',14,'#24364D','middle');
for(let i=0;i<3;i++){
  const rows=data.metrics.filter(g=>g.scope==='excluding_development_task28'&&g.strategy===strategies[i]);
  const pts=rows.map(g=>[x[g.k],y0-g.exploratory_tcr_lower*ph]);
  body+=`<polyline points="${pts.map(p=>p.join(',')).join(' ')}" stroke="${colors[i]}" stroke-width="3" fill="none"/>`;
  rows.forEach((g,j)=>{
    const [px,py]=pts[j]; body+=`<circle cx="${px}" cy="${py}" r="5" fill="${colors[i]}" stroke="white" stroke-width="1.5"/>`;
    if(g.native_unknown){const top=y0-g.unknown_completion_upper*ph; body+=line(px,top,px,py,colors[i],2,'5 4')+line(px-7,top,px+7,top,colors[i],2)+text(px-10,top-10,'1 unknown',13,colors[i],'end');}
  });
}
await save('tcr_task28_excluded',body,375);

body=text(50,27,'Review load across all six exploratory tasks',17,'#14263D','start','bold')+legend();
const yb=280,bh=180,centers=[170,375,580];
for(let n=0;n<=10;n+=2)body+=line(65,yb-n/10*bh,675,yb-n/10*bh)+text(55,yb-n/10*bh+5,String(n),13,'#41546B','end');
for(let k=0;k<3;k++){
  for(let i=0;i<3;i++){
    const g=data.metrics.find(g=>g.scope==='all_six_exploratory'&&g.strategy===strategies[i]&&g.k===k);
    const px=centers[k]+(i-1)*51-18;
    body+=rect(px,yb-g.hitl_all/10*bh,36,g.hitl_all/10*bh,colors[i])+text(px+18,yb-g.hitl_all/10*bh-7,g.hitl_all,13,colors[i],'middle','bold');
    body+=text(px+18,303,g.hitl_native_successful,13,colors[i],'middle');
  }
  body+=text(centers[k],333,'k = '+k,14,'#24364D','middle','bold');
}
body+=text(65,360,'Bars: all reviews. Lower numbers: reviews on native successful tasks.',13);
await save('hitl_all_tasks',body,380);

body=text(50,27,'Known component credits across all six tasks and all k',17,'#14263D','start','bold');
body+=rect(90,47,16,16,'#526E91')+text(114,61,'Agent',14)+rect(265,47,16,16,'#087F72')+text(289,61,'Reviewer',14);
const base=280,hh=180,max=.018;
for(let v=0;v<=.01801;v+=.006)body+=line(80,base-v/max*hh,680,base-v/max*hh)+text(70,base-v/max*hh+5,'$'+v.toFixed(3),13,'#41546B','end');
for(let i=0;i<3;i++){
  const groups=data.component_costs.filter(g=>g.scope==='all_six_exploratory'&&g.strategy===strategies[i]);
  let stacked=0; const px=[180,380,580][i];
  ['agent','reviewer'].forEach((c,j)=>{const v=Number(groups.find(g=>g.component===c).known_reported_usd_credits_subtotal);body+=rect(px-40,base-(stacked+v)/max*hh,80,v/max*hh,['#526E91','#087F72'][j]);stacked+=v;});
  body+=text(px,base-stacked/max*hh-10,'$'+stacked.toFixed(6)+(i===1?'*':''),14,'#24364D','middle','bold')+text(px,310,names[i],14,'#24364D','middle');
}
body+=text(80,343,'* Excludes an unresolved timeout charge. Policy API credits are zero.',13);
await save('component_costs',body,365);
console.log('Created three print-sized report figures from existing analysis. Zero model requests.');
