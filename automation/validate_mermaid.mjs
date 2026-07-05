// Batch Mermaid syntax validator.
// Usage: node validate_mermaid.mjs <json-file>
//   input  : JSON array of mermaid code strings
//   output : JSON array of { ok: bool, error: string } (stdout)
// Exit 0 always (results are in the JSON). Used by daily_trend_bot to drop/repair
// diagrams that would render as "Syntax error in text".
import { JSDOM } from "jsdom";
import fs from "fs";

const dom = new JSDOM("<!DOCTYPE html><body></body>", { pretendToBeVisual: true });
global.window = dom.window;
global.document = dom.window.document;

const mermaid = (await import("mermaid")).default;
mermaid.initialize({ startOnLoad: false, securityLevel: "loose" });

const diagrams = JSON.parse(fs.readFileSync(process.argv[2], "utf-8"));
const results = [];
for (const code of diagrams) {
  try {
    await mermaid.parse(String(code).trim());
    results.push({ ok: true, error: "" });
  } catch (e) {
    results.push({ ok: false, error: String(e && e.message ? e.message : e).split("\n").slice(0, 5).join(" ") });
  }
}
process.stdout.write(JSON.stringify(results));
