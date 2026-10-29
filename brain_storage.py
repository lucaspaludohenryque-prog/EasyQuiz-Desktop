"""
Módulo de Armazenamento Físico e Memória RAG - Mastering Study Quiz
Gerencia a pasta física 'Cerebro_Dados/', a persistência em sessões isoladas,
a categorização de mídias contextuais e a Memória RAG Local (Zero Tokens).
"""

import os
import json
import shutil
import zipfile
import hashlib
import re
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional, Tuple, Callable
from PIL import Image


@dataclass
class QuestionSessionRecord:
    """Registro estruturado de uma sessão de resolução do Cérebro."""
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
    image_hash: Optional[str]
    question_hash: str
    coordenadas_clique: Dict[str, Any]
    prompt_enviado: str
    rag_contexto: str
    modelo: str
    latencia_ms: int
    tokens_usados: int
    tipo_questao: str = "multipla_escolha"
    is_rag_cache: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BrainStorage:
    """
    Gerencia a pasta física Cerebro_Dados, indexação local e recuperação RAG de Zero Tokens.
    """

    CATEGORIAS_VALIDAS = ["Grafico", "Tabela", "Diagrama", "Formula", "Mapa", "Outros"]

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
        else:
            self.base_dir = os.path.abspath(base_dir)

        # Estrutura de Diretórios Físicos
        self.cerebro_dir = os.path.join(self.base_dir, "Cerebro_Dados")
        self.sessoes_dir = os.path.join(self.cerebro_dir, "Sessoes_Contexto")
        self.midia_dir = os.path.join(self.cerebro_dir, "Midia_Contextualizada")
        self.db_file = os.path.join(self.cerebro_dir, "database_cerebro.json")

        self.current_session: Optional[QuestionSessionRecord] = None
        self.database: List[Dict[str, Any]] = []
        self._listeners: List[Callable[[QuestionSessionRecord], None]] = []

        self._ensure_folders()
        self._load_database()

    def _ensure_folders(self) -> None:
        """Garante a criação de todas as pastas físicas do Cérebro."""
        os.makedirs(self.cerebro_dir, exist_ok=True)
        os.makedirs(self.sessoes_dir, exist_ok=True)
        os.makedirs(self.midia_dir, exist_ok=True)

        for cat in self.CATEGORIAS_VALIDAS:
            os.makedirs(os.path.join(self.midia_dir, cat), exist_ok=True)

    def _load_database(self) -> None:
        """Carrega o índice JSON mestre."""
        if not os.path.exists(self.db_file):
            self.database = []
            self._save_database()
            return

        try:
            with open(self.db_file, "r", encoding="utf-8") as f:
                self.database = json.load(f)
        except Exception as e:
            print(f"[CÉREBRO] Aviso ao carregar database_cerebro.json ({e}). Reiniciando índice.")
            self.database = []
            self._save_database()

    def _save_database(self) -> None:
        """Salva o índice JSON mestre atomicamente."""
        try:
            temp_path = self.db_file + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self.database, f, indent=4, ensure_ascii=False)
            if os.path.exists(self.db_file):
                os.remove(self.db_file)
            os.rename(temp_path, self.db_file)
        except Exception as e:
            print(f"[CÉREBRO] Erro ao salvar database_cerebro.json: {e}")

    def register_listener(self, callback: Callable[[QuestionSessionRecord], None]) -> None:
        """Registra callback para atualização ao vivo da GUI (TELA 2 - Cérebro)."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    # =========================================================================
    # Algoritmos de Hashing (Texto + Visão Perceptual)
    # =========================================================================
    @staticmethod
    def normalize_text(text: str) -> str:
        """Normaliza o texto da questão para comparação invariante."""
        if not text:
            return ""
        clean = text.lower()
        clean = re.sub(r"[^a-z0-9áéíóúãõçâêîôû]", " ", clean)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    @classmethod
    def compute_text_hash(cls, text: str) -> str:
        """Gera hash SHA-256 normalizado do texto da questão."""
        normalized = cls.normalize_text(text)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_image_dhash(image: Optional[Image.Image]) -> Optional[str]:
        """
        Calcula o hash perceptual de diferença (dHash de 64 bits) para imagens.
        Resiste a pequenas variações de redimensionamento e compressão.
        """
        if image is None:
            return None
        try:
            # Converte para tons de cinza e redimensiona para 9x8
            gray = image.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
            pixels = list(gray.getdata())
            # Compara pixel esquerdo com pixel direito
            diff_bits = []
            for row in range(8):
                row_start = row * 9
                for col in range(8):
                    left = pixels[row_start + col]
                    right = pixels[row_start + col + 1]
                    diff_bits.append(1 if left > right else 0)

            # Converte 64 bits para representação hexadecimal de 16 caracteres
            decimal_val = 0
            for bit in diff_bits:
                decimal_val = (decimal_val << 1) | bit
            return f"{decimal_val:016x}"
        except Exception as e:
            print(f"[CÉREBRO] Erro ao calcular dHash: {e}")
            return None

    @staticmethod
    def hamming_distance(hash1: Optional[str], hash2: Optional[str]) -> int:
        """Calcula a distância de Hamming entre dois hashes hexadecimais de 64 bits."""
        if not hash1 or not hash2 or len(hash1) != len(hash2):
            return 999
        try:
            val1 = int(hash1, 16)
            val2 = int(hash2, 16)
            xor_val = val1 ^ val2
            return bin(xor_val).count("1")
        except Exception:
            return 999

    # =========================================================================
    # Memória RAG Local (Consumo Zero de Tokens)
    # =========================================================================
    def lookup_rag(
        self,
        question_text: str,
        question_image: Optional[Image.Image] = None,
        max_image_hamming: int = 4
    ) -> Optional[Dict[str, Any]]:
        """
        Consulta a memória local do Cérebro antes de chamar a API da IA.
        Se a questão ou o gráfico já foi resolvido antes, recupera a resposta
        em ~0.1s com ZERO consumo de tokens.
        """
        if not self.database:
            return None

        q_norm = self.normalize_text(question_text)
        q_hash = self.compute_text_hash(question_text) if len(q_norm) > 15 else ""
        img_hash = self.compute_image_dhash(question_image) if question_image else None

        # 1. Correspondência exata por hash de texto (questões com texto representativo)
        if q_hash:
            for entry in reversed(self.database):
                if entry.get("question_hash") == q_hash:
                    cached_entry = entry.copy()
                    cached_entry["is_rag_cache"] = True
                    cached_entry["tokens_usados"] = 0
                    print(f"[RAG ZERO-TOKEN] Questão idêntica identificada no Cérebro (ID #{entry.get('id')})! Resposta recuperada em 0.1s sem chamada de API.")
                    return cached_entry

        # 2. Correspondência por similaridade de hash visual (questões com gráficos/diagramas)
        if img_hash:
            for entry in reversed(self.database):
                entry_img_hash = entry.get("image_hash")
                if entry_img_hash:
                    dist = self.hamming_distance(img_hash, entry_img_hash)
                    if dist <= max_image_hamming:
                        # Se também houver similaridade razoável no texto ou imagem muito próxima
                        cached_entry = entry.copy()
                        cached_entry["is_rag_cache"] = True
                        cached_entry["tokens_usados"] = 0
                        print(f"[RAG ZERO-TOKEN] Elemento visual correspondente (Distância={dist}) encontrado no Cérebro (ID #{entry.get('id')})! Zero tokens.")
                        return cached_entry

        return None

    # =========================================================================
    # Persistência de Sessão e Geração de Arquivos Físicos
    # =========================================================================
    def save_session(
        self,
        pergunta: str,
        resposta: str,
        rationale: str,
        confianca: float,
        categoria: str,
        contexto_imagem: str,
        imagem_recorte: Optional[Image.Image] = None,
        coordenadas_clique: Optional[Dict[str, Any]] = None,
        prompt_enviado: str = "",
        rag_contexto: str = "",
        modelo: str = "gemini-2.5-flash",
        latencia_ms: int = 0,
        tokens_usados: int = 0,
        tipo_questao: str = "multipla_escolha",
        texto_digitado: Optional[str] = None
    ) -> QuestionSessionRecord:
        """
        Salva a questão completa na pasta física Cerebro_Dados/ gerando:
        - rationale.md
        - actions.json
        - resumo.txt
        - prompt-enviado.txt
        - rag-context.txt
        - modelo.info
        - latencia.info
        - tokens.info
        - Imagem categorizada em Midia_Contextualizada/{cat}/
        """
        new_id = len(self.database) + 1
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        q_hash = self.compute_text_hash(pergunta)
        img_hash = self.compute_image_dhash(imagem_recorte) if imagem_recorte else None

        # 1. Pasta isolada da sessão: Sessoes_Contexto/questao_{id:03d}/
        sessao_pasta = os.path.join(self.sessoes_dir, f"questao_{new_id:03d}")
        os.makedirs(sessao_pasta, exist_ok=True)

        # rationale.md
        with open(os.path.join(sessao_pasta, "rationale.md"), "w", encoding="utf-8") as f:
            f.write(f"# Raciocínio da IA - Questão #{new_id:03d}\n\n")
            f.write(f"- **Data/Hora:** {now_str}\n")
            f.write(f"- **Alternativa / Resposta:** {resposta}\n")
            f.write(f"- **Confiança:** {confianca * 100:.1f}%\n")
            f.write(f"- **Modelo:** {modelo}\n")
            f.write(f"- **Tipo de Questão:** {tipo_questao}\n\n")
            f.write("## Justificativa Passo a Passo\n\n")
            f.write(f"{rationale}\n")

        # actions.json
        actions_data = {
            "questao_id": new_id,
            "timestamp": now_str,
            "tipo_questao": tipo_questao,
            "acao": "digitar_texto" if tipo_questao == "discursiva" else "click_alternativa",
            "coordenadas": coordenadas_clique or {},
            "alternativa_selecionada": resposta,
            "texto_digitado": texto_digitado or resposta if tipo_questao == "discursiva" else None
        }
        with open(os.path.join(sessao_pasta, "actions.json"), "w", encoding="utf-8") as f:
            json.dump(actions_data, f, indent=4, ensure_ascii=False)

        # resumo.txt
        with open(os.path.join(sessao_pasta, "resumo.txt"), "w", encoding="utf-8") as f:
            f.write(f"ENUNCIADO: {pergunta}\n")
            f.write(f"RESPOSTA: {resposta}\n")
            f.write(f"CATEGORIA: {categoria}\n")
            f.write(f"CONFIANCA: {confianca * 100:.1f}%\n")

        # prompt-enviado.txt
        with open(os.path.join(sessao_pasta, "prompt-enviado.txt"), "w", encoding="utf-8") as f:
            f.write(prompt_enviado if prompt_enviado else "[Prompt padrão do sistema]")

        # rag-context.txt
        with open(os.path.join(sessao_pasta, "rag-context.txt"), "w", encoding="utf-8") as f:
            f.write(rag_contexto if rag_contexto else "[Nenhum contexto prévio injetado]")

        # Arquivos de metadados .info
        with open(os.path.join(sessao_pasta, "modelo.info"), "w", encoding="utf-8") as f:
            f.write(f"Modelo de IA: {modelo}")

        with open(os.path.join(sessao_pasta, "latencia.info"), "w", encoding="utf-8") as f:
            f.write(f"Latência da Resolução: {latencia_ms} ms")

        with open(os.path.join(sessao_pasta, "tokens.info"), "w", encoding="utf-8") as f:
            if tokens_usados == 0:
                f.write("Tokens Consumidos: 0 (Memória RAG Local / Zero Tokens)")
            else:
                f.write(f"Tokens Consumidos: {tokens_usados}")

        # 2. Imagem em Midia_Contextualizada/{cat}/
        caminho_imagem = None
        cat_sanitizada = categoria.replace("[", "").replace("]", "").strip()
        if cat_sanitizada not in self.CATEGORIAS_VALIDAS:
            cat_sanitizada = "Outros"

        if imagem_recorte is not None:
            nome_img = f"{cat_sanitizada}_{new_id:03d}.png"
            caminho_imagem = os.path.join(self.midia_dir, cat_sanitizada, nome_img)
            imagem_recorte.save(caminho_imagem, format="PNG")

            desc_path = os.path.join(self.midia_dir, cat_sanitizada, f"{cat_sanitizada}_{new_id:03d}_contexto.txt")
            with open(desc_path, "w", encoding="utf-8") as f:
                f.write(f"ENUNCIADO: {pergunta}\n")
                f.write(f"ETIQUETA: [ {cat_sanitizada.upper()} ]\n")
                f.write(f"CONTEXTO VISUAL: {contexto_imagem}\n")
                f.write(f"RESPOSTA: {resposta}\n")

        # 3. Criação do Registro de Sessão e Atualização do Índice
        record = QuestionSessionRecord(
            id=new_id,
            data_hora=now_str,
            pergunta=pergunta,
            resposta_correta=resposta,
            rationale=rationale,
            confianca=confianca,
            possui_elemento_visual=bool(imagem_recorte is not None),
            categoria_imagem=categoria,
            contexto_imagem=contexto_imagem,
            caminho_imagem=caminho_imagem,
            image_hash=img_hash,
            question_hash=q_hash,
            coordenadas_clique=coordenadas_clique or {},
            prompt_enviado=prompt_enviado,
            rag_contexto=rag_contexto,
            modelo=modelo,
            latencia_ms=latencia_ms,
            tokens_usados=tokens_usados,
            tipo_questao=tipo_questao,
            is_rag_cache=(tokens_usados == 0)
        )
        self.current_session = record

        index_entry = {
            "id": new_id,
            "data_hora": now_str,
            "pergunta": pergunta,
            "resposta": resposta,
            "categoria": categoria,
            "contexto_imagem": contexto_imagem,
            "caminho_imagem": caminho_imagem,
            "pasta_sessao": sessao_pasta,
            "question_hash": q_hash,
            "image_hash": img_hash,
            "modelo": modelo,
            "latencia_ms": latencia_ms,
            "tokens_usados": tokens_usados,
            "tipo_questao": tipo_questao
        }
        self.database.append(index_entry)
        self._save_database()

        # Notifica listeners da UI
        for listener in self._listeners:
            try:
                listener(record)
            except Exception as e:
                print(f"[CÉREBRO] Falha ao notificar listener: {e}")

        return record

    # =========================================================================
    # Consultas para a Interface Gráfica (TELA 2 - Cérebro da IA)
    # =========================================================================
    def get_latest_session_record(self) -> Optional[QuestionSessionRecord]:
        return self.current_session

    def get_latest_session_files(self) -> Dict[str, str]:
        """Retorna os caminhos dos 8 arquivos físicos da última sessão para a árvore de arquivos."""
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
            "imagem": last.get("caminho_imagem") or ""
        }

    def list_all_media_items(self) -> List[Dict[str, Any]]:
        """Lista todas as mídias físicas salvas na pasta Midia_Contextualizada."""
        items = []
        for cat in self.CATEGORIAS_VALIDAS:
            folder = os.path.join(self.midia_dir, cat)
            if not os.path.exists(folder):
                continue
            for f in sorted(os.listdir(folder)):
                if f.endswith(".png"):
                    full_p = os.path.join(folder, f)
                    desc_p = full_p.replace(".png", "_contexto.txt")
                    desc_text = cat
                    enunciado = ""
                    if os.path.exists(desc_p):
                        try:
                            with open(desc_p, "r", encoding="utf-8") as df:
                                for line in df:
                                    if line.startswith("CONTEXTO VISUAL:"):
                                        desc_text = line.replace("CONTEXTO VISUAL:", "").strip()
                                    elif line.startswith("ENUNCIADO:"):
                                        enunciado = line.replace("ENUNCIADO:", "").strip()
                        except Exception:
                            pass

                    items.append({
                        "filename": f,
                        "category": cat,
                        "path": full_p,
                        "label": f"{f} - [{desc_text[:35]}...]",
                        "context": desc_text,
                        "enunciado": enunciado
                    })
        return items

    def read_file_safe(self, file_path: str) -> str:
        """Lê um arquivo de texto com proteção contra erros e codificação segura."""
        if not file_path or not os.path.exists(file_path):
            return "[Arquivo não encontrado ou ainda não gerado nesta sessão.]"
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception as e:
            return f"[Erro ao ler arquivo: {e}]"

    def export_cerebro_zip(self, dest_zip_path: str) -> bool:
        """Compacta toda a estrutura física Cerebro_Dados/ em um arquivo .zip."""
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
        """Limpa todas as sessões físicas e o índice do Cérebro."""
        self.database = []
        self._save_database()
        try:
            shutil.rmtree(self.sessoes_dir, ignore_errors=True)
            shutil.rmtree(self.midia_dir, ignore_errors=True)
            self._ensure_folders()
            self.current_session = None
            print("[CÉREBRO] Todos os dados físicos e memória foram limpos.")
        except Exception as e:
            print(f"[CÉREBRO] Erro ao limpar dados físicos: {e}")


# Alias de compatibilidade com versões legadas
CerebroManager = BrainStorage
