"""Interactive CLI chat using the full RAG pipeline (retrieval + Groq LLM answer).

Usage:
    python scripts/chat_cli.py
    python scripts/chat_cli.py "What is the ELSS lock-in period?"
"""

import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.rag_pipeline import RAGPipeline

DISCLAIMER = "Facts-only. No investment advice."


def ask(pipeline: RAGPipeline, query: str, history: list[dict]) -> list[dict]:
    result = pipeline.run(query=query, conversation_history=history)
    print(f"\nAssistant: {result.answer}\n")
    if result.sources:
        print("Sources used:")
        for i, s in enumerate(result.sources, 1):
            url = s.get("source_url") or s.get("filename", "")
            print(f"  {i}. {url}")
    if result.retrieval_scores:
        print(f"\n(retrieval scores: {[round(s, 3) for s in result.retrieval_scores]})")
    history.append({"role": "user", "content": query})
    history.append({"role": "assistant", "content": result.answer})
    return history


if __name__ == "__main__":
    print("#" * 60)
    print("# RAG CHATBOT — INTERACTIVE CLI")
    print("#" * 60)
    print(f"\n{DISCLAIMER}\n")

    pipeline = RAGPipeline()

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        ask(pipeline, query, [])
        sys.exit(0)

    history = []
    print("Type your question and press Enter. Type 'exit' or 'quit' to stop.\n")
    while True:
        try:
            query = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye!")
            break
        if query.lower() in ("exit", "quit"):
            print("Bye!")
            break
        if not query:
            continue
        history = ask(pipeline, query, history)
