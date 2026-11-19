// A stand-in for the agent's service on port 8003, so the e2e tests never reach
// the one `npm run dev` starts. It answers 202 and remembers each request.
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
  calls.push(`${request.method} ${request.url}`);
  response.statusCode = 202;
  response.end("{}");
}).listen(8003, "127.0.0.1");
