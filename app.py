from flask import Flask, jsonify, request
import mercadopago
import requests
import json
import os

app = Flask(__name__)

# ===== SUAS CHAVES =====
PUBLIC_KEY = "APP_USR-d1318a48-c04c-4651-815c-dd148d1bf416"
ACCESS_TOKEN = "APP_USR-7276173347887306-071618-579a6c233b60477bf1693fec59bd4b61-1315684502"
KEYGEN_PRODUCT_ID = "b8428c88-430c-44ab-a64a-ba40db88ee9a"  # <-- ADICIONE ESTA LINHA
# ===== KEYGEN CONFIG =====
# 🔥 SUBSTITUA PELAS SUAS INFORMAÇÕES
KEYGEN_ACCOUNT = "6c068a0e-f15e-4d59-a218-0b74006daf86"           # Ex: "12345678-1234-1234-1234-123456789012"
KEYGEN_PRODUCT_TOKEN = "admin-e90bf1545b746cab9e2b8377efc4d7e54996c90663cb657d22a7bd5b34370644v3"   # Ex: "prod-xxxxx-xxxxx-xxxxx"
KEYGEN_POLICY_ANUAL = "477ce4b2-3552-4a59-814a-5732a9bd7454"       # ID da política para licença anual
KEYGEN_POLICY_VITALICIA = "53c40276-107c-4f75-9580-cda6b82f3839" # ID da política para licença vitalícia
KEYGEN_POLICY_MAIATE = "26c8de16-db97-4cbc-ad1a-c6f17ef06d9a"     # ID da política para Maiate Mixer
KEYGEN_POLICY_WM = "06764b75-7264-4808-a4e4-007fa2b5595e"             # ID da política para WM Meu Negócio

# Inicializa o SDK do Mercado Pago
sdk = mercadopago.SDK(ACCESS_TOKEN)

# ===== PRODUTOS =====
PRODUTOS = {
    'grafolaudo_anual': {
        'nome': 'GrafoLaudo Analyzer Pro - Licença Anual',
        'preco': 399.00
    },
    'grafolaudo_vitalicio': {
        'nome': 'GrafoLaudo Analyzer Pro - Licença Vitalícia',
        'preco': 699.00
    },
    'maiatemixer': {
        'nome': 'Maiate Mixer - Licença Vitalícia',
        'preco': 199.00
    },
    'wmmeunegocio': {
        'nome': 'WM Meu Negócio - Licença Perpétua',
        'preco': 99.00
    }
}

# ===== MAPEAMENTO DE POLÍTICAS POR PRODUTO =====
POLITICAS = {
    'grafolaudo_anual': KEYGEN_POLICY_ANUAL,
    'grafolaudo_vitalicio': KEYGEN_POLICY_VITALICIA,
    'maiatemixer': KEYGEN_POLICY_MAIATE,
    'wmmeunegocio': KEYGEN_POLICY_WM
}

# ===== FUNÇÃO PARA CRIAR LICENÇA NO KEYGEN =====
def criar_licenca_keygen(email_cliente, produto_id):
    """
    Cria uma licença no Keygen para o cliente
    Retorna a chave de licença gerada ou None em caso de erro
    """
    
    policy_id = POLITICAS.get(produto_id)
    if not policy_id:
        print(f"❌ Produto {produto_id} sem política definida")
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
            print(f"✅ Licença criada com sucesso: {chave}")
            return chave
        else:
            print(f"❌ Erro ao criar licença: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")
        return None

# ===== ROTA PARA CRIAR PAGAMENTO =====
@app.route('/criar_pagamento/<produto_id>')
def criar_pagamento(produto_id):
    # Verifica se o produto existe
    if produto_id not in PRODUTOS:
        return jsonify({'erro': 'Produto não encontrado'}), 404
    
    produto = PRODUTOS[produto_id]
    
    # Cria a preferência de pagamento
    preference_data = {
        "items": [
            {
                "title": produto['nome'],
                "quantity": 1,
                "unit_price": produto['preco'],
                "currency_id": "BRL"
            }
        ],
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
        return jsonify({
            'url': preference['response']['init_point'],
            'preference_id': preference['response']['id']
        })
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# ===== ROTA DO WEBHOOK (RECEBE CONFIRMAÇÃO DO MERCADO PAGO) =====
@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Recebe notificações do Mercado Pago quando um pagamento é aprovado
    """
    try:
        data = request.json
        print(f"📥 Webhook recebido: {data}")
        
        # Verifica se é um pagamento
        if data.get('type') == 'payment':
            payment_id = data['data']['id']
            
            # Buscar detalhes do pagamento na API do Mercado Pago
            url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
            headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                payment_data = response.json()
                
                # Verificar se foi aprovado
                if payment_data.get('status') == 'approved':
                    # Pega o email do cliente e o produto
                    email = payment_data.get('payer', {}).get('email', 'cliente@email.com')
                    
                    # Identificar qual produto foi comprado
                    description = payment_data.get('description', '')
                    produto_id = None
                    
                    if 'grafolaudo_anual' in description.lower():
                        produto_id = 'grafolaudo_anual'
                    elif 'grafolaudo_vitalicio' in description.lower():
                        produto_id = 'grafolaudo_vitalicio'
                    elif 'maiatemixer' in description.lower():
                        produto_id = 'maiatemixer'
                    elif 'wmmeunegocio' in description.lower():
                        produto_id = 'wmmeunegocio'
                    
                    if produto_id:
                        # Gerar licença no Keygen
                        chave = criar_licenca_keygen(email, produto_id)
                        
                        if chave:
                            print(f"✅ Licença gerada: {chave} para {email}")
                            # TODO: Enviar e-mail com a chave
                        else:
                            print(f"❌ Falha ao gerar licença para {email}")
                    else:
                        print(f"⚠️ Produto não identificado: {description}")
                        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        print(f"❌ Erro no webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ===== ROTA PARA TESTAR =====
@app.route('/')
def home():
    return jsonify({'status': 'API de pagamentos funcionando!'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
