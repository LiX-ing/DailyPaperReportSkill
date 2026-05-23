from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .openalex_client import Paper


class SeenPaperStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self._init_table()

    def _init_table(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_papers (
                paper_id TEXT PRIMARY KEY,
                title TEXT,
                seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS generated_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id TEXT NOT NULL,
                title TEXT,
                source TEXT,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                md_path TEXT,
                feishu_card_path TEXT,
                status TEXT DEFAULT 'success'
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS paper_cache (
                paper_id TEXT PRIMARY KEY,
                title TEXT,
                abstract TEXT,
                year INTEGER,
                venue TEXT,
                venue_candidates TEXT,
                doi TEXT,
                url TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.conn.commit()

    def exists(self, paper_id: str) -> bool:
        cur = self.conn.execute(
            "SELECT 1 FROM seen_papers WHERE paper_id = ? LIMIT 1", (paper_id,)
        )
        return cur.fetchone() is not None

    def add(self, paper_id: str, title: str) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO seen_papers(paper_id, title) VALUES(?, ?)",
            (paper_id, title),
        )
        self.conn.commit()

    def was_generated(self, paper_id: str) -> bool:
        cur = self.conn.execute(
            "SELECT 1 FROM generated_records WHERE paper_id = ? AND status = 'success' LIMIT 1",
            (paper_id,),
        )
        return cur.fetchone() is not None

    def add_generated_record(
        self,
        paper_id: str,
        title: str,
        source: str,
        md_path: str | None,
        feishu_card_path: str | None,
        status: str = "success",
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO generated_records(
                paper_id, title, source, md_path, feishu_card_path, status
            ) VALUES(?, ?, ?, ?, ?, ?)
            """,
            (paper_id, title, source, md_path, feishu_card_path, status),
        )
        self.conn.commit()

    def upsert_cache(self, papers: list["Paper"]) -> None:
        rows = []
        for p in papers:
            venue_candidates = "|".join(p.venue_candidates or [])
            rows.append(
                (
                    p.paper_id,
                    p.title,
                    p.abstract,
                    p.year,
                    p.venue,
                    venue_candidates,
                    p.doi,
                    p.url,
                )
            )
        self.conn.executemany(
            """
            INSERT INTO paper_cache(
                paper_id, title, abstract, year, venue, venue_candidates, doi, url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(paper_id) DO UPDATE SET
                title=excluded.title,
                abstract=excluded.abstract,
                year=excluded.year,
                venue=excluded.venue,
                venue_candidates=excluded.venue_candidates,
                doi=excluded.doi,
                url=excluded.url,
                updated_at=CURRENT_TIMESTAMP
            """,
            rows,
        )
        self.conn.commit()

    def load_cache(self, limit: int = 1000) -> list["Paper"]:
        from .openalex_client import Paper

        cur = self.conn.execute(
            """
            SELECT paper_id, title, abstract, year, venue, venue_candidates, doi, url
            FROM paper_cache
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        out: list[Paper] = []
        for row in cur.fetchall():
            vc = row[5] or ""
            out.append(
                Paper(
                    paper_id=row[0] or "",
                    title=row[1] or "",
                    abstract=row[2] or "",
                    year=int(row[3] or 0),
                    venue=row[4] or "",
                    venue_candidates=[x for x in vc.split("|") if x],
                    doi=row[6] or "",
                    url=row[7] or "",
                )
            )
        return out

    def close(self) -> None:
        self.conn.close()
