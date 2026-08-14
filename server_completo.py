from flask import Flask, request, jsonify, send_file, redirect, url_for
from flask_cors import CORS
import sqlite3
import os
import json

app = Flask(__name__)
CORS(app)

# ===== BANCO DE AVALIAÇÕES =====
DB_PATH = '/var/www/html/avaliacoes.db'

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
    print("✅ Banco de avaliações criado!")

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

# ===== ROTAS DE COMPRA =====
@app.route('/comprar/<produto>')
def comprar(produto):
    # Redireciona para o Mercado Pago ou página de pagamento
    return f"""
    <h1>💳 Compra do {produto}</h1>
    <p>Sistema de pagamento em desenvolvimento...</p>
    <p>Produto: {produto}</p>
    <a href="/">Voltar</a>
    """
# ===== ROTAS DE DOWNLOAD =====
@app.route('/baixar/<produto>')
def baixar(produto):
    # Mapeamento dos arquivos para download
    arquivos = {
        'GrafoLaudo': '/var/www/html/downloads/GrafoLaudo_Setup.rar',
        'MaiateMixer': '/var/www/html/downloads/MaiateMixer_Setup.rar',
        'WM_Meu_Negocio': '/var/www/html/downloads/WM_Meu_Negocio_Setup.rar'
    }
    
    if produto in arquivos and os.path.exists(arquivos[produto]):
        return send_file(arquivos[produto], as_attachment=True)
    else:
        return f"Arquivo não encontrado para {produto}", 404

# ===== ROTA PRINCIPAL =====
@app.route('/')
def home():
    return redirect('/index.html')

# ===== INICIAR SERVIDOR =====
if __name__ == '__main__':
    print("🚀 Servidor COMPLETO rodando!")
    print("✅ Avaliações: /media/<produto> e /avaliar/<produto>")
    print("✅ Compras: /comprar/<produto>")
    print("✅ Downloads: /baixar/<produto>")
    app.run(host='0.0.0.0', port=5000, debug=False)
