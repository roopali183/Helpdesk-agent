import os
import re

KB_DIR = os.path.join(os.path.dirname(__file__), "kb_articles")

STOPWORDS = {
    # question words and filler
    "how", "do", "does", "did", "i", "to", "the", "a", "an", "my", "is", "are",
    "can", "could", "what", "which", "who", "when", "where", "why", "of", "for",
    "in", "on", "at", "by", "from", "and", "or", "me", "it", "its", "with",
    "you", "your", "we", "our", "if", "will", "not", "this", "that", "these",
    "be", "been", "as", "so", "up", "please", "need", "want", "get", "have",
    "has", "had", "should", "would", "after", "first", "also", "then",
}


def _stem(word: str) -> str:
    """Very simple plural handling: 'passwords' -> 'password'."""
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _tokenize(text: str) -> set:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {_stem(w) for w in words} - STOPWORDS


def search_kb(query: str, top_k: int = 2) -> dict:
    """Keyword search over the markdown help articles."""
    if not os.path.isdir(KB_DIR):
        return {"found": False, "message": "Knowledge base folder not found."}

    query_words = _tokenize(query)
    if not query_words:
        return {"found": False, "message": "Query has no searchable words."}

    results = []
    for filename in sorted(os.listdir(KB_DIR)):
        if not filename.endswith(".md"):
            continue
        with open(os.path.join(KB_DIR, filename), encoding="utf-8") as f:
            content = f.read()

        title_words = _tokenize(filename.replace("_", " ").replace(".md", ""))
        score = len(query_words & _tokenize(content)) + 2 * len(query_words & title_words)
        if score > 0:
            results.append((score, filename, content))

    results.sort(key=lambda r: r[0], reverse=True)

    if not results:
        return {"found": False, "message": "No matching articles found."}

    return {
        "found": True,
        "articles": [{"source": name, "content": text} for _, name, text in results[:top_k]],
    }


if __name__ == "__main__":
    tests = [
        "how do I set up VPN",
        "what is the password policy",
        "how do I install new software",
        "how do I configure the office coffee machine",
        "my printer will not print",
    ]
    for q in tests:
        r = search_kb(q)
        sources = [a["source"] for a in r["articles"]] if r["found"] else "NOT FOUND"
        print(f"{q!r:55} -> {sources}")