import fs from 'node:fs/promises';
import {PresentationFile,FileBlob} from '@oai/artifact-tool';
const root='/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/fyr_ppt_15slide_revision_20261017';
const p=await PresentationFile.importPptx(await FileBlob.load(root+'/output/Wennie_Wan_First_Year_Assessment_15_Main_v3.pptx'));
await fs.mkdir(root+'/review/roundtrip',{recursive:true});
const states=[];
for(let i=0;i<p.slides.items.length;i++){
 const s=p.slides.items[i];states.push({number:i+1,hidden:s.hidden});
 const b=await p.export({slide:s,format:'png',scale:1});await fs.writeFile(root+'/review/roundtrip/'+String(i+1).padStart(2,'0')+'.png',new Uint8Array(await b.arrayBuffer()));
}
await fs.writeFile(root+'/review/roundtrip_visibility.json',JSON.stringify(states,null,2));
console.log('Rendered',states.length,'slides; hidden:',states.filter(s=>s.hidden).length);
