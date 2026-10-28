"""
Módulo de Banco de Dados e Armazenamento Local - Cérebro (Mastering Study Quiz)
Gerencia a persistência em SQLite3, cache de resoluções, armazenamento de recortes visuais e filtros de busca.
"""

import os
import sqlite3
import hashlib
import uuid
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any, Tuple
from PIL import Image


@dataclass
class BrainMemory:
    """Representação estruturada de um registro de conhecimento no Cérebro."""
    id: Optional[int]
    created_at: str
    question_text: str
    chosen_answer: str
    confidence: float
    has_visual_element: bool
    image_category: str
    image_context: str
    image_path: Optional[str]
    image_hash: Optional[str]
    question_hash: str
    click_x: float
    click_y: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BrainDatabase:
    """Gerenciador central do Banco de Dados SQLite e storage de recortes do Cérebro."""

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        self.storage_dir = os.path.join(base_dir, "brain_storage")
        self.images_dir = os.path.join(self.storage_dir, "images")
        self.db_path = os.path.join(self.storage_dir, "brain.db")

        # Criação dos diretórios locais
        os.makedirs(self.images_dir, exist_ok=True)

        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Cria e retorna uma conexão SQLite configurada com WAL mode e row factory."""
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_database(self) -> None:
        """Cria as tabelas e índices necessários caso ainda não existam."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS brain_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    question_text TEXT NOT NULL,
                    chosen_answer TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    has_visual_element INTEGER NOT NULL DEFAULT 0,
                    image_category TEXT NOT NULL DEFAULT 'Texto Puro',
                    image_context TEXT NOT NULL DEFAULT '',
                    image_path TEXT,
                    image_hash TEXT,
                    question_hash TEXT NOT NULL,
                    click_x REAL NOT NULL DEFAULT 0.0,
                    click_y REAL NOT NULL DEFAULT 0.0
                );
            """)

            # Índices para aceleração de buscas e cache
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_question_hash ON brain_memory(question_hash);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_image_category ON brain_memory(image_category);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_has_visual ON brain_memory(has_visual_element);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON brain_memory(created_at DESC);")
            conn.commit()

    @staticmethod
    def compute_text_hash(text: str) -> str:
        """Gera um hash SHA-256 normalizado do enunciado para detecção rápida de duplicidade."""
        normalized = "".join(text.lower().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_image_hash(image: Image.Image) -> str:
        """Calcula o hash perceptual simplificado/MD5 dos pixels da imagem."""
        img_resized = image.resize((64, 64)).convert("L")
        return hashlib.md5(img_resized.tobytes()).hexdigest()

    def save_memory(
        self,
        question_text: str,
        chosen_answer: str,
        confidence: float,
        has_visual_element: bool,
        image_category: str,
        image_context: str,
        cropped_image: Optional[Image.Image] = None,
        click_x: float = 0.0,
        click_y: float = 0.0
    ) -> BrainMemory:
        """Persiste uma nova questão resolvida e seu recorte visual no banco de dados."""
        now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        q_hash = self.compute_text_hash(question_text)

        image_path: Optional[str] = None
        img_hash: Optional[str] = None

        # Salva o arquivo de imagem recortado se houver elemento visual relevante
        if has_visual_element and cropped_image is not None:
            filename = f"brain_{uuid.uuid4().hex[:12]}.png"
            image_path = os.path.join(self.images_dir, filename)
            cropped_image.save(image_path, format="PNG", optimize=True)
            img_hash = self.compute_image_hash(cropped_image)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO brain_memory (
                    created_at, question_text, chosen_answer, confidence,
                    has_visual_element, image_category, image_context,
                    image_path, image_hash, question_hash, click_x, click_y
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                now_iso,
                question_text.strip(),
                chosen_answer.strip(),
                float(confidence),
                1 if has_visual_element else 0,
                image_category.strip() or "Texto Puro",
                image_context.strip(),
                image_path,
                img_hash,
                q_hash,
                float(click_x),
                float(click_y)
            ))
            row_id = cursor.lastrowid
            conn.commit()

        return BrainMemory(
            id=row_id,
            created_at=now_iso,
            question_text=question_text.strip(),
            chosen_answer=chosen_answer.strip(),
            confidence=confidence,
            has_visual_element=has_visual_element,
            image_category=image_category.strip() or "Texto Puro",
            image_context=image_context.strip(),
            image_path=image_path,
            image_hash=img_hash,
            question_hash=q_hash,
            click_x=click_x,
            click_y=click_y
        )

    def find_cached_question(self, question_text: str) -> Optional[BrainMemory]:
        """Consulta o Cérebro para reutilizar resolução de questões já analisadas anteriormente."""
        q_hash = self.compute_text_hash(question_text)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM brain_memory
                WHERE question_hash = ?
                ORDER BY id DESC
                LIMIT 1
            """, (q_hash,))
            row = cursor.fetchone()
            if row:
                return self._row_to_memory(row)
        return None

    def search_memories(
        self,
        query: str = "",
        category_filter: Optional[str] = None,
        only_with_images: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[BrainMemory]:
        """Busca questões no Cérebro com suporte a filtro de categoria, palavras-chave e paginação."""
        sql_parts = ["SELECT * FROM brain_memory WHERE 1=1"]
        params: List[Any] = []

        if query.strip():
            sql_parts.append("AND (question_text LIKE ? OR image_context LIKE ? OR chosen_answer LIKE ?)")
            wildcard = f"%{query.strip()}%"
            params.extend([wildcard, wildcard, wildcard])

        if category_filter and category_filter != "Todas":
            sql_parts.append("AND image_category = ?")
            params.append(category_filter)

        if only_with_images:
            sql_parts.append("AND has_visual_element = 1")

        sql_parts.append("ORDER BY id DESC LIMIT ? OFFSET ?")
        params.extend([limit, offset])

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(" ".join(sql_parts), params)
            rows = cursor.fetchall()
            return [self._row_to_memory(r) for r in rows]

    def get_distinct_categories(self) -> List[str]:
        """Retorna todas as categorias únicas de elementos visuais já categorizados pela IA."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT image_category FROM brain_memory
                WHERE image_category IS NOT NULL AND image_category != ''
                ORDER BY image_category ASC
            """)
            return [row["image_category"] for row in cursor.fetchall()]

    def get_statistics(self) -> Dict[str, Any]:
        """Gera métricas agregadas da base de conhecimento do Cérebro."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total FROM brain_memory")
            total = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) as with_visual FROM brain_memory WHERE has_visual_element = 1")
            with_visual = cursor.fetchone()["with_visual"]

            cursor.execute("""
                SELECT image_category, COUNT(*) as count
                FROM brain_memory
                GROUP BY image_category
                ORDER BY count DESC
            """)
            category_distribution = {row["image_category"]: row["count"] for row in cursor.fetchall()}

        return {
            "total_questions": total,
            "visual_elements_count": with_visual,
            "categories": category_distribution
        }

    def delete_memory(self, memory_id: int) -> bool:
        """Remove um registro do Cérebro e expurga o arquivo de imagem associado."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT image_path FROM brain_memory WHERE id = ?", (memory_id,))
            row = cursor.fetchone()
            if not row:
                return False

            img_path = row["image_path"]
            if img_path and os.path.exists(img_path):
                try:
                    os.remove(img_path)
                except OSError:
                    pass

            cursor.execute("DELETE FROM brain_memory WHERE id = ?", (memory_id,))
            conn.commit()
            return True

    def clear_brain(self) -> None:
        """Limpa completamente a base do Cérebro e apaga todas as imagens locais."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT image_path FROM brain_memory WHERE image_path IS NOT NULL")
            rows = cursor.fetchall()
            for r in rows:
                p = r["image_path"]
                if p and os.path.exists(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass
            cursor.execute("DELETE FROM brain_memory")
            conn.commit()

    @staticmethod
    def _row_to_memory(row: sqlite3.Row) -> BrainMemory:
        return BrainMemory(
            id=row["id"],
            created_at=row["created_at"],
            question_text=row["question_text"],
            chosen_answer=row["chosen_answer"],
            confidence=row["confidence"],
            has_visual_element=bool(row["has_visual_element"]),
            image_category=row["image_category"],
            image_context=row["image_context"],
            image_path=row["image_path"],
            image_hash=row["image_hash"],
            question_hash=row["question_hash"],
            click_x=row["click_x"],
            click_y=row["click_y"]
        )
