import uuid
from datetime import datetime
from Database.ChromaDB.ChromaDBMain import memory_collection

def save_memory(content:str, category:str = "general", metadata_extra: dict = None):
    doc_id = str(uuid.uuid4())
    now_iso = datetime.now().isoformat()

    meta = {
        "timestamp":now_iso,
        "category" : category
    }

    if metadata_extra:
        meta.update(metadata_extra)

    memory_collection.add(
        ids = [doc_id],
        documents=[content],
        metadatas=[meta]
    )
    return doc_id

def search_memory(query:str, limit: int  = 3):
    results = memory_collection.query(
        query_texts=[query],
        n_results=limit
    )

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    formatted_resuls = []

    for doc, meta, dist in zip(docs, metas, distances):
        formatted_resuls.append({
            "content":   doc,
            "timestamp": meta.get("timestamp"),
            "category" : meta.get("category"),
            "relevance_score" : round(1-dist, 3) if dist is not None else 1.0
        }
        )
    return formatted_resuls
