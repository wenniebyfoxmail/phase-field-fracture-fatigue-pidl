import fs from 'node:fs/promises';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {PresentationFile,FileBlob} from '@oai/artifact-tool';
process.env.RUNTIME_NODE='/Users/wenxiaofang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node';
process.env.RUNTIME_NODE_MODULES='/Users/wenxiaofang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
process.env.RUNTIME_BIN_DIR='/Users/wenxiaofang/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override';
const ROOT='/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/fyr_ppt_alignment_update_20261017';
const INPUT='/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/fyr_ppt_15slide_revision_20261017/output/Wennie_Wan_First_Year_Assessment_15_Main_v3.pptx';
const SKILL='/Users/wenxiaofang/.codex/plugins/cache/openai-primary-runtime/presentations/26.1013.11914/skills/presentations';
const PY='/Users/wenxiaofang/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3';
const p=await PresentationFile.importPptx(await FileBlob.load(INPUT));
const old=[...p.slides.items];
const spec=JSON.parse(await fs.readFile(ROOT+'/build/content_final.json','utf8'));
const C={blue:'#174B73',dark:'#1B2730',muted:'#52616B'};
let seq=0;
function addText(s,v,x,y,w,h,size=27,bold=false,color=C.dark){
 const a=s.shapes.add({geometry:'textbox',name:'alignment-text-'+(++seq),position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 a.text=v;a.text.style={typeface:'Arial',fontSize:size,bold,color,wrap:'word',verticalAlignment:'top',insets:0};return a;
}
function addTable(s,values,x,y,w,h,widths,size=24){
 const t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,columnWidths:widths,values});
 for(let r=0;r<values.length;r++)for(let c=0;c<values[0].length;c++){
  const a=t.getCell(r,c);a.fill=r===0?'#EAF1F5':'#FFFFFF';a.text.style={typeface:'Arial',fontSize:size,bold:r===0,color:r===0?C.blue:C.dark,insets:8,verticalAlignment:'middle'};
 }
 t.borders.assign({fill:'#B7C8D3',width:.6,style:'solid'});return t;
}
// Duplicate before changing any source body or notes.
for(let n=7;n<=15;n++){
 const s=old[n-1].duplicate();s.moveTo(p.slides.items.length-1);s.hidden=true;
 s.speakerNotes.text=old[n-1].speakerNotes.text;
}
const inspection=await p.inspect({kind:'slide,textbox,shape,image,table,notes',maxChars:2500000});
const records=inspection.records;
const recs=n=>records.filter(r=>r.slideIndex===n-1);
function at(n,kind,top){
 const a=recs(n).filter(r=>r.kind===kind&&Math.abs(r.position?.top-top)<.02);
 if(a.length!==1)throw new Error(`Ambiguous ${n}/${kind}/${top}: ${a.length}`);
 return p.resolve(a[0].id);
}
function replace(n,oldText,newText){
 const a=recs(n).filter(r=>r.kind==='textbox'&&r.text===oldText);
 if(a.length!==1)throw new Error(`Text anchor ${n}: ${oldText}`);
 const obj=p.resolve(a[0].id);obj.text=newText;return obj;
}
for(let n=7;n<=15;n++){
 at(n,'textbox',55).text=spec[n-1].title;
 old[n-1].speakerNotes.text='English narration\n'+spec[n-1].en+'\n\n中文对照\n'+spec[n-1].zh+'\n\nSources\n'+spec[n-1].source;
}
// 07: retain the original damage image and numerical values.
at(7,'image',142).position={left:62,top:160,width:1150,height:294};
addText(old[6],'Matching displacement BCs · Different starting damage · c83 peak',62,126,1150,29,23,true,C.blue);
const t7=at(7,'table',479);t7.cells.set(0,2,'Front along y = 0');
t7.position={left:62,top:466,width:1150,height:143};
t7.cells.set(1,3,'Wider band; close front');t7.cells.set(2,3,'Wider; shifted path; front behind');
const f7=at(7,'textbox',629);f7.text='FEM / PIDL. d ≥ 0.5, dimensionless. Band width is not crack opening.\nFront values are read along y = 0, not at the farthest 2D tip.';
f7.position={left:62,top:625,width:1150,height:53};f7.text.style={typeface:'Arial',fontSize:19,color:C.muted};
// 08–10: connect the existing results without changing any plotted data.
replace(8,'The sign of the history difference depends on topology and location','History differences depend on mesh and location');
replace(9,'c1 damage gap: Q4 10.22%, T3 10.43%. Initial damage already differs.','c1 damage relative L2: Q4 10.22%, T3 10.43%. Starting damage differs.');
replace(9,'Q4 history gap grows. T3 changes trend. Factor MAE grows on both.','History gaps change with stage; fatigue-factor gaps grow on both meshes.');
replace(10,'Local overlap matters','Compare local overlap');
// 11: report the limited gain from the fixed-damage check without causal ranking.
const t11=at(11,'table',174);t11.cells.set(2,1,'Test a displacement correction');
t11.cells.set(2,2,'Small reduction in active-field gap');
replace(11,'The coupled damage and history updates remain the next focus','Next: test starting state, fatigue updates and field optimisation');
// 12: completed work -> measured findings -> next question.
const lead=replace(12,'Close event timing does not establish local-field agreement','Q4 event timing is close; local fields still differ');
lead.text.style={typeface:'Arial',fontSize:35,bold:true,color:C.blue};
replace(12,'What the comparison shows','Observed differences');
replace(12,'Different initial damage, local shape and history; most gap remains after re-solving u','Starting damage, band width, path and fatigue history differ');
replace(12,'Next question: separate initial state, current-step fatigue and damage constraints','Next: test the causes and define which outputs support prediction');
// 13: four concrete tests, with moderate path improvement as one diagnostic.
replace(13,'Keep material, mesh and loading fixed. Change one part at a time.','Keep material, mesh and loading fixed. Test one part at a time.');
const oldTable13=recs(13).find(r=>r.kind==='table');p.delete([oldTable13.id]);
addTable(old[12],[['Controlled change','Question to test'],
 ['Common starting damage and history','How much later mismatch comes from the start?'],
 ['Current-step fatigue treatment','How do history increments and f change?'],
 ['Damage bounds and force balance','Do accepted fields satisfy the equations?'],
 ['Field representation and optimisation','Can we reduce drift and keep damage localised?']],62,237,1150,316,[570,580],24);
const end13=replace(13,'Track the complete trajectory, event timing and local-field differences','Improve local fields while preserving fatigue history and crack growth');
end13.position={left:62,top:579,width:1150,height:66};end13.text.style={typeface:'Arial',fontSize:28,bold:true,color:C.blue};
// 14: define the checked model range before asking what observations add.
addText(old[13],'Use outputs and loading ranges checked in Stage 1',62,130,1150,34,26,true,C.blue);
at(14,'table',164).position={left:62,top:183,width:1150,height:261};
at(14,'table',164).cells.set(0,0,'Observation known at prediction time');
replace(14,'Evaluate complete held-out trajectories. Check mean error, interval coverage and width near cracks.','Test unseen full trajectories. Report error, interval coverage and interval width near cracks.');
const footer14=at(14,'textbox',629);footer14.text='Planned study: compare future crack shape and growth at fixed prediction horizons.';
// 15: numerical checks -> observation value -> independent road measurement.
replace(15,'Choose the material model using relevant fracture and fatigue tests','Select and calibrate the material model using fracture and fatigue tests');
replace(15,'First-year findings lead to numerical controls, observation tests, then measured road prediction.','Numerical reliability → observation value → measured road prediction');
// Preserve all 46 existing backups and add B47–B55, retaining original notes.
for(let n=62;n<=70;n++){
 const d=spec[n-1],s=p.slides.items[n-1];
 const marker=at(n,'textbox',665);marker.text=d.backup_label;
 marker.position={left:1164,top:665,width:84,height:27};marker.text.style={typeface:'Arial',fontSize:18,color:C.muted};
 s.hidden=true;
}
await fs.mkdir(ROOT+'/review/slides',{recursive:true});
for(let i=0;i<p.slides.items.length;i++){
 const b=await p.export({slide:p.slides.items[i],format:'png',scale:1});
 await fs.writeFile(ROOT+'/review/slides/'+String(i+1).padStart(2,'0')+'.png',new Uint8Array(await b.arrayBuffer()));
 if((i+1)%15===0)console.log('Rendered',i+1);
}
const after=await p.inspect({kind:'slide,textbox,image,shape,table,notes,layout',maxChars:2500000});
await fs.writeFile(ROOT+'/review/final_inspect.json',JSON.stringify(after,null,2));
const tableOwners=[...new Set(after.records.filter(r=>r.kind==='table').map(r=>r.slideIndex+1))];
const candidate=ROOT+'/build/candidate.pptx';await(await PresentationFile.exportPptx(p)).save(candidate);
const {finalizePresentation}=await import(pathToFileURL(SKILL+'/container_tools/artifact_tool_utils.mjs').href);
const result=await finalizePresentation({workspaceDir:ROOT,candidatePath:candidate,
 finalPath:ROOT+'/output/Wennie_Wan_First_Year_Assessment_15_Main_v5.pptx',pythonExecutable:PY,
 integrityValidatorPath:SKILL+'/container_tools/inspect_presentation_package_integrity.py',
 layoutValidatorPath:SKILL+'/container_tools/inspect_presentation_layout_geometry.py',
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit',...tableOwners.flatMap(n=>['--require-native-table-slide',String(n)])],
 explicitTotalSlideCount:70,requiredNativeTableOwnerSlides:tableOwners,requiredNativeChartOwnerSlides:[],
 fontPolicy:{basis:'reference',families:['Arial'],referencePath:INPUT,referenceSha256:createHash('sha256').update(readFileSync(INPUT)).digest('hex')},
 verifyArtifactToolImport:true,receiptPath:ROOT+'/review/finalization_v5.json'});
console.log('Finalized',JSON.stringify(result).slice(0,600));
