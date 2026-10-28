# Mastering Study Quiz Desktop

Software desktop para Windows desenvolvido em Python para automação inteligente de quizzes e provas online utilizando **Visão Computacional**, **Inteligência Artificial Multimodal** (Google Gemini e OpenAI) e **Automação RPA** com o sistema **"Cérebro"** (persistência em pastas locais e exibição em tempo real na interface).

---

## 🌟 Principais Recursos

1. **Tema Claro Padrão (Clean White):**
   - Interface moderna em modo claro minimalista com tipografia nítida e cantos arredondados.
   - Alternância instantânea (Switch) para **Modo Escuro (Dark Mode)** na barra lateral.

2. **Cérebro em Tempo Real (Live Monitor):**
   - Painel integrado no Dashboard que atualiza no mesmo instante em que a IA responde à questão.
   - Exibição da miniatura/recorte analisado com `CTkImage`.
   - **Etiqueta em Destaque:** `[ GRÁFICO ]`, `[ TABELA ]`, `[ DIAGRAMA ]`, `[ FÓRMULA ]`, `[ MAPA ]`, `[ TEXTO PURO ]`.
   - Explicação contextual resumida gerada pela IA e indicação visual da alternativa clicada.

3. **Explorar Cérebro (Galeria Interativa & Busca):**
   - Grade rolável com todos os cards históricos salvos no disco.
   - Barra de pesquisa textual em tempo real por palavras-chave ou matéria.
   - Filtros rápidos por botões de categoria (`Todos`, `Gráficos`, `Tabelas`, `Diagramas`, `Fórmulas`, `Texto`).
   - Modal com zoom e detalhes pedagógicos completos ao clicar no card.

4. **Armazenamento Físico Estruturado (`Cerebro_Dados`):**
   ```text
   📁 Mastering_Study_Quiz/
    ├── 🚀 MasteringStudyQuiz.exe
    ├── ⚙️ config.json
    └── 📁 Cerebro_Dados/
         ├── 📄 database_cerebro.json
         ├── 📁 Thumbnails/
         └── 📁 Imagens_Contexto/
              ├── 📁 Grafico/
              │    └── 🖼️ img_001_Grafico.png
              ├── 📁 Tabela/
              ├── 📁 Diagrama/
              ├── 📁 Formula/
              └── 📁 Outros/
   ```

5. **Automação Segura e Atalhos Globais:**
   - Calibração de área com tela translúcida (Sniper).
   - Mapeamento de coordenada X, Y do botão de avançar questão.
   - **`[F8]`**: Iniciar / Pausar.
   - **`[ESC]`**: Parada de Emergência Imediata (além do Failsafe nos cantos da tela via PyAutoGUI).

---

## ⚡ Instalação e Execução

### Pré-requisitos
- Python 3.11+
- Windows 10 ou 11 (com DPI scaling automático suportado)

### Instalação de Dependências
```bash
python -m pip install -r requirements.txt
```

### Executar em Desenvolvimento
```bash
python main.py
```

---

## 📦 Compilação para `.exe` Standalone

Para gerar o executável único independente:

```powershell
python build_exe.py
```

Ou comando direto PyInstaller:
```powershell
python -m PyInstaller --noconsole --onefile --clean --name "MasteringStudyQuiz" --collect-all customtkinter main.py
```

O arquivo final pronto para uso estará em: `dist\MasteringStudyQuiz.exe`.
