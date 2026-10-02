"""Tiny demo web UI for the RAG chatbot — no Postgres/Redis needed.

Run:
    py -m uvicorn app.web_demo:app --port 8002 --reload

Then open http://localhost:8002
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.services.rag_pipeline import RAGPipeline

app = FastAPI(title="Mutual Fund FAQ Demo")

import os
_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(_dist):
    from fastapi.staticfiles import StaticFiles
    app.mount("/assets", StaticFiles(directory=os.path.join(_dist, "assets")), name="assets")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag = RAGPipeline()

HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Mutual Fund FAQ Assistant</title>
  <style>
    body { font-family: Segoe UI, Arial, sans-serif; max-width: 760px; margin: 30px auto; padding: 0 16px; }
    h1 { color: #1e3a8a; }
    #chat { border: 1px solid #ddd; border-radius: 8px; padding: 12px; height: 380px; overflow-y: auto; margin-bottom: 12px; }
    .q { font-weight: 700; margin-top: 10px; color: #1e3a8a; }
    .a { margin: 4px 0 8px 0; }
    .src { font-size: 13px; color: #555; }
    #row { display: flex; gap: 8px; }
    #q { flex: 1; padding: 10px; border-radius: 6px; border: 1px solid #bbb; }
    button { padding: 10px 16px; border: none; background: #2563eb; color: white; border-radius: 6px; cursor: pointer; }
    ul.examples { padding-left: 18px; color: #333; }
    .examples li { cursor: pointer; }
  </style>
</head>
<body>
  <h1>Mutual Fund FAQ Assistant</h1>
  <p><b>Welcome!</b> Ask factual questions about our HDFC mutual fund schemes.</p>
  <ul class="examples">
    <li onclick="setQ('What is the expense ratio of HDFC Large Cap Fund?')">What is the expense ratio of HDFC Large Cap Fund?</li>
    <li onclick="setQ('What is the ELSS lock-in period?')">What is the ELSS lock-in period?</li>
    <li onclick="setQ('What is the minimum SIP amount?')">What is the minimum SIP amount?</li>
  </ul>
  <p><i>Facts-only. No investment advice.</i></p>
  <div id="chat"></div>
  <div id="row">
    <input id="q" placeholder="Type your question..." onkeydown="if(event.key==='Enter') send()">
    <button onclick="send()">Ask</button>
  </div>
  <script>
    function setQ(t){ document.getElementById('q').value = t; }
    async function send(){
      const q = document.getElementById('q').value.trim();
      if(!q) return;
      const chat = document.getElementById('chat');
      chat.innerHTML += `<div class="q">You: ${q}</div><div class="a">Thinking…</div>`;
      document.getElementById('q').value = '';
      chat.scrollTop = chat.scrollHeight;
      const r = await fetch('/api/ask', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({question:q})});
      const j = await r.json();
      chat.lastElementChild.innerHTML = `<b>Assistant:</b> ${j.answer.replace(/\\n/g,'<br>')}` +
        (j.sources && j.sources.length ? `<div class="src"><b>Sources:</b><br>${j.sources.map(s=>`<a href="${s.source_url||'#'}" target="_blank">${s.source_url||s.filename}</a>`).join('<br>')}</div>` : '');
      chat.scrollTop = chat.scrollHeight;
    }
  </script>
</body>
</html>
"""


class AskRequest(BaseModel):
    question: str


@app.get("/", response_class=HTMLResponse)
def index():
    # Prefer the built React app, fall back to the inline demo UI
    import os
    dist_index = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist", "index.html")
    if os.path.exists(dist_index):
        with open(dist_index, "r", encoding="utf-8") as f:
            return f.read()
    return HTML


@app.post("/api/ask")
def ask(req: AskRequest):
    result = rag.run(query=req.question)
    return {"answer": result.answer, "sources": result.sources}
