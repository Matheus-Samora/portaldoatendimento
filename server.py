import os
import requests
import json
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

app = Flask(__name__)
# Permite CORS de qualquer origem
CORS(app, resources={r"/*": {"origins": "*"}})

# Configurações Solis
API_URL = os.getenv("SOLIS_API_URL", "https://academico.faculdadeimes.org.br")
JWT_TOKEN = os.getenv("SOLIS_JWT_TOKEN")

# IDs dos Relatórios
REPORT_ID_CPF = "6820251203155305"
REPORT_ID_NOME = "6620251203154311"
REPORT_ID_DETALHE = "7020251204095501"

# --- ROTA RAIZ (Agora entrega o HTML) ---
@app.route('/')
def index():
    """
    Serve o arquivo index.html quando o usuário acessa a raiz.
    Certifique-se de que 'index.html' está na mesma pasta deste script.
    """
    try:
        return send_file('index.html')
    except Exception as e:
        return f"Erro ao carregar o site: {e}. Verifique se o arquivo index.html está no repositório.", 404

# --- ROTA DE STATUS (PING) ---
@app.route('/status', methods=['GET'])
def server_status():
    return jsonify({"status": "online", "service": "Solis Proxy"}), 200

def execute_report(report_id, params, step_name="Relatório"):
    if not JWT_TOKEN:
        print(f"❌ [{step_name}] ERRO: Token não configurado.")
        return None

    url = f"{API_URL}/api/basico/relatorio-generico/gerar/{report_id}"
    payload = { "par": params }
    headers = { "X-Token": JWT_TOKEN, "Content-Type": "application/json" }
    
    try:
        response = requests.get(url, headers=headers, json=payload, timeout=20)
        if response.status_code == 200:
            try:
                data = response.json()
                items = data if isinstance(data, list) else data.get('items', [])
                return items
            except json.JSONDecodeError:
                return None
        else:
            return None
    except Exception as e:
        return None

@app.route('/proxy/smart-search', methods=['POST'])
def smart_search():
    if not JWT_TOKEN:
        return jsonify({"error": "Token não configurado"}), 500

    data = request.json
    cpf_input = data.get('cpf', '').replace('.', '').replace('-', '').strip()
    nome_input = data.get('nome', '').strip()
    aluno_encontrado = None

    # 1. Busca por CPF
    if cpf_input:
        res_cpf = execute_report(REPORT_ID_CPF, {"cpf": cpf_input}, step_name="Busca CPF")
        if res_cpf and len(res_cpf) > 0:
            return jsonify(res_cpf[0])

    # 2. Busca por Nome
    if nome_input:
        params_nome = { "NOME_ALUNO": nome_input, "nome": nome_input }
        res_nomes = execute_report(REPORT_ID_NOME, params_nome, step_name="Busca Nome")
        
        if res_nomes and len(res_nomes) > 0:
            candidato = res_nomes[0]
            id_candidato = candidato.get('ID') or candidato.get('id') or candidato.get('personid') or candidato.get('identificador')
            
            if id_candidato:
                params_detalhe = { "cod": id_candidato, "id": id_candidato, "ID": id_candidato }
                res_detalhe = execute_report(REPORT_ID_DETALHE, params_detalhe, step_name="Busca Detalhes ID")
                if res_detalhe and len(res_detalhe) > 0:
                    return jsonify(res_detalhe[0])

    return jsonify({"error": "Aluno não encontrado."}), 404

@app.route('/proxy/api', methods=['POST'])
def proxy_api():
    data = request.json
    endpoint = data.get('endpoint')
    params = data.get('params', {})
    url = f"{API_URL}{endpoint}"
    headers = {"X-Token": JWT_TOKEN, "Content-Type": "application/json"}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=20)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"error": f"Erro Solis: {response.status_code}", "details": response.text}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
