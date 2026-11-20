// A stand-in for the agent's service on port 8003, so the e2e tests never reach
// the one `npm run dev` starts. It answers 202 and remembers each request, with
// its body if it has one.
import { createServer } from "node:http";

const calls = [];

createServer((request, response) => {
  response.setHeader("content-type", "application/json");
  if (request.method === "GET" && request.url === "/health") {
    response.end(JSON.stringify({ status: "ok" }));
    return;
  }
  if (request.method === "GET" && request.url === "/calls") {
    response.end(JSON.stringify(calls));
    return;
  }
  let body = "";
  request.on("data", (chunk) => {
    body += chunk;
  });
  request.on("end", () => {
    const call = `${request.method} ${request.url}`;
    calls.push(body ? `${call} ${body}` : call);
    response.statusCode = 202;
    response.end("null");
  });
}).listen(8003, "127.0.0.1");
