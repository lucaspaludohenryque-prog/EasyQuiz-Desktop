"""
Módulo de Gestão do Cérebro - Mastering Study Quiz
Gerencia a persistência estruturada em pastas (Cerebro_Dados/Imagens_Contexto/{Categoria})
e arquivo JSON central (database_cerebro.json), com busca, cache e suporte a thumbnails.
"""

import os
import json
import hashlib
import re
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any, Tuple
from PIL import Image


def sanitize_folder_name(name: str) -> str:
    """Higieniza o nome da categoria para uso seguro como diretório no sistema de arquivos."""
    clean = re.sub(r'[^\w\s-]', '', name).strip()
    clean = re.sub(r'[-\s]+', '_', clean)
    return clean or "Outros"


@dataclass
class CerebroItem:
    """Modelo de dados de uma questão e elemento visual registrado no Cérebro."""
    id: int
    data_hora: str
    pergunta: str
    resposta_correta: str
    confianca: float
    possui_elemento_visual: bool
    categoria: str
    contexto_explicativo: str
    caminho_imagem: Optional[str]
    caminho_thumbnail: Optional[str]
    question_hash: str
    coordenadas_clique: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CerebroItem":
        return cls(
            id=data.get("id", 0),
            data_hora=data.get("data_hora", ""),
            pergunta=data.get("pergunta", ""),
            resposta_correta=data.get("resposta_correta", ""),
            confianca=float(data.get("confianca", 1.0)),
            possui_elemento_visual=bool(data.get("possui_elemento_visual", False)),
            categoria=data.get("categoria", "Texto Puro"),
            contexto_explicativo=data.get("contexto_explicativo", ""),
            caminho_imagem=data.get("caminho_imagem"),
            caminho_thumbnail=data.get("caminho_thumbnail"),
            question_hash=data.get("question_hash", ""),
            coordenadas_clique=data.get("coordenadas_clique", {"x": 0.0, "y": 0.0})
        )


class CerebroManager:
    """Controlador de dados físicos do Cérebro (JSON + Pastas de Imagens Categorizadas)."""

    CATEGORIAS_PADRAO = ["Gráfico", "Tabela", "Diagrama", "Fórmula", "Mapa", "Texto Puro", "Outros"]

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        self.base_dir = base_dir
        self.cerebro_dir = os.path.join(base_dir, "Cerebro_Dados")
        self.imagens_dir = os.path.join(self.cerebro_dir, "Imagens_Contexto")
        self.thumbs_dir = os.path.join(self.cerebro_dir, "Thumbnails")
        self.db_json_path = os.path.join(self.cerebro_dir, "database_cerebro.json")

        self._ensure_directories()
        self.itens: List[CerebroItem] = self._load_database()

    def _ensure_directories(self) -> None:
        """Cria as pastas estruturadas no disco se ainda não existirem."""
        os.makedirs(self.cerebro_dir, exist_ok=True)
        os.makedirs(self.imagens_dir, exist_ok=True)
        os.makedirs(self.thumbs_dir, exist_ok=True)

        for cat in self.CATEGORIAS_PADRAO:
            cat_folder = os.path.join(self.imagens_dir, sanitize_folder_name(cat))
            os.makedirs(cat_folder, exist_ok=True)

    def _load_database(self) -> List[CerebroItem]:
        """Carrega a base de dados JSON."""
        if not os.path.exists(self.db_json_path):
            return []
        try:
            with open(self.db_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [CerebroItem.from_dict(item) for item in data]
        except Exception as e:
            print(f"[CÉREBRO] Falha ao carregar database_cerebro.json: {e}")
            return []

    def _save_database(self) -> bool:
        """Salva a lista de itens no arquivo database_cerebro.json de forma atômica."""
        try:
            temp_path = self.db_json_path + ".tmp"
            data = [item.to_dict() for item in self.itens]
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            if os.path.exists(self.db_json_path):
                os.remove(self.db_json_path)
            os.rename(temp_path, self.db_json_path)
            return True
        except Exception as e:
            print(f"[CÉREBRO] Erro ao gravar database_cerebro.json: {e}")
            return False

    @staticmethod
    def compute_hash(text: str) -> str:
        """Normaliza enunciado para consulta de cache sem espaços ou caixa alta."""
        clean = "".join(text.lower().split())
        return hashlib.sha256(clean.encode("utf-8")).hexdigest()

    def find_cached_item(self, question_text: str) -> Optional[CerebroItem]:
        """Verifica se a questão já foi resolvida e registrada no Cérebro."""
        q_hash = self.compute_hash(question_text)
        for item in reversed(self.itens):
            if item.question_hash == q_hash:
                return item
        return None

    def add_item(
        self,
        pergunta: str,
        resposta: str,
        confianca: float,
        possui_elemento_visual: bool,
        categoria: str,
        contexto: str,
        imagem_recorte: Optional[Image.Image] = None,
        coordenadas_clique: Optional[Dict[str, float]] = None
    ) -> CerebroItem:
        """Armazena o recorte visual na subpasta da categoria e registra o item no JSON."""
        new_id = len(self.itens) + 1
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cat_clean = sanitize_folder_name(categoria)

        cat_folder = os.path.join(self.imagens_dir, cat_clean)
        os.makedirs(cat_folder, exist_ok=True)

        caminho_imagem: Optional[str] = None
        caminho_thumb: Optional[str] = None

        if imagem_recorte is not None:
            # Salva a imagem na pasta da respectiva categoria
            filename = f"img_{new_id:03d}_{cat_clean}.png"
            caminho_imagem = os.path.join(cat_folder, filename)
            imagem_recorte.save(caminho_imagem, format="PNG", optimize=True)

            # Gera thumbnail leve (240x160) para exibição fluida em alta velocidade na GUI
            thumb_filename = f"thumb_{new_id:03d}_{cat_clean}.png"
            caminho_thumb = os.path.join(self.thumbs_dir, thumb_filename)
            thumb = imagem_recorte.copy()
            thumb.thumbnail((260, 180), Image.Resampling.LANCZOS)
            thumb.save(caminho_thumb, format="PNG")

        item = CerebroItem(
            id=new_id,
            data_hora=now_str,
            pergunta=pergunta.strip(),
            resposta_correta=resposta.strip(),
            confianca=float(confianca),
            possui_elemento_visual=possui_elemento_visual,
            categoria=categoria.strip() or "Texto Puro",
            contexto_explicativo=contexto.strip(),
            caminho_imagem=caminho_imagem,
            caminho_thumbnail=caminho_thumb,
            question_hash=self.compute_hash(pergunta),
            coordenadas_clique=coordenadas_clique or {"x": 0.0, "y": 0.0}
        )

        self.itens.append(item)
        self._save_database()
        return item

    def search_items(
        self,
        query: str = "",
        categoria_filter: str = "Todos",
        apenas_com_imagem: bool = False
    ) -> List[CerebroItem]:
        """Filtra os itens da memória com base em pesquisa textual e categoria."""
        query_lower = query.lower().strip()
        results: List[CerebroItem] = []

        for item in reversed(self.itens):
            if categoria_filter not in ("Todos", "Todas", ""):
                if item.categoria.lower() != categoria_filter.lower():
                    continue

            if apenas_com_imagem and not item.possui_elemento_visual:
                continue

            if query_lower:
                match_text = (
                    query_lower in item.pergunta.lower() or
                    query_lower in item.contexto_explicativo.lower() or
                    query_lower in item.resposta_correta.lower() or
                    query_lower in item.categoria.lower()
                )
                if not match_text:
                    continue

            results.append(item)

        return results

    def get_all_categories(self) -> List[str]:
        """Lista todas as categorias distintas presentes nos registros do Cérebro."""
        cats = set(self.CATEGORIAS_PADRAO)
        for item in self.itens:
            if item.categoria:
                cats.add(item.categoria)
        return ["Todos"] + sorted(list(cats))

    def clear_cerebro(self) -> None:
        """Limpa a base de dados e apaga os arquivos de imagem associados."""
        self.itens = []
        self._save_database()
        try:
            for root, dirs, files in os.walk(self.imagens_dir):
                for f in files:
                    try:
                        os.remove(os.path.join(root, f))
                    except OSError:
                        pass
            for f in os.listdir(self.thumbs_dir):
                try:
                    os.remove(os.path.join(self.thumbs_dir, f))
                except OSError:
                    pass
        except Exception as e:
            print(f"[CÉREBRO] Erro ao limpar arquivos físicos: {e}")
