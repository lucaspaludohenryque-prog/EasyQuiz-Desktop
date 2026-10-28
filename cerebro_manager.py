"""
Módulo de Gestão do Cérebro Físico - Mastering Study Quiz
Organiza a base de dados nas pastas locais:
- Cerebro_Dados/database_cerebro.json
- Cerebro_Dados/Sessoes_Contexto/questao_{id}/ (rationale.md, actions.json, resumo.txt, prompt-enviado.txt, metadados.json)
- Cerebro_Dados/Midia_Contextualizada/{Categoria}/
"""

import os
import json
import shutil
import zipfile
import hashlib
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any, Tuple
from PIL import Image


@dataclass
class QuestionSessionRecord:
    id: int
    data_hora: str
    pergunta: str
    resposta_correta: str
    rationale: str
    confianca: float
    possui_elemento_visual: bool
    categoria_imagem: str
    contexto_imagem: str
    caminho_imagem: Optional[str]
    coordenadas_clique: Dict[str, float]
    prompt_enviado: str
    rag_contexto: str
    modelo: str
    latencia_ms: int
    tokens_usados: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CerebroManager:
    """Gerenciador de arquivos físicos e indexador do Cérebro da IA."""

    CATEGORIAS = ["Grafico", "Tabela", "Diagrama", "Formula", "Mapa", "Outros"]

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        self.base_dir = base_dir
        self.cerebro_dir = os.path.join(base_dir, "Cerebro_Dados")
        self.db_json_path = os.path.join(self.cerebro_dir, "database_cerebro.json")
        self.sessoes_dir = os.path.join(self.cerebro_dir, "Sessoes_Contexto")
        self.midia_dir = os.path.join(self.cerebro_dir, "Midia_Contextualizada")

        self._ensure_folders()
        self.database: List[Dict[str, Any]] = self._load_database()
        self.current_session: Optional[QuestionSessionRecord] = None

    def _ensure_folders(self) -> None:
        os.makedirs(self.cerebro_dir, exist_ok=True)
        os.makedirs(self.sessoes_dir, exist_ok=True)
        os.makedirs(self.midia_dir, exist_ok=True)
        for cat in self.CATEGORIAS:
            os.makedirs(os.path.join(self.midia_dir, cat), exist_ok=True)

    def _load_database(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.db_json_path):
            return []
        try:
            with open(self.db_json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_database(self) -> None:
        try:
            temp = self.db_json_path + ".tmp"
            with open(temp, "w", encoding="utf-8") as f:
                json.dump(self.database, f, indent=4, ensure_ascii=False)
            if os.path.exists(self.db_json_path):
                os.remove(self.db_json_path)
            os.rename(temp, self.db_json_path)
        except Exception as e:
            print(f"[CÉREBRO] Falha ao gravar database_cerebro.json: {e}")

    @staticmethod
    def compute_hash(text: str) -> str:
        clean = "".join(text.lower().split())
        return hashlib.sha256(clean.encode("utf-8")).hexdigest()

    def find_cached_answer(self, question_text: str) -> Optional[Dict[str, Any]]:
        """Verifica se a questão já foi respondida anteriormente (Cache RAG)."""
        target_hash = self.compute_hash(question_text)
        for item in reversed(self.database):
            if item.get("hash") == target_hash:
                return item
        return None

    def get_rag_context(self, question_text: str) -> str:
        """Gera contexto a partir de resoluções similares no Cérebro para alimentar o prompt."""
        cached = self.find_cached_answer(question_text)
        if cached:
            return f"[MEMÓRIA CÉREBRO: Questão idêntica resolvida anteriormente. Resposta correta: '{cached.get('resposta')}' | Categoria: {cached.get('categoria')}]."
        # Busca por palavras-chave relevantes
        words = [w.lower() for w in question_text.split() if len(w) > 4]
        matches = []
        for item in reversed(self.database[-10:]):
            p = item.get("pergunta", "").lower()
            if any(w in p for w in words[:3]):
                matches.append(f"- Questão anterior: '{item.get('pergunta')[:60]}...' -> Resposta: '{item.get('resposta')}' ({item.get('categoria')})")
        if matches:
            return "[MEMÓRIA CÉREBRO: Tópicos relacionados identificados na base local]:\n" + "\n".join(matches[:2])
        return "[MEMÓRIA CÉREBRO: Nenhum registro similar anterior encontrado na base local]."

    def record_question_session(
        self,
        pergunta: str,
        resposta: str,
        rationale: str,
        confianca: float,
        possui_elemento_visual: bool,
        categoria: str,
        contexto_imagem: str,
        imagem_recorte: Optional[Image.Image],
        coordenadas_clique: Dict[str, float],
        prompt_enviado: str,
        rag_contexto: str,
        modelo: str,
        latencia_ms: int,
        tokens_usados: int
    ) -> QuestionSessionRecord:
        """Salva a questão completa nas pastas de sessões, grava os arquivos físicos e indexa no JSON."""
        new_id = len(self.database) + 1
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. Pasta da Sessão: Sessoes_Contexto/questao_{id:03d}/
        sessao_pasta = os.path.join(self.sessoes_dir, f"questao_{new_id:03d}")
        os.makedirs(sessao_pasta, exist_ok=True)

        # rationale.md
        with open(os.path.join(sessao_pasta, "rationale.md"), "w", encoding="utf-8") as f:
            f.write(f"# Raciocínio da IA - Questão #{new_id}\n\n")
            f.write(f"**Data/Hora:** {now_str}\n")
            f.write(f"**Alternativa Selecionada:** {resposta}\n")
            f.write(f"**Confiança:** {confianca*100:.1f}%\n\n")
            f.write(f"## Justificativa Passo a Passo\n{rationale}\n")

        # actions.json
        actions_data = {
            "questao_id": new_id,
            "timestamp": now_str,
            "acao": "click_alternativa",
            "coordenadas": coordenadas_clique,
            "alternativa": resposta
        }
        with open(os.path.join(sessao_pasta, "actions.json"), "w", encoding="utf-8") as f:
            json.dump(actions_data, f, indent=4, ensure_ascii=False)

        # resumo.txt
        with open(os.path.join(sessao_pasta, "resumo.txt"), "w", encoding="utf-8") as f:
            f.write(f"ENUNCIADO: {pergunta}\nRESPOSTA: {resposta}\nCATEGORIA: {categoria}\n")

        # prompt-enviado.txt
        with open(os.path.join(sessao_pasta, "prompt-enviado.txt"), "w", encoding="utf-8") as f:
            f.write(prompt_enviado)

        # rag-context.txt
        with open(os.path.join(sessao_pasta, "rag-context.txt"), "w", encoding="utf-8") as f:
            f.write(rag_contexto)

        # Metadados
        with open(os.path.join(sessao_pasta, "modelo.info"), "w", encoding="utf-8") as f:
            f.write(f"Modelo: {modelo}")
        with open(os.path.join(sessao_pasta, "latencia.info"), "w", encoding="utf-8") as f:
            f.write(f"Latência da API: {latencia_ms} ms")
        with open(os.path.join(sessao_pasta, "tokens.info"), "w", encoding="utf-8") as f:
            f.write(f"Tokens Consumidos: {tokens_usados}")

        # 2. Pasta de Mídia: Midia_Contextualizada/{Categoria}/
        caminho_imagem = None
        if imagem_recorte is not None:
            cat_safe = categoria if categoria in self.CATEGORIAS else "Outros"
            nome_img = f"{cat_safe}_{new_id:03d}.png"
            caminho_imagem = os.path.join(self.midia_dir, cat_safe, nome_img)
            imagem_recorte.save(caminho_imagem, format="PNG")

            # Salva também um descritivo de contexto ao lado da imagem
            desc_path = os.path.join(self.midia_dir, cat_safe, f"{cat_safe}_{new_id:03d}_contexto.txt")
            with open(desc_path, "w", encoding="utf-8") as f:
                f.write(f"ENUNCIADO: {pergunta}\nCONTEXTO VISUAL: {contexto_imagem}\nRESPOSTA: {resposta}")

        # 3. Registro no índice database_cerebro.json
        record = QuestionSessionRecord(
            id=new_id,
            data_hora=now_str,
            pergunta=pergunta,
            resposta_correta=resposta,
            rationale=rationale,
            confianca=confianca,
            possui_elemento_visual=possui_elemento_visual,
            categoria_imagem=categoria,
            contexto_imagem=contexto_imagem,
            caminho_imagem=caminho_imagem,
            coordenadas_clique=coordenadas_clique,
            prompt_enviado=prompt_enviado,
            rag_contexto=rag_contexto,
            modelo=modelo,
            latencia_ms=latencia_ms,
            tokens_usados=tokens_usados
        )
        self.current_session = record

        index_entry = {
            "id": new_id,
            "data_hora": now_str,
            "hash": self.compute_hash(pergunta),
            "pergunta": pergunta,
            "resposta": resposta,
            "categoria": categoria,
            "contexto_imagem": contexto_imagem,
            "caminho_imagem": caminho_imagem,
            "pasta_sessao": sessao_pasta,
            "modelo": modelo,
            "latencia_ms": latencia_ms,
            "tokens": tokens_usados
        }
        self.database.append(index_entry)
        self._save_database()

        return record

    def get_latest_session_files(self) -> Dict[str, str]:
        """Retorna caminhos de arquivos da última questão para exibição na árvore da GUI."""
        if not self.database:
            return {}
        last = self.database[-1]
        sess_dir = last.get("pasta_sessao", "")
        if not os.path.exists(sess_dir):
            return {}
        return {
            "rationale": os.path.join(sess_dir, "rationale.md"),
            "actions": os.path.join(sess_dir, "actions.json"),
            "resumo": os.path.join(sess_dir, "resumo.txt"),
            "prompt": os.path.join(sess_dir, "prompt-enviado.txt"),
            "rag": os.path.join(sess_dir, "rag-context.txt"),
            "modelo": os.path.join(sess_dir, "modelo.info"),
            "latencia": os.path.join(sess_dir, "latencia.info"),
            "tokens": os.path.join(sess_dir, "tokens.info"),
            "imagem": last.get("caminho_imagem", "")
        }

    def list_all_media_items(self) -> List[Dict[str, str]]:
        """Lista todas as imagens salvas na pasta Midia_Contextualizada com label e contexto."""
        items = []
        for cat in self.CATEGORIAS:
            folder = os.path.join(self.midia_dir, cat)
            if not os.path.exists(folder):
                continue
            for f in sorted(os.listdir(folder)):
                if f.endswith(".png"):
                    full_p = os.path.join(folder, f)
                    desc_p = full_p.replace(".png", "_contexto.txt")
                    desc_text = cat
                    if os.path.exists(desc_p):
                        try:
                            with open(desc_p, "r", encoding="utf-8") as df:
                                lines = df.readlines()
                                for line in lines:
                                    if line.startswith("CONTEXTO VISUAL:"):
                                        desc_text = line.replace("CONTEXTO VISUAL:", "").strip()
                                        break
                        except Exception:
                            pass
                    items.append({
                        "filename": f,
                        "category": cat,
                        "path": full_p,
                        "label": f"{f} - \"{desc_text[:35]}...\""
                    })
        return items

    def read_file_safe(self, file_path: str) -> str:
        """Lê com segurança o conteúdo de um arquivo de texto das sessões do Cérebro."""
        if not file_path or not os.path.exists(file_path):
            return "[Arquivo não encontrado ou ainda não gerado nesta sessão.]"
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception as e:
            return f"[Erro ao ler arquivo: {e}]"

    def export_cerebro_zip(self, dest_zip_path: str) -> bool:
        """Gera um arquivo .zip com toda a estrutura física de Cerebro_Dados."""
        try:
            with zipfile.ZipFile(dest_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(self.cerebro_dir):
                    for file in files:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, self.cerebro_dir)
                        zipf.write(full_path, arcname=rel_path)
            return True
        except Exception as e:
            print(f"[CÉREBRO] Falha ao exportar zip: {e}")
            return False

    def clear_all_data(self) -> None:
        """Limpa todo o histórico e apaga todas as sessões e mídias físicas."""
        self.database = []
        self._save_database()
        try:
            shutil.rmtree(self.sessoes_dir, ignore_errors=True)
            shutil.rmtree(self.midia_dir, ignore_errors=True)
            self._ensure_folders()
        except Exception as e:
            print(f"[CÉREBRO] Erro ao limpar dados físicos: {e}")
