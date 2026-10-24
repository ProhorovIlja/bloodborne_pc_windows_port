/** Deterministic Bloodborne challenge planner; no game patching or server access. */
export const TIERS = Object.freeze(["normal", "hard", "nightmare"]);
const GOALS = Object.freeze([
  "Defeat your next available story boss",
  "Hunt an optional boss you can currently reach",
  "Complete one available Chalice Dungeon layer",
  "Clear a new area without dying",
  "Defeat a boss using one weapon of your choice",
  "Finish a new area without returning to the Hunter's Dream",
  "Defeat your next available boss with no summons",
  "Defeat a boss without upgrading your weapon during this hunt"
]);
const RULES = Object.freeze([
  "No blood vials during the final boss attempt",
  "Do not fire your gun during the challenge",
  "No visceral attacks",
  "No beast blood pellets or fire/bolt paper",
  "Keep your trick weapon in one form for the final fight",
  "Use no Hunter Tools",
  "No healing during a boss fight",
  "Do not equip any new Blood Gems for this attempt",
  "Complete the goal using the equipment you started with",
  "Defeat the boss without parrying"
]);
function nextRandom(value) {
  let t = (value + 0x6D2B79F5) >>> 0;
  t = Math.imul(t ^ t >>> 15, t | 1);
  t ^= t + Math.imul(t ^ t >>> 7, t | 61);
  return [((t ^ t >>> 14) >>> 0) / 4294967296, t >>> 0];
}
function hashString(str) {
  let h = 2166136261;
  for(let i=0;i<str.length;i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}
export function generateChallenge(seed, tier="normal") {
  if(typeof seed!=="string" || !/^[A-Za-z0-9_-]{1,24}$/.test(seed))
    throw new Error("Seed must be 1-24 letters, digits, underscores or dashes.");
  if(!TIERS.includes(tier)) throw new Error("Unknown challenge difficulty.");
  let state = hashString(seed+"|"+tier+"|v1");
  const roll = (count) => {
    const [n, next] = nextRandom(state);
    state = next;
    return Math.floor(n*count);
  };
  const goal = GOALS[roll(GOALS.length)];
  const first = roll(RULES.length);
  const rules = [RULES[first]];
  if(tier!=="normal") {
    let second=roll(RULES.length-1);
    if(second>=first)second++;
    rules.push(RULES[second]);
  }
  if(tier==="nightmare")
    rules.push("Finish within three attempts; reset or reroll if you exceed the limit");
  return Object.freeze({seed,tier,goal,rules:Object.freeze(rules),ruleset:"v1"});
}
