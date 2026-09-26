# bilalai.py dosyasının çalışması için gereklidir.

from flask import Flask, jsonify, request, send_from_directory
import subprocess
import sys
import threading
import atexit

app = Flask(__name__)

PYTHON = sys.executable
BILALAI_FILE = "bilalai.py"

# bilalai.py'yi değiştirmeden çalıştırıyoruz.
# -u: stdout'u anlık iletmek için unbuffered mod.
bilalai_process = subprocess.Popen(
    [PYTHON, "-u", BILALAI_FILE],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    encoding="utf-8",
    errors="replace",
    bufsize=1
)

process_lock = threading.Lock()


def read_until_prompt():
    """
    bilalai.py'nin çıktısını 'Sen: ' promptuna kadar okur.
    Prompt görünce sadece BilalAI cevabını döndürür.
    """
    data = ""

    while True:
        char = bilalai_process.stdout.read(1)

        if char == "":
            # Python programı kapanmışsa elde kalan çıktıyı döndür.
            return data.strip()

        data += char

        if data.endswith("Sen: "):
            # Kullanıcı promptunu cevaptan çıkar.
            return data[:-5].strip()


def send_to_bilalai(message):
    """
    Mevcut input()/print() tabanlı BilalAI'ye mesaj gönderir.
    """
    with process_lock:
        if bilalai_process.poll() is not None:
            raise RuntimeError("bilalai.py çalışmıyor.")

        # Mesajı input()'a gönder.
        bilalai_process.stdin.write(message + "\n")
        bilalai_process.stdin.flush()

        # BilalAI cevabını ve bir sonraki 'Sen: ' promptunu oku.
        return read_until_prompt()


# Program açılırken bilalai.py'nin başlangıç mesajını ve ilk promptunu tüket.
startup_output = read_until_prompt()

if startup_output:
    print("BilalAI başlatıldı:")
    print(startup_output)


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True)

    if not data or "message" not in data:
        return jsonify({
            "error": "message alanı gerekli."
        }), 400

    message = str(data["message"]).strip()

    if not message:
        return jsonify({
            "error": "Mesaj boş olamaz."
        }), 400

    try:
        response = send_to_bilalai(message)

        return jsonify({
            "response": response
        })

    except Exception as error:
        return jsonify({
            "error": str(error)
        }), 500


@atexit.register
def shutdown():
    try:
        if bilalai_process.poll() is None:
            bilalai_process.terminate()
            bilalai_process.wait(timeout=2)
    except Exception:
        try:
            bilalai_process.kill()
        except Exception:
            pass


if __name__ == "__main__":
    print("BilalAI web sunucusu başlatılıyor...")
    print("Tarayıcı: http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
