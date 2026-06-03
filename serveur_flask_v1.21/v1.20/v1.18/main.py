# coding: utf-8
import os
os.environ['OMP_NUM_THREADS'] = '1'  # évite les crashes PyTorch multi-thread

if __name__ == '__main__':
    import socket
    from application import Application

    # Trouver l'IP locale automatiquement
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = "127.0.0.1"

    app = Application()

    print("\n" + "=" * 50)
    print("  JOGAM SAMv2 — Serveur démarré !")
    print(f"  Local  : http://127.0.0.1:5000")
    print(f"  Réseau : http://{ip}:5000")
    print("=" * 50 + "\n")

    app.run(host='0.0.0.0', port=5000)