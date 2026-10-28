# EasyQuiz Desktop

Aplicação Windows independente desenvolvida para automação de resolução de quizzes e exames online utilizando **Visão Computacional**, **IA Multimodal** (Google Gemini / OpenAI) e **RPA (Robotic Process Automation)**.

---

## 🏗 Arquitetura do Projeto

```
Mastering Study Quiz/
│
├── main.py              # Ponto de entrada principal com DPI Awareness para Windows
├── gui.py               # Interface gráfica moderna em CustomTkinter (Dark Mode)
├── automation.py        # Motor de automação RPA (mss + PyAutoGUI) em Thread dedicada
├── ai_service.py        # Módulo de visão computacional multimodal com retorno JSON
├── overlay.py           # Sobreposições translúcidas (Sniper) para calibração de tela
├── config_manager.py    # Persistência segura de configurações locais em config.json
├── build_exe.py         # Script automatizado de compilação com PyInstaller
├── requirements.txt     # Dependências do ecossistema Python
└── README.md            # Documentação técnica e guia operacional
```

---

## ⚡ Instalação das Dependências

Instale os pacotes necessários executando no PowerShell ou Prompt de Comando:

```bash
python -m pip install -r requirements.txt
```

---

## 🚀 Como Executar em Modo de Desenvolvimento

```bash
python main.py
```

---

## 🎮 Guia Operacional e Calibração

1. **Configurar IA**:
   - Escolha o provedor (`Google Gemini` ou `OpenAI`).
   - Cole sua Chave de API no campo correspondente e clique em **"Salvar Configurações de IA"**.
2. **Calibrar Região do Quiz**:
   - Clique em **"🔍 Selecionar Área do Quiz"**.
   - A tela ficará escura em modo sniper. Clique e arraste o mouse cobrindo o quadrante onde aparecem o enunciado e as opções de resposta.
3. **Calibrar Botão de Avançar**:
   - Clique em **"🎯 Definir Botão Próximo"**.
   - Clique com o botão esquerdo exatamente sobre o botão "Avançar" / "Próxima Pergunta" do quiz.
4. **Iniciar Automação**:
   - Clique em **"▶ Iniciar"** na interface ou pressione a tecla **`F8`** no teclado.
   - Para pausar/retomar, pressione **`F8`**.
   - Para parada de emergência imediata, pressione **`ESC`** ou arraste o mouse para o canto superior esquerdo da tela (Failsafe do PyAutoGUI).

---

## 📦 Compilação do Executável (.exe)

Para gerar o arquivo executável standalone (arquivo único sem necessidade de Python instalado):

### Opção 1: Via script automatizado
```bash
python build_exe.py
```

### Opção 2: Comando direto do PyInstaller
```bash
python -m PyInstaller --noconsole --onefile --clean --name "EasyQuiz" --collect-all customtkinter main.py
```

O arquivo compilado final estará disponível no diretório:
`dist/EasyQuiz.exe`
