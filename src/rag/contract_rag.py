"""
RAG Document Intelligence Engine for Infrastructure Contracts.
Indexes structured contract clauses and full-text agreements using a local
TF-IDF / vector semantic retriever with exact clause citations and verbatim excerpts.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re

from config.settings import CONTRACTS_RAW_DIR, LLM_PROVIDER, GEMINI_API_KEY, OPENAI_API_KEY


class ContractRAGEngine:
    """
    Retrieval-Augmented Generation engine for legal contracts and clauses.
    Grounded in actual contract texts with verbatim citations and zero hallucination.
    """

    def __init__(self, clauses_df: pd.DataFrame, contracts_dir: Optional[Path] = None):
        self.clauses_df = clauses_df.copy()
        self.contracts_dir = Path(contracts_dir) if contracts_dir else CONTRACTS_RAW_DIR
        self.corpus_chunks: List[Dict[str, Any]] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix = None
        self.is_indexed = False

    def build_index(self):
        """Builds search index over structured clauses and raw contract documents."""
        self.corpus_chunks.clear()

        # 1. Index structured clauses from contract_clauses.csv
        if not self.clauses_df.empty:
            for _, row in self.clauses_df.iterrows():
                chunk_text = f"{row.get('title', '')}: {row.get('clause_text', '')}"
                is_pen = str(row.get("penalty_applicable", "")).lower() in ["true", "1", "yes"]
                self.corpus_chunks.append({
                    "source_type": "STRUCTURED_CLAUSE",
                    "clause_id": row.get("clause_id", ""),
                    "contract_id": row.get("contract_id", ""),
                    "vendor_id": row.get("vendor_id", ""),
                    "clause_number": str(row.get("clause_number", "")),
                    "section": str(row.get("section", "")),
                    "title": row.get("title", ""),
                    "text": str(row.get("clause_text", "")),
                    "page": row.get("document_page", "N/A"),
                    "penalty_applicable": is_pen,
                    "searchable_content": f"Contract {row.get('contract_id')} Vendor {row.get('vendor_id')} Clause {row.get('clause_number')} {row.get('title')}: {row.get('clause_text')}"
                })

        # 2. Index raw contract text files from contracts_raw/
        if self.contracts_dir.exists():
            for txt_file in self.contracts_dir.glob("*.txt"):
                contract_id = txt_file.stem
                try:
                    with open(txt_file, "r", encoding="utf-8", errors="ignore") as f:
                        lines = [line.strip() for line in f if line.strip()]

                    curr_clause_num = ""
                    curr_title = ""
                    curr_body = []

                    for line in lines:
                        if line.startswith("Clause "):
                            if curr_clause_num and curr_body:
                                body_str = " ".join(curr_body)
                                full_clause_str = (curr_title + " " + body_str).lower()
                                is_pen_raw = "liquidated damages" in full_clause_str or "penalty" in full_clause_str
                                self.corpus_chunks.append({
                                    "source_type": "RAW_CONTRACT_FILE",
                                    "clause_id": f"{contract_id}-{curr_clause_num.replace('.', '')}",
                                    "contract_id": contract_id,
                                    "vendor_id": "From Document",
                                    "clause_number": curr_clause_num,
                                    "section": curr_clause_num.split(".")[0],
                                    "title": curr_title,
                                    "text": body_str,
                                    "page": "Document Text",
                                    "penalty_applicable": is_pen_raw,
                                    "searchable_content": f"{contract_id} Clause {curr_clause_num} {curr_title}: {body_str}"
                                })
                                curr_body = []
                            parts = line.split(":", 1)
                            clause_part = parts[0].replace("Clause", "").strip()
                            curr_clause_num = clause_part
                            curr_title = parts[1].strip() if len(parts) > 1 else "Contract Clause"
                        elif not line.startswith("CONTRACT ") and not line.startswith("Vendor:"):
                            curr_body.append(line)

                    # Last clause in file
                    if curr_clause_num and curr_body:
                        body_str = " ".join(curr_body)
                        full_clause_str = (curr_title + " " + body_str).lower()
                        is_pen_raw = "liquidated damages" in full_clause_str or "penalty" in full_clause_str
                        self.corpus_chunks.append({
                            "source_type": "RAW_CONTRACT_FILE",
                            "clause_id": f"{contract_id}-{curr_clause_num.replace('.', '')}",
                            "contract_id": contract_id,
                            "vendor_id": "From Document",
                            "clause_number": curr_clause_num,
                            "section": curr_clause_num.split(".")[0],
                            "title": curr_title,
                            "text": body_str,
                            "page": "Document Text",
                            "penalty_applicable": is_pen_raw,
                            "searchable_content": f"{contract_id} Clause {curr_clause_num} {curr_title}: {body_str}"
                        })
                except Exception as e:
                    pass

        # Build TF-IDF vector matrix
        if self.corpus_chunks:
            texts = [c["searchable_content"] for c in self.corpus_chunks]
            self.vectorizer = TfidfVectorizer(
                stop_words="english",
                ngram_range=(1, 2),
                max_features=5000
            )
            self.tfidf_matrix = self.vectorizer.fit_transform(texts)
            self.is_indexed = True

    def retrieve(
        self,
        query: str,
        contract_id: Optional[str] = None,
        vendor_id: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top-k most relevant contract clauses grounded in source texts.
        Supports filtering by specific contract_id or vendor_id.
        """
        if not self.is_indexed:
            self.build_index()

        if not self.corpus_chunks or self.vectorizer is None or self.tfidf_matrix is None:
            return []

        # Transform query
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.tfidf_matrix)[0]

        # Filter and rank
        candidates = []
        for idx, score in enumerate(scores):
            chunk = self.corpus_chunks[idx]
            if contract_id and chunk["contract_id"] != contract_id:
                continue
            if vendor_id and chunk["vendor_id"] != vendor_id and chunk["vendor_id"] != "From Document":
                continue

            if score >= 0.15:  # Minimum relevance floor
                candidates.append((score, chunk))

        # Sort descending by score
        candidates.sort(key=lambda x: x[0], reverse=True)

        results = []
        seen_keys = set()
        for score, chunk in candidates[:top_k]:
            key = f"{chunk['contract_id']}_{chunk['clause_number']}"
            if key in seen_keys:
                continue
            seen_keys.add(key)
            results.append({
                "relevance_score": round(float(score), 4),
                "contract_id": chunk["contract_id"],
                "clause_number": chunk["clause_number"],
                "section": chunk["section"],
                "title": chunk["title"],
                "text": chunk["text"],
                "page": chunk["page"],
                "penalty_applicable": chunk["penalty_applicable"],
                "source_type": chunk["source_type"]
            })

        return results

    def answer_contract_question(
        self,
        question: str,
        contract_id: Optional[str] = None,
        vendor_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Answers legal and contractual inquiries using retrieved evidence chunks.
        Strictly distinguishes actual contract wording from analysis.
        """
        evidence = self.retrieve(question, contract_id=contract_id, vendor_id=vendor_id, top_k=3)

        if not evidence or evidence[0]["relevance_score"] < 0.20:
            return {
                "question": question,
                "answer": "Insufficient data: No relevant contractual clauses or policy documents were found matching this inquiry in the workspace repository.",
                "evidence_retrieved": False,
                "citations": []
            }

        # Deterministic evidence synthesis
        citations = []
        clause_summaries = []
        for e in evidence:
            citation_str = f"[{e['contract_id']} - Clause {e['clause_number']}: '{e['title']}']"
            citations.append({
                "contract_id": e["contract_id"],
                "clause_number": e["clause_number"],
                "title": e["title"],
                "page": e["page"],
                "verbatim_text": e["text"],
                "penalty_applicable": e["penalty_applicable"]
            })
            clause_summaries.append(f"{citation_str}: \"{e['text']}\"")

        # Synthesize clear answer
        lead_clause = evidence[0]
        answer_text = (
            f"Based on retrieved evidence from {lead_clause['contract_id']}, "
            f"Clause {lead_clause['clause_number']} ('{lead_clause['title']}') states:\n\n"
            f"> \"{lead_clause['text']}\"\n\n"
            f"**Contractual Status**: Liquidated damages/penalty applicable: {'YES' if lead_clause['penalty_applicable'] else 'NO'}. "
            f"This clause governs contractor and supplier obligations under the specified terms."
        )

        return {
            "question": question,
            "answer": answer_text,
            "evidence_retrieved": True,
            "citations": citations
        }
