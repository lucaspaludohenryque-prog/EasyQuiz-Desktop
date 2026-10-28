"""
Script de Compilação Automatizada - EasyQuiz Desktop
Gera o executável standalone (.exe) com PyInstaller garantindo empacotamento completo dos assets.
"""

import subprocess
import sys
import os
import shutil


def build_executable():
    print("=" * 60)
    print("Iniciando compilação do EasyQuiz Desktop para Windows (.exe)")
    print("=" * 60)

    # Comando base do PyInstaller
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconsole",
        "--onefile",
        "--clean",
        "--name=EasyQuiz",
        "--collect-all=customtkinter",
        "main.py"
    ]

    print("\nExecutando comando:")
    print(" ".join(cmd))
    print("\nEmpacotando aplicação... Aguarde.\n")

    result = subprocess.run(cmd)

    if result.returncode == 0:
        exe_path = os.path.abspath(os.path.join("dist", "EasyQuiz.exe"))
        print("\n" + "=" * 60)
        print("✅ COMPILAÇÃO CONCLUÍDA COM SUCESSO!")
        print(f"Executável gerado em: {exe_path}")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ ERRO DURANTE A COMPILAÇÃO. Verifique as mensagens acima.")
        print("=" * 60)


if __name__ == "__main__":
    build_executable()
