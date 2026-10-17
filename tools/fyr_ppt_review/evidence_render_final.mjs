import fs from 'node:fs/promises';
import {PresentationFile,FileBlob} from '@oai/artifact-tool';
const r='/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/fyr_ppt_evidence_revision_20261017';
const p=await PresentationFile.importPptx(await FileBlob.load(r+'/output/Wennie_Wan_First_Year_Assessment_Evidence_v6.pptx'));
await fs.mkdir(r+'/review/roundtrip',{recursive:true});
for(let i=0;i<p.slides.items.length;i++){
 const b=await p.export({slide:p.slides.items[i],format:'png',scale:1});await fs.writeFile(r+'/review/roundtrip/'+String(i+1).padStart(2,'0')+'.png',new Uint8Array(await b.arrayBuffer()));
}
console.log('Round-trip rendered',p.slides.items.length,'slides');
