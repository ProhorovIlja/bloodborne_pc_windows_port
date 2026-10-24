import assert from "node:assert/strict";
import {generateChallenge,TIERS} from "./challenges.mjs";
for(const tier of TIERS) {
  const a=generateChallenge("HUNT-2026",tier),b=generateChallenge("HUNT-2026",tier);
  assert.deepEqual(a,b,"same input reproduces same run");
  assert.equal(a.tier,tier);
  assert.ok(a.goal.length>10);
  assert.equal(a.rules.length,tier==="normal"?1:tier==="hard"?2:3);
  assert.equal(new Set(a.rules).size,a.rules.length,"no duplicate rules");
}
for(const invalid of ["","../evil","x".repeat(25),"<script>","abc def"]){
  assert.throws(()=>generateChallenge(invalid),"unsafe seed rejected");
}
assert.throws(()=>generateChallenge("SAFE","extreme"));
assert.notDeepEqual(generateChallenge("A","normal"),generateChallenge("B","normal"));
console.log("PASS: deterministic offline seeded challenges, tier restrictions, URL-safe input");
