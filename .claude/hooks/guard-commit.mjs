import { appendFileSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const input = JSON.parse(readFileSync(0, "utf8"));
const command = input.tool_input.command;
const bypasses = [/--no-verify/, /\bgit\b.*\bcommit\b.*\s-n\b/, /LEFTHOOK=0/, /core\.hooksPath/];
const blocked = bypasses.some((pattern) => pattern.test(command));
const log = (file, entry) =>
  appendFileSync(join(homedir(), ".claude", file), JSON.stringify(entry) + "\n");

const entry = {
  time: new Date().toISOString(),
  session: input.session_id,
  cwd: input.cwd,
  transcript: input.transcript_path,
  command,
};

if (/\bgit\b/.test(command)) log("guard-calls.log", { ...entry, blocked });

if (blocked) {
  log("blocked-commits.log", entry);
  console.error("Blocked: the pre-commit checks must run. Fix the failure and commit again.");
  process.exit(2);
}
