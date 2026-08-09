# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, send_file, make_response, session, redirect
import mercadopago
import requests
import json
import os
import uuid

app = Flask(__name__)
app.secret_key = 'MaiateSoftwares2026SecretKey'

# ===== SUAS CHAVES =====
PUBLIC_KEY = "APP_USR-d1318a48-c04c-4651-815c-dd148d1bf416"
ACCESS_TOKEN = "APP_USR-7276173347887306-071618-579a6c233b60477bf1693fec59bd4b61-1315684502"
KEYGEN_PRODUCT_ID = "b8428c88-430c-44ab-a64a-ba40db88ee9a"

# ===== KEYGEN CONFIG =====
KEYGEN_ACCOUNT = "6c068a0e-f15e-4d59-a218-0b74006daf86"
KEYGEN_PRODUCT_TOKEN = "admin-e90bf1545b746cab9e2b8377efc4d7e54996c90663cb657d22a7bd5b34370644v3"
KEYGEN_POLICY_ANUAL = "477ce4b2-3552-4a59-814a-5732a9bd7454"
KEYGEN_POLICY_VITALICIA = "53c40276-107c-4f75-9580-cda6b82f3839"
KEYGEN_POLICY_MAIATE = "26c8de16-db97-4cbc-ad1a-c6f17ef06d9a"
KEYGEN_POLICY_WM = "06764b75-7264-4808-a4e4-007fa2b5595e"
KEYGEN_POLICY_GRAFOTECNICA = "bf6855b6-d23b-47bd-8323-85255a635b5b"

# Inicializa o SDK do Mercado Pago
sdk = mercadopago.SDK(ACCESS_TOKEN)

# ===== PRODUTOS =====
PRODUTOS = {
    'grafolaudo_anual': {
        'nome': 'GrafoLaudo Analyzer Pro - Licenca Anual',
        'preco': 399.00
    },
    'grafolaudo_vitalicio': {
        'nome': 'GrafoLaudo Analyzer Pro - Licenca Vitalicia',
        'preco': 699.00
    },
    'maiatemixer': {
        'nome': 'Maiate Mixer - Licenca Vitalicia',
        'preco': 199.00
    },
    'wmmeunegocio': {
        'nome': 'WM Meu Negocio - Licenca Perpetua',
        'preco': 99.00
    },
    'grafotecnica': {
        'nome': 'Tabela Grafotecnica WM - Licenca Vitalicia',
        'preco': 89.90
    }
}

# ===== MAPEAMENTO DE POLITICAS POR PRODUTO =====
POLITICAS = {
    'grafolaudo_anual': KEYGEN_POLICY_ANUAL,
    'grafolaudo_vitalicio': KEYGEN_POLICY_VITALICIA,
    'maiatemixer': KEYGEN_POLICY_MAIATE,
    'wmmeunegocio': KEYGEN_POLICY_WM,
    'grafotecnica': KEYGEN_POLICY_GRAFOTECNICA
}

# ===== DICIONÁRIO PARA ARMAZENAR E-MAILS =====
pagamentos_pendentes = {}

# ===== FUNÇÃO PARA CRIAR LICENÇA NO KEYGEN =====
def criar_licenca_keygen(email_cliente, produto_id):
    policy_id = POLITICAS.get(produto_id)
    if not policy_id:
        print(f"ERRO: Produto {produto_id} sem politica definida")
        return None

    url = f"https://api.keygen.sh/v1/accounts/{KEYGEN_ACCOUNT}/licenses"
    payload = {
        "data": {
            "type": "licenses",
            "attributes": {
                "name": email_cliente,
                "metadata": {
                    "produto": produto_id,
                    "email": email_cliente
                }
            },
            "relationships": {
                "policy": {
                    "data": {
                        "type": "policies",
                        "id": policy_id
                    }
                }
            }
        }
    }
    headers = {
        "Authorization": f"Bearer {KEYGEN_PRODUCT_TOKEN}",
        "Content-Type": "application/vnd.api+json",
        "Accept": "application/vnd.api+json"
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 201:
            dados = response.json()
            chave = dados['data']['attributes']['key']
            print(f"Licenca criada com sucesso: {chave}")
            return chave
        else:
            print(f"ERRO ao criar licenca: {response.status_code}")
            return None
    except Exception as e:
        print(f"ERRO: {e}")
        return None

# ===== CONFIGURAÇÃO DO E-MAIL (BREVO) =====
EMAIL_HOST = "smtp-relay.brevo.com"
EMAIL_PORT = 587
EMAIL_USER = "b4b172001@smtp-brevo.com"
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')
EMAIL_FROM = "contato@maiatesoftwares.com.br"


# ===== FUNÇÃO PARA ENVIAR E-MAIL =====
def enviar_email(destino, chave, produto):
    import smtplib
    from email.mime.text import MIMEText

    assunto = f"Sua licença - {produto}"
    mensagem = f"""
Olá!

Sua licença para o produto {produto} foi gerada com sucesso.

Chave de ativação: {chave}

Instruções de ativação:
1. Abra o software
2. Clique em "Ativar"
3. Cole a chave acima

Qualquer dúvida, responda a este e-mail.

Atenciosamente,
MaIAte Softwares
"""

    msg = MIMEText(mensagem)
    msg['Subject'] = assunto
    msg['From'] = EMAIL_FROM
    msg['To'] = destino

    try:
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_FROM, destino, msg.as_string())
        server.quit()
        print(f"✅ E-mail enviado para {destino}")
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar e-mail: {e}")
        return False

# ===== ROTA DE COMPRA COM FORMULÁRIO =====
@app.route('/comprar/<produto>', methods=['GET', 'POST'])
def comprar(produto):
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        estado = request.form.get('estado')

        if not nome or not email or not estado:
            return "Preencha todos os campos!", 400

        session['nome_comprador'] = nome
        session['email_comprador'] = email
        session['estado_comprador'] = estado

        if produto not in PRODUTOS:
            return "Produto não encontrado", 404

        produto_info = PRODUTOS[produto]
        preference_data = {
            "items": [
                {
                    "title": produto_info['nome'],
                    "quantity": 1,
                    "unit_price": produto_info['preco'],
                    "currency_id": "BRL"
                }
            ],
            "external_reference": str(uuid.uuid4()),
            "back_urls": {
                "success": "https://maiatesoftwares.com.br/obrigado.html",
                "failure": "https://maiatesoftwares.com.br/erro.html",
                "pending": "https://maiatesoftwares.com.br/pendente.html"
            },
            "auto_return": "approved",
            "payment_methods": {
                "excluded_payment_methods": [],
                "installments": 12
            },
            "notification_url": "https://maiatesoftwares.com.br/webhook"
        }

        try:
            preference = sdk.preference().create(preference_data)
            external_ref = preference_data["external_reference"]
            pagamentos_pendentes[external_ref] = email
            url = preference['response']['init_point']
            return redirect(url)
        except Exception as e:
            return f"Erro ao criar pagamento: {e}", 500

    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Comprar {produto}</title>
        <style>
            body {{ font-family: Arial; background: #0b0b1a; color: #fff; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
            .box {{ background: #1a1a2e; padding: 30px; border-radius: 12px; border: 1px solid #2d3748; width: 340px; text-align: center; }}
            input, select {{ width: 100%; padding: 10px; margin: 8px 0; border-radius: 6px; border: 1px solid #2d3748; background: #0f172a; color: #fff; box-sizing: border-box; }}
            button {{ width: 100%; padding: 10px; background: #00d4ff; color: #0b0b1a; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 16px; }}
            h2 {{ color: #00d4ff; }}
        </style>
    </head>
    <body>
        <div class="box">
            <h2>🛒 Comprar {produto}</h2>
            <p style="font-size: 14px; color: #9ca3af;">Preencha para finalizar a compra</p>
            <form method="POST">
                <input type="text" name="nome" placeholder="Seu nome" required>
                <input type="email" name="email" placeholder="Seu e-mail" required>
                <select name="estado" required>
                    <option value="">Selecione seu estado</option>
                    <option value="AC">AC</option><option value="AL">AL</option><option value="AP">AP</option>
                    <option value="AM">AM</option><option value="BA">BA</option><option value="CE">CE</option>
                    <option value="DF">DF</option><option value="ES">ES</option><option value="GO">GO</option>
                    <option value="MA">MA</option><option value="MT">MT</option><option value="MS">MS</option>
                    <option value="MG">MG</option><option value="PA">PA</option><option value="PB">PB</option>
                    <option value="PR">PR</option><option value="PE">PE</option><option value="PI">PI</option>
                    <option value="RJ">RJ</option><option value="RN">RN</option><option value="RS">RS</option>
                    <option value="RO">RO</option><option value="RR">RR</option><option value="SC">SC</option>
                    <option value="SP">SP</option><option value="SE">SE</option><option value="TO">TO</option>
                </select>
                <button type="submit">Continuar para pagamento</button>
            </form>
        </div>
    </body>
    </html>
    '''

# ===== ROTA DO WEBHOOK =====
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        print(f"Webhook recebido: {data}")

        if data.get('type') == 'payment':
            payment_id = data['data']['id']
            url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
            headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                payment_data = response.json()
                print(f"Status do pagamento: {payment_data.get('status')}")

                if payment_data.get('status') == 'approved':
                    external_ref = payment_data.get('external_reference')
                    email = pagamentos_pendentes.get(external_ref, 'cliente@email.com')
                    print(f"📧 E-mail: {email}")

                    description = payment_data.get('description', '')
                    produto_id = None

                    if 'grafolaudo_anual' in description.lower():
                        produto_id = 'grafolaudo_anual'
                    elif 'grafolaudo_vitalicio' in description.lower():
                        produto_id = 'grafolaudo_vitalicio'
                    elif 'maiatemixer' in description.lower():
                        produto_id = 'maiatemixer'
                    elif 'wmmeunegocio' in description.lower() or 'wm meu negocio' in description.lower():
                        produto_id = 'wmmeunegocio'
                    elif 'grafotecnica' in description.lower():
                        produto_id = 'grafotecnica'

                    if produto_id:
                        chave = criar_licenca_keygen(email, produto_id)
                        if chave:
                            print(f"✅ Licença gerada: {chave} para {email}")
                            enviar_email(email, chave, produto_id)
                        else:
                            print(f"❌ Falha ao gerar licença para {email}")
                    else:
                        print(f"⚠️ Produto não identificado: {description}")

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print(f"ERRO no webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ===== ROTA PARA TESTAR =====
@app.route('/')
def home():
    return jsonify({'status': 'API de pagamentos funcionando!'})

# ===== ROTA DE DOWNLOAD COM COOKIE =====
@app.route('/baixar/<produto>', methods=['GET', 'POST'])
def baixar(produto):
    if request.cookies.get('baixou'):
        return send_file(f'/var/www/html/downloads/{produto}_Setup.rar')

    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        with open('downloads_log.txt', 'a') as f:
            f.write(f"{nome},{email},{produto}\n")
        resp = make_response(send_file(f'/var/www/html/downloads/{produto}_Setup.rar'))
        resp.set_cookie('baixou', 'true', max_age=60*60*24*30)
        return resp

    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Baixar {produto}</title>
        <style>
            body {{ font-family: Arial; background: #0b0b1a; color: #fff; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
            .box {{ background: #1a1a2e; padding: 30px; border-radius: 12px; border: 1px solid #2d3748; width: 340px; text-align: center; }}
            input, select {{ width: 100%; padding: 10px; margin: 8px 0; border-radius: 6px; border: 1px solid #2d3748; background: #0f172a; color: #fff; box-sizing: border-box; }}
            button {{ width: 100%; padding: 10px; background: #00d4ff; color: #0b0b1a; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 16px; }}
            h2 {{ color: #00d4ff; }}
        </style>
    </head>
    <body>
        <div class="box">
            <h2>📥 Baixar {produto}</h2>
            <p style="font-size: 14px; color: #9ca3af;">Preencha para baixar o software</p>
            <form method="POST">
                <input type="text" name="nome" placeholder="Seu nome" required>
                <input type="email" name="email" placeholder="Seu e-mail" required>
                <select name="estado" required>
                    <option value="">Selecione seu estado</option>
                    <option value="AC">AC</option><option value="AL">AL</option><option value="AP">AP</option>
                    <option value="AM">AM</option><option value="BA">BA</option><option value="CE">CE</option>
                    <option value="DF">DF</option><option value="ES">ES</option><option value="GO">GO</option>
                    <option value="MA">MA</option><option value="MT">MT</option><option value="MS">MS</option>
                    <option value="MG">MG</option><option value="PA">PA</option><option value="PB">PB</option>
                    <option value="PR">PR</option><option value="PE">PE</option><option value="PI">PI</option>
                    <option value="RJ">RJ</option><option value="RN">RN</option><option value="RS">RS</option>
                    <option value="RO">RO</option><option value="RR">RR</option><option value="SC">SC</option>
                    <option value="SP">SP</option><option value="SE">SE</option><option value="TO">TO</option>
                </select>
                <button type="submit">Baixar agora</button>
            </form>
        </div>
    </body>
    </html>
    '''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
