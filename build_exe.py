"""
Script de Compilação Automatizada - Mastering Study Quiz
Empacota a aplicação em um executável (.exe) único com assets e customtkinter.
"""

import subprocess
import sys
import os


def build_executable():
    print("=" * 65)
    print("Iniciando compilação do Mastering Study Quiz para Windows (.exe)")
    print("=" * 65)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconsole",
        "--onefile",
        "--clean",
        "--name=MasteringStudyQuiz",
        "--collect-all=customtkinter",
        "main.py"
    ]

    print("\nExecutando comando:")
    print(" ".join(cmd))
    print("\nEmpacotando aplicação... Aguarde.\n")

    result = subprocess.run(cmd)

    if result.returncode == 0:
        exe_path = os.path.abspath(os.path.join("dist", "MasteringStudyQuiz.exe"))
        print("\n" + "=" * 65)
        print("✅ COMPILAÇÃO CONCLUÍDA COM SUCESSO!")
        print(f"Executável final gerado em: {exe_path}")
        print("=" * 65)
    else:
        print("\n" + "=" * 65)
        print("❌ ERRO DURANTE A COMPILAÇÃO. Verifique o log acima.")
        print("=" * 65)


if __name__ == "__main__":
    build_executable()
