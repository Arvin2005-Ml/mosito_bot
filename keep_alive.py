from flask import Flask, send_file
from threading import Thread
import os

app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

@app.route('/download-db')
def download_db():
    if os.path.exists("data.db"):
        return send_file("data.db", as_attachment=True)
    return "فایل پیدا نشد", 404

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()
