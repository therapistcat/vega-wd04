"""
Clustering Service - AI Duplicate Detection
============================================
Uses TF-IDF cosine similarity to detect and group duplicate civic complaints.

Designed to be swapped with SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
in the future for multilingual support.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict

from motor.motor_asyncio import AsyncIOMotorDatabase
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

CLUSTERS_COLLECTION = "clusters"
SIMILARITY_THRESHOLD = 0.40
MAX_CLUSTERS_TO_COMPARE = 200


def _build_text(category: str, location: str, description: str) -> str:
    """Build the representative text for a complaint."""
    return f"{category.lower()} {location.lower()} {description.lower()}"


def _compute_similarity_sync(new_text: str, existing_texts: list[str]) -> tuple[int, float]:
    """
    Synchronous TF-IDF comparison. Returns (best_index, best_score).
    Runs in a thread pool to avoid blocking the event loop.
    """
    if not existing_texts:
        return -1, 0.0

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
    all_texts = existing_texts + [new_text]

    try:
        tfidf_matrix = vectorizer.fit_transform(all_texts)
    except ValueError:
        return -1, 0.0

    new_vec = tfidf_matrix[-1]
    existing_vecs = tfidf_matrix[:-1]
    scores = cosine_similarity(new_vec, existing_vecs).flatten()

    best_idx = int(scores.argmax())
    best_score = float(scores[best_idx])
    return best_idx, best_score


async def process_issue(
    db: AsyncIOMotorDatabase,
    category: str,
    location: str,
    description: str,
    complaint_id: str | None = None,
    user_id: str | None = None,
    source: str = "web",
) -> Dict[str, Any]:
    """
    Core clustering function. Checks if complaint is a duplicate or needs a new cluster.

    Returns:
        {
            "cluster_id": str,
            "is_duplicate": bool,
            "similarity_score": float
        }
    """
    now = datetime.now(timezone.utc)
    new_text = _build_text(category, location, description)

    # Fetch recent clusters (representative text only for performance)
    cursor = (
        db[CLUSTERS_COLLECTION]
        .find({}, {"_id": 1, "text": 1})
        .sort("_id", -1)
        .limit(MAX_CLUSTERS_TO_COMPARE)
    )
    clusters_raw = await cursor.to_list(length=MAX_CLUSTERS_TO_COMPARE)

    cluster_ids = [str(doc["_id"]) for doc in clusters_raw]
    cluster_texts = [str(doc.get("text") or "") for doc in clusters_raw]

    # Run TF-IDF in a thread pool to avoid blocking the async event loop
    best_idx, best_score = await asyncio.get_event_loop().run_in_executor(
        None, _compute_similarity_sync, new_text, cluster_texts
    )

    report_entry: Dict[str, Any] = {
        "complaint_id": complaint_id,
        "description": description[:200],
        "timestamp": now,
        "user_id": user_id,
        "source": source,
    }

    if best_score >= SIMILARITY_THRESHOLD and best_idx >= 0:
        # Merge into existing cluster
        cluster_id = cluster_ids[best_idx]
        await db[CLUSTERS_COLLECTION].update_one(
            {"_id": cluster_id},
            {
                "$push": {"reports": report_entry},
                "$inc": {"report_count": 1},
                "$set": {"updated_at": now},
            },
        )
        return {
            "cluster_id": cluster_id,
            "is_duplicate": True,
            "similarity_score": round(best_score, 4),
        }

    # Create a new cluster
    count = await db[CLUSTERS_COLLECTION].count_documents({})
    cluster_id = f"C-{count + 1:04d}"

    cluster_doc = {
        "_id": cluster_id,
        "category": category,
        "location": location,
        "text": new_text,
        "status": "Open",
        "report_count": 1,
        "reports": [report_entry],
        "created_at": now,
        "updated_at": now,
    }
    await db[CLUSTERS_COLLECTION].insert_one(cluster_doc)

    return {
        "cluster_id": cluster_id,
        "is_duplicate": False,
        "similarity_score": 0.0,
    }


async def get_cluster_with_complaints(
    db: AsyncIOMotorDatabase, cluster_id: str
) -> Dict[str, Any] | None:
    """Fetch a cluster document."""
    return await db[CLUSTERS_COLLECTION].find_one({"_id": cluster_id})


async def list_clusters(
    db: AsyncIOMotorDatabase, limit: int = 100
) -> list[Dict[str, Any]]:
    """List clusters sorted by report count (most reported first)."""
    cursor = db[CLUSTERS_COLLECTION].find({}).sort("report_count", -1).limit(limit)
    return await cursor.to_list(length=limit)
