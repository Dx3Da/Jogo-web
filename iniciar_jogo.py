import os
import webbrowser
import threading
import time
from server import main  # Importa a função principal do seu server.py

def abrir_navegador():
    time.sleep(3) # Espera o servidor iniciar
    webbrowser.open("http://localhost:8765")

if __name__ == "__main__":
    # Inicia o servidor em uma thread separada
    threading.Thread(target=main, daemon=True).start()
    # Abre o navegador automaticamente
    abrir_navegador()
    # Mantém o script rodando
    while True:
        time.sleep(1)