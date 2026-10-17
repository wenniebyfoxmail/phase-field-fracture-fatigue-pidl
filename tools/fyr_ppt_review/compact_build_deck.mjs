import fs from 'node:fs/promises';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {PresentationFile,FileBlob} from '@oai/artifact-tool';
process.env.RUNTIME_NODE='/Users/wenxiaofang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node';
process.env.RUNTIME_NODE_MODULES='/Users/wenxiaofang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
process.env.RUNTIME_BIN_DIR='/Users/wenxiaofang/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override';
const ROOT='/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/fyr_ppt_15slide_revision_20261017';
const INPUT='/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/fyr_ppt_evidence_revision_20261017/output/Wennie_Wan_First_Year_Assessment_Evidence_v6.pptx';
const SKILL='/Users/wenxiaofang/.codex/plugins/cache/openai-primary-runtime/presentations/26.1013.11914/skills/presentations';
const PY='/Users/wenxiaofang/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3';
const p=await PresentationFile.importPptx(await FileBlob.load(INPUT));
const old=[...p.slides.items];
const spec=JSON.parse(await fs.readFile(ROOT+'/build/content.json','utf8'));
const C={blue:'#174B73',dark:'#1B2730',muted:'#52616B',light:'#F2F6F8'};
let seq=0;
function text(s,v,x,y,w,h,size=28,bold=false,color=C.dark){
 const a=s.shapes.add({geometry:'textbox',name:'talk-text-'+(++seq),position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 a.text=v;a.text.style={typeface:'Arial',fontSize:size,bold,color,wrap:'word',verticalAlignment:'top',insets:0};return a;
}
function image(s,file,x,y,w,h){s.images.add({blob:new Uint8Array(readFileSync(file)),contentType:'image/png',fit:'contain',alt:file.split('/').pop(),position:{left:x,top:y,width:w,height:h}});}
function table(s,v,x,y,w,h,widths,size=24){
 const t=s.tables.add({rows:v.length,columns:v[0].length,left:x,top:y,width:w,height:h,columnWidths:widths,values:v});
 for(let r=0;r<v.length;r++)for(let c=0;c<v[0].length;c++){const a=t.getCell(r,c);a.fill=r===0?'#EAF1F5':'#FFFFFF';a.text.style={typeface:'Arial',fontSize:size,bold:r===0,color:r===0?C.blue:C.dark,insets:8,verticalAlignment:'middle'};}
 t.borders.assign({fill:'#B7C8D3',width:.6,style:'solid'});return t;
}
const foot=(s,v)=>text(s,v,62,629,1150,49,20,false,C.muted);
async function records(s){const i=p.slides.items.indexOf(s);return (await p.inspect({kind:'slide,textbox,shape,image,table',maxChars:1800000})).records.filter(r=>r.slideIndex===i);}
async function clone(n){const s=old[n-1].duplicate();s.moveTo(p.slides.items.length-1);s.hidden=false;return s;}
async function blank(){const s=await clone(6);p.delete((await records(s)).filter(r=>r.position&&r.position.top<665&&!(r.kind==='textbox'&&r.position.top<130)).map(r=>r.id));return s;}
async function header(s,title,kicker,n){for(const r of await records(s)){if(r.kind!=='textbox')continue;const a=p.resolve(r.id);if(r.position.top===17)a.text=kicker;if(r.position.top===55)a.text=title;if(r.position.top===665)a.text=String(n).padStart(2,'0');}}
function para(s,head,body,y,h=72){text(s,head,62,y,1150,40,29,true,C.blue);text(s,body,62,y+48,1150,h,28);}
let main=[];
for(let i=0;i<15;i++){
 const d=spec[i];let s;
 if(d.kind==='cover')s=await clone(1);
 else if(d.kind==='fem'||d.kind==='pidl'){
  s=await clone(d.kind==='fem'?9:10);
  for(const r of await records(s))if(r.kind==='textbox'){
   const a=p.resolve(r.id);
   if(r.position.top===625){a.text=d.kind==='fem'?'Carry accepted u, v, d, maximum raw-energy history, ᾱ, previous driver and f.':'Carry θ, accepted d, ᾱ, previous active driver and f into the next load substep.';a.text.style={typeface:'Arial',fontSize:20,color:C.muted};}
   if(d.kind==='pidl'&&r.position.top===193){a.text='8 hidden layers × 400 neurons. Trainable ReLU. Fixed material parameters.';a.text.style={typeface:'Arial',fontSize:24,color:C.muted};}
  }
  if(d.kind==='fem')text(s,'Stored old history stays fixed during iteration; trial fatigue enters the damage solve.',62,600,1150,24,19,false,C.muted);
 }else if(d.kind==='model'){
  s=await clone(4);const rr=await records(s);
  p.delete(rr.filter(r=>r.position&&r.position.top<665&&!(r.kind==='textbox'&&r.position.top<130)&&!(r.kind==='image'&&r.position.top===130)).map(r=>r.id));
  const r=(await records(s)).find(r=>r.kind==='image'&&r.position.top===130);p.resolve(r.id).position={left:62,top:146,width:405,height:400};
  text(s,'Linear elastic bulk, plane strain',520,150,695,43,29,true,C.blue);
  text(s,'E = 1, ν = 0.3, Gc = 0.01\nℓ = 0.01, fatigue threshold αT = 0.5',520,203,695,80,26);
  text(s,'Damage d changes stiffness',520,300,695,42,29,true,C.blue);
  text(s,'g(d) = (1 − d)², d = 0 intact, d = 1 damaged\nσ = ∂[g(d) ψ⁺ + ψ⁻] / ∂ε',520,350,695,82,25);
  text(s,'Fatigue lowers fracture resistance',520,453,695,42,29,true,C.blue);
  text(s,'History ᾱ accumulates positive driver increments\nf = 1 below αT, then f = [1 / (ᾱ + 0.5)]²',520,503,695,80,25);
  text(s,'E = ∫Ω [g(d) ψ⁺ + ψ⁻ + f(ᾱ) Gc γℓ(d,∇d)] dΩ',62,583,1150,44,27,true,C.blue);
  foot(s,'AT1, Amor split, normalised parameters. Sketch α is damage d here; γℓ is diffuse crack density.');
 }else{
  s=await blank();
  switch(d.kind){
   case 'question':
    text(s,'Can PIDL reproduce FEM fields and fatigue history?',62,154,1150,61,32,true,C.blue);
    text(s,'Inspection gives visible shape. Prediction also needs loading history and a damage model.',62,232,1150,76,28);
    table(s,[['PhD stage','Question','Status'],['1  Controlled numerical model','Do the fields and history agree?','First-year focus'],['2  Limited observations','What information helps future prediction?','Future work'],['3  Road adaptation','Does it predict measured crack growth?','Future work']],62,337,1150,257,[345,555,250],25);
    foot(s,'The first-year study tests the forward fracture calculation before adding observations.');break;
   case 'comparison':
    text(s,'Shared nodes and five load substeps: 0.03, 0.06, 0.09, 0.12, 0',62,154,1150,60,28,true,C.blue);
    table(s,[['Mesh','Initial damage relative L2','FEM first event','PIDL first event'],['Q4, GP4','8.04%','84','85'],['T3, GP3','7.47%','84','89']],62,245,1150,207,[240,400,255,255],26);
    text(s,'Fatigue starts at ᾱ = 0 and f = 1. Recovered damage already differs.',62,490,1150,73,28);
    text(s,'Field comparisons use the same peak and matching native spatial support.',62,566,1150,52,27,true,C.blue);
    foot(s,'Event: ≥3 nodes with x > 0.48, d > 0.95 at peak. Actual peak U = 0.11999988; load display rounded.');break;
   case 'damage':
    image(s,d.image,62,142,1150,324);
    table(s,[['Mesh','Band width, x = 0.25','Front x, y = 0','Difference'],['Q4','0.01316 / 0.01548','0.4745 / 0.4708','Wider wake, close front'],['T3','0.01180 / 0.01772','0.4636 / 0.4322','Wider wake, front behind']],62,479,1150,133,[100,340,300,410],22);
    foot(s,'c83 peak. Values: FEM / PIDL. d ≥ 0.5 diagnostic, dimensionless. Band width is not crack opening.');break;
   case 'history':
    image(s,d.image,62,153,815,421);
    text(s,'Maximum ᾱ\nFEM / PIDL',917,173,295,95,28,true,C.blue);
    text(s,'Q4\n21.44 / 17.03',917,301,295,100,29);
    text(s,'T3\n22.28 / 26.77',917,446,295,100,29);
    text(s,'The sign of the history difference depends on topology and location',62,578,1150,44,28,true,C.blue);
    foot(s,'c83 after update. Curves: GP-weighted means in |yGP| ≤ 0.01, x-bin width 0.01. Maxima use all GPs.');break;
   case 'evolution':
    image(s,d.image,62,158,1150,322);
    text(s,'c1 damage gap: Q4 10.22%, T3 10.43%. Initial damage already differs.',62,505,1150,60,27);
    text(s,'Q4 history gap grows. T3 changes trend. Factor MAE grows on both.',62,576,1150,45,28,true,C.blue);
    foot(s,'Post-update peaks c20, c60, c83. Dashed lines: |yGP| ≤ 0.03. Lines connect only three saved states.');break;
   case 'energy':
    image(s,d.image,62,155,805,448);
    text(s,'Active driver\n= g(d) × ψraw',918,166,290,98,29,true,C.blue);
    text(s,'Integral gap\n+5.81%',918,298,290,98,31);
    text(s,'Field relative L2\n0.476',918,424,290,98,29);
    text(s,'Local overlap matters',918,559,290,62,26,true,C.blue);
    foot(s,'Q4 c83 diagnostic before PIDL history refresh. The product is evaluated at GPs before averaging.');break;
   case 'attempts':
    table(s,[['Existing check','Reason','Outcome'],['Richer local representations','Resolve local fields','Fields change; no consistent match'],['Hold d fixed, re-solve u','Check displacement contribution','Most active-field gap remains'],['Inspect damage bounds','Check the accepted fields','Small d < 0 and d > 1 values']],62,174,1150,312,[355,355,440],25);
    text(s,'Active relative L2: Q4 0.476 → 0.463; T3 1.026 → 1.018',62,527,1150,51,29,true,C.blue);
    text(s,'The coupled damage and history updates remain the next focus',62,591,1150,42,26);
    foot(s,'Fixed-damage re-solves use d bounded to [0,1], η = 10⁻⁶ sensitivity. They do not re-run the trajectory.');break;
   case 'conclusion':
    text(s,'Close event timing does not establish local-field agreement',62,156,1150,92,35,true,C.blue);
    para(s,'Completed work','A fatigue PIDL implementation and a paired FEM comparison on Q4 and T3',295,66);
    para(s,'What the comparison shows','Different initial damage, local shape and history; most gap remains after re-solving u',435,76);
    text(s,'Next question: separate initial state, current-step fatigue and damage constraints',62,583,1150,68,28,true,C.blue);break;
   case 'controls':
    text(s,'Keep material, mesh and loading fixed. Change one part at a time.',62,157,1150,61,29,true,C.blue);
    table(s,[['Controlled change','Question to test'],['Common recovered damage and histories','How much later mismatch comes from the start?'],['Match current-step fatigue treatment','How do history increments and f change?'],['Damage constraints and final residuals','Are the accepted fields numerically consistent?']],62,259,1150,280,[570,580],26);
    text(s,'Track the complete trajectory, event timing and local-field differences',62,579,1150,66,29,true,C.blue);break;
   case 'observations':
    table(s,[['Allowed observation at prediction time','What it adds'],['Current crack mask','Visible current shape'],['Current + earlier mask','Observed recent change'],['Masks + past loading','Part of the driving history']],62,164,1150,272,[630,520],27);
    text(s,'Same future loading and target. Compare with persistence and simple extrapolation.',62,468,1150,78,28,true,C.blue);
    text(s,'Evaluate complete held-out trajectories. Check mean error, interval coverage and width near cracks.',62,563,1150,79,27);
    foot(s,'Proposed prediction study. The archived supervised UQ summaries remain in the backups.');break;
   case 'roads':
    para(s,'One pavement problem','Choose material, temperature, loading and the crack-growth target',159,65);
    para(s,'Suitable mechanics and calibration','Choose the material model using relevant fracture and fatigue tests',315,67);
    para(s,'Independent measurement validation','Compare future crack evolution with separate crack and loading measurements',472,75);
    foot(s,'First-year findings lead to numerical controls, observation tests, then measured road prediction.');break;
   default:throw new Error(d.kind);
  }
 }
 await header(s,d.title,i===0?'FIRST-YEAR PHD ASSESSMENT':i<2?'RESEARCH QUESTION':i<6?'MODEL AND COMPUTATION':i<11?'RESULTS AND EXPLANATION':i===11?'CONCLUSIONS':'FUTURE WORK',i+1);
 s.speakerNotes.text='English narration\n'+d.en+'\n\n中文对照\n'+d.zh+'\n\nSources\n'+d.source;
 main.push(s);
}
const backups=[];
for(let j=15;j<spec.length;j++){
 const d=spec[j],s=old[d.backup_original_slide-1];s.hidden=true;
 const num=(await records(s)).find(r=>r.kind==='textbox'&&r.position.top===665);
 if(num){const a=p.resolve(num.id);a.text=d.backup_label;a.position={left:1164,top:665,width:84,height:27};a.text.style={typeface:'Arial',fontSize:18,color:C.muted};}
 else text(s,d.backup_label,1180,665,70,30,18,false,'#FFFFFF');
 backups.push(s);
}
const all=[...main,...backups];for(let i=0;i<all.length;i++)all[i].moveTo(i);
await fs.writeFile(ROOT+'/build/content_final.json',JSON.stringify(spec,null,2));
await fs.mkdir(ROOT+'/review/final_slides',{recursive:true});
for(let i=0;i<all.length;i++){const b=await p.export({slide:all[i],format:'png',scale:1});await fs.writeFile(ROOT+'/review/final_slides/'+String(i+1).padStart(2,'0')+'.png',new Uint8Array(await b.arrayBuffer()));}
await fs.writeFile(ROOT+'/review/final_inspect.json',JSON.stringify(await p.inspect({kind:'slide,textbox,image,shape,table,notes,layout',maxChars:1800000}),null,2));
const candidate=ROOT+'/build/candidate.pptx';await(await PresentationFile.exportPptx(p)).save(candidate);
const oldTables=[3,12,13,14,16,19,26,29,33,40,46];
const tableOwners=[2,6,7,11,13,14,...spec.slice(15).flatMap((d,j)=>oldTables.includes(d.backup_original_slide)?[j+16]:[])];
const {finalizePresentation}=await import(pathToFileURL(SKILL+'/container_tools/artifact_tool_utils.mjs').href);
const result=await finalizePresentation({workspaceDir:ROOT,candidatePath:candidate,finalPath:ROOT+'/output/Wennie_Wan_First_Year_Assessment_15_Main_v3.pptx',pythonExecutable:PY,integrityValidatorPath:SKILL+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:SKILL+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit',...tableOwners.flatMap(n=>['--require-native-table-slide',String(n)])],explicitTotalSlideCount:61,requiredNativeTableOwnerSlides:tableOwners,requiredNativeChartOwnerSlides:[],fontPolicy:{basis:'reference',families:['Arial'],referencePath:INPUT,referenceSha256:createHash('sha256').update(readFileSync(INPUT)).digest('hex')},verifyArtifactToolImport:true,receiptPath:ROOT+'/review/finalization_v3.json'});
console.log('Finalized 15 visible main slides and 46 hidden backups.',JSON.stringify(result).slice(0,800));
