/** Exercise the actual offline frontier controls against the published aggregate input. */
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const frontier = JSON.parse(fs.readFileSync(path.join(root, "portfolio/qualification_frontier.json"), "utf8"));
const script = fs.readFileSync(path.join(root, "tools/qualification_frontier.js"), "utf8");
const template = fs.readFileSync(path.join(root, "tools/qualification_frontier_template.html"), "utf8");
const states = ["qualified", "missing_home_only", "missing_court_only", "missing_both"];
const totals = Object.fromEntries(["required", ...states].map(key => [key, frontier.editions.reduce((n, row) => n + row[key], 0)]));
const summary = {...frontier, totals, unknown:totals.required - totals.qualified};
const sourceBefore = JSON.stringify(summary);
function element(value = "") {return {value, textContent:"", handlers:{}, addEventListener(event, handler) {this.handlers[event] = handler;}};}
const focus = element("all"), order = element("season"), live = element();
const nodes = frontier.editions.map(row => {
  const value = element();
  const segments = states.map(state => ({dataset:{state}, style:{width:`${100 * row[state] / row.required}%`}}));
  return {dataset:{season:String(row.season)}, hidden:false, value, segments,
    querySelector(selector) {assert.equal(selector,".frontier-value"); return value;},
    querySelectorAll(selector) {assert.equal(selector,".frontier-segment"); return segments;}};
});
const chart = {children:[...nodes], appendChild(node) {this.children = this.children.filter(item => item !== node);this.children.push(node);}};
const ids = new Map([["frontier-data",{textContent:JSON.stringify(summary)}],["frontier-focus",focus],["frontier-order",order],["frontier-live",live],["frontier-chart",chart]]);
const sandbox = {document:{getElementById(id) {assert.ok(ids.has(id),id);return ids.get(id);},
  querySelectorAll(selector) {assert.equal(selector,".frontier-edition");return nodes;}}};
vm.createContext(sandbox);
vm.runInContext(script,sandbox,{filename:"qualification_frontier.js"});
let checks=0;
function test(name, run) {run(); console.log(`ok ${++checks} - ${name}`);}
function change(control,value) {control.value=value;control.handlers.change();}
const visible = () => chart.children.filter(n => !n.hidden).map(n => Number(n.dataset.season));
const widths = () => nodes.map(n => n.segments.map(s => s.style.width));
const originalWidths = widths();

test("default renders all frozen editions with full-population context", () => {
  assert.deepEqual(visible(),frontier.editions.map(r=>r.season));
  assert.match(live.textContent,/102 of 583 rows qualified; 481 remain unknown/);
});
test("home-context focus selects the three actual editions", () => {
  change(focus,"missing_home_only");
  assert.deepEqual(visible(),[2016,2017,2021]);
  assert.match(live.textContent,/3 editions shown; 21 rows/);
  assert.equal(nodes[0].value.textContent,"3 / 63 in selected state");
});
test("largest selected gap first is stable and keeps the 2021 exception visible", () => {
  change(order,"gap");
  assert.deepEqual(visible(),[2021,2016,2017]);
});
test("zero category reports unknown semantics without pretending completion", () => {
  change(focus,"missing_court_only");
  assert.deepEqual(visible(),[]);
  assert.match(live.textContent,/Zero in this category does not prove the absence/);
  assert.match(live.textContent,/481 remain unknown/);
});
test("both-unqualified focus uses all nine editions and orders by that count", () => {
  change(focus,"missing_both");
  assert.equal(visible().length,9);
  assert.equal(visible()[0],2022);
  assert.match(live.textContent,/460 rows/);
});
test("qualification focus does not include the unqualified 2021 edition", () => {
  change(focus,"qualified");
  assert.equal(visible().length,8);
  assert.equal(visible()[0],2025);
  assert.ok(!visible().includes(2021));
});
test("focus and order never rescale the published segments", () => {
  assert.deepEqual(widths(),originalWidths);
  for(const node of nodes) for(const segment of node.segments) {
    assert.equal(segment.style.opacity,segment.dataset.state==="qualified"?"1":"0.24");
  }
});
test("all-state reset restores chronological complete coverage", () => {
  change(focus,"all"); change(order,"season");
  assert.deepEqual(visible(),frontier.editions.map(r=>r.season));
  assert.ok(nodes.every(n=>n.segments.every(s=>s.style.opacity==="1")));
  assert.equal(JSON.stringify(summary),sourceBefore);
});
test("native controls, polite updates and complete static table remain present", () => {
  assert.match(template,/<label for="frontier-focus">/);
  assert.match(template,/<label for="frontier-order">/);
  assert.match(template,/aria-live="polite"/);
  assert.match(template,/<table><caption>/);
  assert.doesNotMatch(script,/fetch\(|XMLHttpRequest|innerHTML/);
});
console.log(JSON.stringify({status:"PASS",checks,actual_script_executed:true,network_requests:0,model_fits:0}));
