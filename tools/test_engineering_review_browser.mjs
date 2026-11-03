import assert from "node:assert/strict";
import { validateProofLayout, validateProofNavigation } from "./check_engineering_review_browser.mjs";

const layout = { viewportWidth:390,pageWidth:390,duplicateIds:[],missingTargets:[],primaryHeadings:1,
  cards:[0,1,2].map(i=>({left:38,right:352,top:i*180,bottom:i*180+160})),scopeDisclosed:true,trustDisclosed:true };
validateProofLayout(layout,390);
for(const change of [{pageWidth:440},{duplicateIds:["duplicate"]},{missingTargets:["proof"]},{primaryHeadings:2},{scopeDisclosed:false},{trustDisclosed:false}])
  assert.throws(()=>validateProofLayout({...layout,...change},390));
assert.throws(()=>validateProofLayout({...layout,cards:[...layout.cards.slice(0,2),{left:38,right:400,top:100,bottom:200}]},390));
const nav={hash:"#execution-proof",activeElement:"execution-proof",top:20,height:844,detailsOpen:true,commandVisible:true};
validateProofNavigation(nav);
for(const change of [{hash:"#elsewhere"},{activeElement:""},{top:-100},{top:900},{detailsOpen:false},{commandVisible:false}])
  assert.throws(()=>validateProofNavigation({...nav,...change}));
console.log("PASS: two positive layout/navigation contracts and thirteen rejection cases; invented fixtures, not browser renders.");
