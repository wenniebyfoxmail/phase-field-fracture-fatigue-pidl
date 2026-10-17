import fs from 'node:fs/promises';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {PresentationFile,FileBlob} from '@oai/artifact-tool';
process.env.RUNTIME_NODE='/Users/wenxiaofang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node';
process.env.RUNTIME_NODE_MODULES='/Users/wenxiaofang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
process.env.RUNTIME_BIN_DIR='/Users/wenxiaofang/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override';
const ROOT='/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/fyr_ppt_evidence_revision_20261017';
const SKILL='/Users/wenxiaofang/.codex/plugins/cache/openai-primary-runtime/presentations/26.1013.11914/skills/presentations';
const PY='/Users/wenxiaofang/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3';
const INPUT='/Users/wenxiaofang/Downloads/Winnie_First_Year_Assessment.pptx';
const p=await PresentationFile.importPptx(await FileBlob.load(INPUT));
const original=[...p.slides.items];
const spec=JSON.parse(await fs.readFile(ROOT+'/build/content.json','utf8'));
const colors={blue:'#174B73',dark:'#1B2730',muted:'#52616B',light:'#F2F6F8'};
let serial=0;
function text(s,value,x,y,w,h,size=28,bold=false,color=colors.dark){
 const a=s.shapes.add({geometry:'textbox',name:'content-'+(++serial),position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 a.text=value;a.text.style={typeface:'Arial',fontSize:size,bold,color,wrap:'word',verticalAlignment:'top',insets:0};return a;
}
function rect(s,x,y,w,h,fill=colors.light){return s.shapes.add({geometry:'rect',name:'process-step-'+(++serial),position:{left:x,top:y,width:w,height:h},fill,line:{fill:colors.blue,width:1.3}});}
function arrow(s,x,y,w=30,left=false){return s.shapes.add({geometry:left?'leftArrow':'rightArrow',name:'process-arrow-'+(++serial),position:{left:x,top:y,width:w,height:18},fill:colors.blue,line:{fill:'none',width:0}});}
async function records(s){const idx=p.slides.items.indexOf(s);return (await p.inspect({kind:'slide,textbox,shape,image,table,chart',maxChars:1600000})).records.filter(x=>x.slideIndex===idx);}
async function duplicate(i){const s=original[i-1].duplicate();s.moveTo(p.slides.items.length-1);return s;}
async function blank(){const s=await duplicate(4);const r=await records(s);p.delete(r.filter(x=>x.position&&!(x.position.top<130&&x.kind==='textbox')&&x.position.top<665).map(x=>x.id));return s;}
async function setHeader(s,d,n){for(const r of await records(s)){
 if(r.kind!=='textbox')continue;let sh=p.resolve(r.id);
 if(r.position.top===17)sh.text=d.kicker||'FIRST-YEAR STUDY';
 if(r.position.top===55)sh.text=d.title;
 if(r.position.top===665)sh.text=String(n).padStart(2,'0');
}}
function table(s,values,x,y,w,h,widths,size=25){
 const t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,columnWidths:widths,values});
 for(let r=0;r<values.length;r++)for(let c=0;c<values[0].length;c++){
  const cell=t.getCell(r,c);cell.fill=r===0?'#EAF1F5':'#FFFFFF';cell.text.style={typeface:'Arial',fontSize:size,color:r===0?colors.blue:colors.dark,bold:r===0,insets:8,verticalAlignment:'middle'};
 }
 t.borders.assign({fill:'#B7C8D3',width:0.6,style:'solid'});return t;
}
function image(s,file,x,y,w,h){s.images.add({blob:new Uint8Array(readFileSync(file)),contentType:'image/png',fit:'contain',alt:path.basename(file,'.png').replaceAll('_',' '),position:{left:x,top:y,width:w,height:h}});}
function label(s,t,y=625){text(s,t,62,y,1125,44,21,false,colors.muted);}
function row(s,head,body,y){text(s,head,62,y,1140,42,29,true,colors.blue);text(s,body,62,y+49,1115,77,28);}
let slides=[];
for(let i=0;i<spec.length;i++){
 const d=spec[i];let s;
 if(d.kind==='cover'){
  s=await duplicate(1);
  for(const r of await records(s))if(r.kind==='textbox'){
   const sh=p.resolve(r.id);
   if(r.text==='Crack-state Prediction')sh.text='Road-crack Prediction';
   if(r.text.startsWith('Controlled fatigue diagnosis')){sh.text='First-year focus:\nA controlled fracture model';sh.text.style={typeface:'Arial',fontSize:40,color:colors.dark};}
   if(r.text.startsWith('Xiaofang Wen')){sh.text='Wennie Wan\nSupervisor: Brian Sheil\nCambridge Engineering';sh.position={left:54,top:474,width:650,height:142};sh.text.style={typeface:'Arial',fontSize:28,color:colors.dark};}
   if(r.text==='Department of Engineering')sh.position={left:411,top:664,width:810,height:38};
  }
 }else if(d.kind==='benchmark'){
  s=await duplicate(3);const r=await records(s);
  p.delete(r.filter(x=>x.kind==='textbox'&&x.position.left>=790&&x.position.top>=130&&x.position.top<620).map(x=>x.id));
  text(s,'Linear-elastic bulk response',790,160,430,42,29,true,colors.blue);
  text(s,'Plane strain · AT1 phase field\nAmor tensile/compressive split',790,214,430,85,27);
  text(s,'Normalised parameters',790,326,430,42,29,true,colors.blue);
  text(s,'E = 1     ν = 0.3\nGc = 0.01     ℓ = 0.01\nFatigue threshold αT = 0.5',790,380,430,125,27);
  const cap=r.find(x=>x.kind==='textbox'&&x.position.top===646);if(cap)p.resolve(cap.id).text='Unit square, left starter crack   ·   Sketch α is damage d in these slides';
 }else if(d.kind==='fatigue'){
  s=await duplicate(8);const r=await records(s);
  p.delete(r.filter(x=>x.kind==='textbox'&&x.position.left>=890&&x.position.top>=130&&x.position.top<630).map(x=>x.id));
  text(s,'Damage affects stiffness',890,160,330,40,28,true,colors.blue);
  text(s,'g(d) = (1 − d)²\nψactive = g(d) ψraw',890,211,330,95,27);
  text(s,'Fatigue affects fracture resistance',890,340,330,80,28,true,colors.blue);
  text(s,'ᾱ accumulates along loading\nf = 1 below αT\nf = [1 / (ᾱ + 0.5)]² above αT',890,430,330,139,25);
  const cap=r.find(x=>x.kind==='textbox'&&x.position.top===646);if(cap)p.resolve(cap.id).text='αT = 0.5 · Fatigue exponent p = 2';
 }else if(d.kind==='backup'){
  s=await duplicate(d.original);
 }else if(d.kind==='observations'){
  s=await duplicate(11);const r=await records(s);
  p.delete(r.filter(x=>x.kind==='textbox'&&x.position.top>=130&&x.position.top<665).map(x=>x.id));
  text(s,'One mask → two masks → load history',62,160,590,84,29,true,colors.blue);
  text(s,'Hold future loading and the\ngrowth target fixed',62,280,560,82,30);
  text(s,'Compare with persistence\nand simple growth extrapolation',62,400,560,98,28);
  label(s,'Conceptual illustration · Proposed synthetic study',646);
 }else{
  s=await blank();
  switch(d.kind){
   case 'prose':
    for(let k=0;k<d.rows.length;k++)row(s,d.rows[k][0],d.rows[k][1],161+155*k);
    if(d.foot)label(s,d.foot,638);
    break;
   case 'native_table':
    table(s,d.values,62,167,1150,365,d.widths,d.fontSize||25);
    if(d.foot)text(s,d.foot,62,571,1150,75,24,false,colors.blue);
    break;
   case 'network':
    text(s,'Spatial coordinates',62,160,1120,42,29,true,colors.blue);
    const netX=[62,455,850],netW=[325,325,360];
    const netText=['Input\n(x, y)','MLP\n8 × 400','Field outputs\nuθ, vθ, dθ'];
    for(let k=0;k<3;k++){rect(s,netX[k],235,netW[k],125);text(s,netText[k],netX[k]+18,260,netW[k]-36,92,29);if(k<2)arrow(s,netX[k]+netW[k]+16,290,34);}
    text(s,'Current load U enters the displacement boundary constraints',62,397,1150,52,28,false,colors.blue);
    text(s,'Objective: elastic + fracture energy + damage penalties\nRPROP updates θ, including trainable ReLU parameters',62,480,1150,98,29);
    label(s,'Seed 1   ·   Maximum 10,000 iterations per substep   ·   E, ν, Gc, ℓ and αT stay fixed',633);
    break;
   case 'stages':
    text(s,'Long-term objective: predict how road cracks develop and grow',62,152,1120,60,29,true,colors.blue);
    row(s,'1  Build and test the numerical model','Controlled phase-field fatigue problem · First-year focus',250);
    row(s,'2  Predict with limited observations','Test what extra observations tell us about future crack growth',381);
    row(s,'3  Adapt to roads and validate','Choose a pavement problem and test against measurements',512);
    label(s,'First-year report: Stage 1 · Stages 2 and 3: future plans',646);
    break;
   case 'phase':
    text(s,'Damage d',62,156,480,48,31,true,colors.blue);
    text(s,'d = 0   intact material\nd = 1   fully damaged material\nℓ controls the diffuse crack width',62,220,520,158,30);
    text(s,'Energy balance',660,156,550,48,31,true,colors.blue);
    text(s,'Elastic energy\n+ fatigue-reduced fracture energy',660,220,550,100,30);
    text(s,'Find displacement u and damage d\nunder the imposed load',660,365,550,110,30);
    text(s,'E(u,d) = Eelastic(u,d) + ∫Ω f(ᾱ) Gc γℓ(d,∇d) dΩ',62,540,1150,55,29,true,colors.blue);
    label(s,'γℓ: diffuse crack density · d represents fracture; f reduces fracture resistance');
    break;
   case 'fem':
    text(s,'Input: current load + previous accepted fields and history',62,150,1150,54,28,true,colors.blue);
    rect(s,62,235,490,128);text(s,'1  Solve displacement u\nKeep damage d fixed',82,258,448,92,29);
    arrow(s,582,287,60);
    rect(s,678,235,535,128);text(s,'2  Solve damage d\nUse trial fatigue in this solve',698,258,490,92,29);
    arrow(s,630,392,170,true);text(s,'Repeat these solves until the stopping test is met',160,425,990,44,27,false,colors.blue);
    rect(s,62,501,315,91);text(s,'3  Accept the fields',79,529,285,40,27);
    arrow(s,394,535,38);rect(s,450,501,390,91);text(s,'4  Commit updated history',467,529,355,40,27);
    arrow(s,854,535,38);rect(s,910,501,303,91);text(s,'5  Next load substep',927,529,270,40,27);
    label(s,'Stored old history stays fixed during iteration; accepted history is committed once');
    break;
   case 'pidl':
    text(s,'Network input: (x, y) · Current load enters the boundary constraints',62,143,1150,50,27,true,colors.blue);
    text(s,'Previous accepted history supplies fixed f during the fit',62,193,1150,34,24,false,colors.muted);
    const xs=[62,460,858];const ws=[345,345,355];const tx=['1  Network fields\nuθ, vθ, dθ','2  Energy objective\n+ damage penalties','3  RPROP update\nθ ← updated weights'];
    for(let k=0;k<3;k++){rect(s,xs[k],235,ws[k],130);text(s,tx[k],xs[k]+18,258,ws[k]-36,96,29);if(k<2)arrow(s,xs[k]+ws[k]+12,291,28);}
    text(s,'Repeat the fit at fixed load and fixed old fatigue factor f',62,396,1150,52,28,false,colors.blue);
    rect(s,62,491,315,103);text(s,'Accept damage',80,527,280,40,28);
    arrow(s,394,534,38);rect(s,450,491,390,103);text(s,'Update fatigue history\nand previous driver; refresh f',468,510,352,78,25);
    arrow(s,854,534,38);rect(s,910,491,303,103);text(s,'Next substep\nReuse θ and history',926,510,270,78,27);
    label(s,'Network: 8 hidden layers × 400 neurons · Material parameters remain fixed');
    break;
   case 'cycle':
    table(s,[['Substep','1','2','3','4 peak','5 unload'],['U','0.02999988','0.05999988','0.08999988','0.11999988','0'],['After solve','Accept + carry','Accept + carry','Accept + carry','Accept + carry','Accept + carry']],62,180,1150,202,[150,200,200,200,200,200],24);
    row(s,'Inner loop: one fixed loading state','FEM: alternate u and d solves     PIDL: update network weights θ',426);
    text(s,'Outer loop: accept state → update history → next substep → next cycle',62,585,1150,54,27,true,colors.blue);
    break;
   case 'compare':
    table(s,[['','Q4','T3'],['FEM','86,408 elements · GP4','172,816 elements · GP3'],['PIDL','Same Q4 support','Same T3 support']],62,180,1150,215,[160,495,495],27);
    text(s,'Shared ordered nodes · Same realised Hard-5 loading sequence',62,433,1150,44,28,true,colors.blue);
    text(s,'Scalars: event cycle and domain mean\nFields: where damage and fatigue values differ',62,505,1150,90,28);
    label(s,'All field comparisons use the same physical peak; fatigue maps use post-update histories');
    break;
   case 'events':
    text(s,'First detection: at least 3 nodes with x > 0.48 and d > 0.95 at a peak',62,150,1150,67,27,true,colors.blue);
    table(s,[['Calculation','First detection','Confirmation'],['FEM-Q4','84','87'],['FEM-T3','84','87'],['PIDL-Q4','85','88'],['PIDL-T3','89','92']],62,246,1150,270,[450,350,350],28);
    text(s,'All four: confirmation label = first detection + 3 physical cycles',62,553,1150,66,28,false,colors.blue);
    label(s,'Common rule applied to 480 saved peaks');
    break;
   case 'figure':
    image(s,d.image,62,142,1150,415);
    text(s,d.message,62,577,1150,48,28,true,colors.blue);label(s,d.small,638);
    break;
   case 'evolution':
    image(s,d.image,62,143,790,493);
    text(s,'Q4 history gap\nincreases',900,190,310,95,29,true,colors.blue);
    text(s,'T3 history gap\nfalls, then rises slightly',900,330,310,120,28);
    text(s,'Factor MAE grows\non both meshes',900,505,310,100,28);
    label(s,'c20 → c60 → c83 · Post-update peaks; lines connect these three samples',646);
    break;
   case 'attempts':
    table(s,[['Question','Existing check','Outcome'],['Local representation?','Crack-tip / Fourier / local heads','Changed fields; no consistent match'],['Discretisation?','Paired Q4 and T3','Different damage and event response'],['Displacement equilibrium?','Hold damage fixed; re-solve u','Most active-field gap remains'],['Final accepted state?','Bounds and final residual checks','Constraints and updates matter']],62,166,1150,386,[285,415,450],25);
    text(s,'c83 active relative L2: Q4 0.476 → 0.463; T3 1.026 → 1.018',62,577,1150,48,27,true,colors.blue);
    label(s,'Existing fixed-damage re-solves: d bounded to [0,1], η = 10⁻⁶ sensitivity',641);
    break;
   case 'summary':
    row(s,'Implementation and comparison','Fatigue PIDL tested against FEM on paired Q4 and T3 meshes',163);
    row(s,'Event timing and local fields','Q4 events are close; damage and fatigue fields still differ',328);
    row(s,'Specific next questions','Initial damage · Current-step fatigue · Damage constraints',493);
    break;
   case 'controls':
    table(s,[['Controlled comparison','Question'],['Start from a common state','How much comes from recovered damage?'],['Match current-step fatigue treatment','How do local increments and f change?'],['Enforce damage constraints; check final residuals','Are the final fields numerically consistent?']],62,175,1150,328,[550,600],26);
    text(s,'Evaluate complete trajectories, event timing and local-field differences',62,557,1150,75,29,true,colors.blue);
    break;
   case 'roads':
    row(s,'Define the pavement problem','Select the material, loading conditions and crack-growth target',163);
    row(s,'Choose and calibrate the mechanics','Use a material model suited to that problem and relevant data',328);
    row(s,'Test on separate measurements','Assess future crack evolution beyond the calibration data',493);
    break;
   case 'thanks':
    text(s,'Questions and discussion',62,272,1140,84,42);
    text(s,'Wennie Wan · Supervisor: Brian Sheil',62,460,1140,70,30,false,colors.muted);
    text(s,'Supporting results follow in the backup slides',62,581,1140,46,25,false,colors.muted);
    break;
   default:throw new Error(d.kind);
  }
 }
 await setHeader(s,d,i+1);
 const en=typeof d.en==='string'?d.en:String(d.en);
 s.speakerNotes.text='English narration\n'+en+'\n\n中文对照\n'+d.zh+'\n\nSources\n'+d.source;
 slides.push(s);
}
p.delete(original.map(s=>'sl/'+s.id));
for(let i=0;i<slides.length;i++)slides[i].moveTo(i);
await fs.writeFile(ROOT+'/build/content_final.json',JSON.stringify(spec,null,2));
await fs.mkdir(ROOT+'/review/final_slides',{recursive:true});
for(let i=0;i<slides.length;i++){
 const png=await p.export({slide:slides[i],format:'png',scale:1});
 await fs.writeFile(ROOT+'/review/final_slides/'+String(i+1).padStart(2,'0')+'.png',new Uint8Array(await png.arrayBuffer()));
}
await fs.writeFile(ROOT+'/review/final_inspect.json',JSON.stringify(await p.inspect({kind:'slide,textbox,shape,image,table,notes,layout',maxChars:1600000}),null,2));
const candidate=ROOT+'/build/candidate.pptx';await (await PresentationFile.exportPptx(p)).save(candidate);
const {finalizePresentation}=await import(pathToFileURL(SKILL+'/container_tools/artifact_tool_utils.mjs').href);
const tableOwners=spec.map((d,i)=>['native_table','cycle','compare','events','attempts','controls'].includes(d.kind)?i+1:null).filter(Boolean);
const result=await finalizePresentation({workspaceDir:ROOT,candidatePath:candidate,finalPath:ROOT+'/output/Wennie_Wan_First_Year_Assessment_Evidence_v6.pptx',pythonExecutable:PY,integrityValidatorPath:SKILL+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:SKILL+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit',...tableOwners.flatMap(n=>['--require-native-table-slide',String(n)])],explicitTotalSlideCount:spec.length,requiredNativeTableOwnerSlides:tableOwners,requiredNativeChartOwnerSlides:[],fontPolicy:{basis:'reference',families:['Arial'],referencePath:INPUT,referenceSha256:createHash('sha256').update(readFileSync(INPUT)).digest('hex')},verifyArtifactToolImport:true,receiptPath:ROOT+'/review/finalization_v6.json'});
console.log('Finalized',slides.length,'slides',JSON.stringify(result).slice(0,1200));
