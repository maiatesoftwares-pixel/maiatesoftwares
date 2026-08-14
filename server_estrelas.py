from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app)

DB_PATH = '/var/www/html/avaliacoes.db'

# Cria banco se não existir
if not os.path.exists(DB_PATH):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS avaliacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto TEXT NOT NULL,
            nota INTEGER NOT NULL,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ Banco criado!")

@app.route('/avaliar/<produto>', methods=['POST'])
def avaliar(produto):
    try:
        nota = request.json.get('nota')
        if not nota or nota < 1 or nota > 5:
            return jsonify({'erro': 'Nota inválida'}), 400
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('INSERT INTO avaliacoes (produto, nota) VALUES (?, ?)', (produto, nota))
        conn.commit()
        conn.close()
        return jsonify({'status': 'ok', 'mensagem': 'Avaliação salva!'})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/media/<produto>')
def media(produto):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT AVG(nota), COUNT(*) FROM avaliacoes WHERE produto = ?', (produto,))
        media, total = c.fetchone()
        conn.close()
        return jsonify({'media': round(media or 0, 1), 'total': total or 0})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/')
def home():
    return 'API de Avaliações - OK ✅'

if __name__ == '__main__':
    print("🚀 Servidor de Avaliações iniciando...")
    app.run(host='0.0.0.0', port=5000, debug=False)
