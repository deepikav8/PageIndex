import streamlit as st
import json

from services.page_index import (
    submit_pdf, is_ready, get_tree,
    clean_tree, create_node_map
)
from services.llm_service2 import call_llm
from utils.json_utils import safe_json_parse


from fastapi import FastAPI, UploadFile, File
import shutil
import json


app = FastAPI(
    title="PageIndex PDF QA PoC",
    description="Reasoning-based, vectorless retrieval over PDFs",
    version="0.1"
)
from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
    <head>
        <title>PageIndex </title>
        <style>
            body {
                font-family: Arial, sans-serif;
                padding: 40px;
                background: #f7f7f7;
            }
            h2 {
                margin-bottom: 20px;
            }
            input, button {
                font-size: 16px;
                padding: 10px 14px;
                margin-top: 10px;
            }
            button {
                cursor: pointer;
                background-color: #4F46E5;
                color: white;
                border: none;
                border-radius: 6px;
            }
            button:hover {
                background-color: #4338CA;
            }
            .card {
                background: white;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 20px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            }
            pre {
                background: #111;
                color: #0f0;
                padding: 15px;
                overflow-x: auto;
                border-radius: 6px;
            }
        </style>
    </head>

    <body>
        <h2>📄 PageIndex PDF QA </h2>

        <div class="card">
            <h3>1️⃣ Upload PDF</h3>
            <form action="/upload" method="post" enctype="multipart/form-data">
                <input type="file" name="file" required /><br/>
                <button type="submit">Upload & Index</button>
            </form>
        </div>

        <div class="card">
            <h3>2️⃣ View Document Tree</h3>
            <form action="/tree-ui" method="post">
                <input type="text" name="doc_id" placeholder="Paste doc_id here" size="40" required /><br/>
                <button type="submit">Show Tree</button>
            </form>
        </div>

        <div class="card">
            <h3>3️⃣ Ask Question</h3>
            <form action="/ask-ui" method="post">
                <input type="text" name="doc_id" placeholder="doc_id" size="40" required /><br/><br/>
                <input type="text" name="query" placeholder="Your question" size="80" required /><br/>
                <button type="submit">Ask</button>
            </form>
        </div>
    </body>
    </html>
    """

DOCUMENTS = {}  # simple in-memory store 

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    path = f"tmp_{file.filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    doc_id = submit_pdf(path)
    DOCUMENTS[doc_id] = {"path": path}

    return {"doc_id": doc_id, "status": "submitted"}

@app.get("/tree/{doc_id}")
def get_document_tree(doc_id: str):
    if not is_ready(doc_id):
        return {"status": "processing"}

    tree = get_tree(doc_id)

    DOCUMENTS[doc_id]["tree"] = tree
    DOCUMENTS[doc_id]["node_map"] = create_node_map(tree)

    return {
        "status": "ready",
        "tree": clean_tree(tree)
    }


from fastapi import Form

@app.post("/tree-ui", response_class=HTMLResponse)
def tree_ui(doc_id: str = Form(...)):
    if not is_ready(doc_id):
        return "<h3>⏳ Document still processing. Please refresh.</h3>"

    tree = get_tree(doc_id)
    DOCUMENTS[doc_id]["tree"] = tree
    DOCUMENTS[doc_id]["node_map"] = create_node_map(tree)

    clean = clean_tree(tree)

    return f"""
    <h3>📑 Document Structure (Tree)</h3>
    <pre>{json.dumps(clean, indent=2)}</pre>
    <br/>
    <a href="/">⬅ Back</a>
    """

@app.post("/ask-ui", response_class=HTMLResponse)
def ask_ui(doc_id: str = Form(...), query: str = Form(...)):

    if doc_id not in DOCUMENTS or "tree" not in DOCUMENTS[doc_id]:
        return "<h3>⚠️ Tree not loaded. Please view tree first.</h3><a href='/'>⬅ Back</a>"

    tree = DOCUMENTS[doc_id]["tree"]
    tree_wo_text = clean_tree(tree)
    node_map = create_node_map(tree)

    search_prompt = f"""
    You are given a question and a tree structure of a document.
    Each node has node_id, title, and summary.

    Question: {query}

    Tree:
    {json.dumps(tree_wo_text, indent=2)}
    Return JSON only:
    {{
      "thinking": "...",
      "node_list": ["node_id"]
    }}
    """

    reasoning = safe_json_parse(call_llm(search_prompt))

    if not reasoning["node_list"]:
        return "<h3>⚠️ No relevant sections found</h3><a href='/'>⬅ Back</a>"

    node_ids = reasoning["node_list"]

    content = "\n\n".join(
        node_map[n]["text"] for n in node_ids if n in node_map
    )

    answer_prompt = f"""
    Answer ONLY using the context below.

    Question: {query}

    Context:
    {content}
    """

    answer = call_llm(answer_prompt)

    return f"""
    <h3>✅ Answer</h3>
    <p>{answer}</p>

    <h4>📍 Source sections</h4>
    <ul>
        {"".join(f"<li>{node_map[n]['title']} (Page {node_map[n]['page_index']})</li>" for n in node_ids)}
    </ul>

    <a href="/">⬅ Back</a>
    """
