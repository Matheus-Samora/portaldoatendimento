import os
import requests
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

app = Flask(__name__)
# Permite CORS de qualquer origem para facilitar desenvolvimento local
CORS(app, resources={r"/*": {"origins": "*"}})

# Configurações Solis
API_URL = os.getenv("SOLIS_API_URL", "https://academico.faculdadeimes.org.br")
JWT_TOKEN = os.getenv("SOLIS_JWT_TOKEN")

# IDs dos Relatórios
REPORT_ID_CPF = "6820251203155305"      # Busca por CPF -> Retorna Detalhes
REPORT_ID_NOME = "6620251203154311"     # Busca por Nome -> Retorna ID + Nome
REPORT_ID_DETALHE = "7020251204095501"  # Busca por ID -> Retorna Detalhes Completos

# --- ROTA DE STATUS (PING) ---
@app.route('/status', methods=['GET'])
def server_status():
    """Rota para o HTML verificar se o servidor está online"""
    return jsonify({"status": "online", "service": "Solis Proxy"}), 200

def execute_report(report_id, params, step_name="Relatório"):
    """
    Executa relatório genérico com LOGS COMPLETOS.
    """
    if not JWT_TOKEN:
        print(f"❌ [{step_name}] ERRO: Token não configurado.")
        return None

    url = f"{API_URL}/api/basico/relatorio-generico/gerar/{report_id}"
    
    # Payload no padrão Solis
    payload = { "par": params }
    
    headers = {
        "X-Token": JWT_TOKEN,
        "Content-Type": "application/json"
    }
    
    try:
        print(f"\n--- 📡 [{step_name}] Executando Requisição ---")
        print(f"   📍 URL: {url}")
        print(f"   📦 Payload Enviado: {json.dumps(payload, ensure_ascii=False)}")
        
        response = requests.get(url, headers=headers, json=payload, timeout=20)
        
        print(f"   🔙 Status Code: {response.status_code}")
        
        # Log da resposta (primeiros 500 caracteres para não poluir demais se for gigante)
        # raw_resp = response.text
        # print(f"   📄 Resposta Raw (início): {raw_resp[:500]}...")
        
        if response.status_code == 200:
            try:
                data = response.json()
                items = data if isinstance(data, list) else data.get('items', [])
                print(f"   ✅ [{step_name}] Sucesso! Itens retornados: {len(items)}")
                return items
            except json.JSONDecodeError:
                print(f"   ❌ [{step_name}] Erro: Resposta não é JSON válido.")
                return None
        else:
            # Tenta ler o erro do corpo da resposta
            print(f"   ⚠️  [{step_name}] Falha na API Solis. Body: {response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"   ❌ [{step_name}] Exceção de Conexão: {e}")
        return None

@app.route('/proxy/smart-search', methods=['POST'])
def smart_search():
    """
    Busca Inteligente (Smart Search)
    Lógica: CPF -> (falha) -> Nome -> Pega ID -> Detalhes
    """
    print("\n\n" + "="*60)
    print("🚀 NOVA REQUISIÇÃO: /proxy/smart-search")
    
    if not JWT_TOKEN:
        print("❌ ERRO CRÍTICO: Token JWT não encontrado no .env")
        return jsonify({"error": "Token não configurado"}), 500

    data = request.json
    print(f"📥 Dados Recebidos do Front: {json.dumps(data, ensure_ascii=False)}")

    # Limpa CPF
    cpf_input = data.get('cpf', '').replace('.', '').replace('-', '').strip()
    nome_input = data.get('nome', '').strip()

    aluno_encontrado = None

    # --- TENTATIVA 1: Busca por CPF ---
    if cpf_input:
        print(f"\n👉 [ETAPA 1] Tentando busca direta por CPF: {cpf_input}")
        res_cpf = execute_report(REPORT_ID_CPF, {"cpf": cpf_input}, step_name="Busca CPF")
        
        if res_cpf and len(res_cpf) > 0:
            aluno_encontrado = res_cpf[0]
            print(f"🎉 ALUNO ENCONTRADO (via CPF): {aluno_encontrado.get('nome')}")
            print("="*60 + "\n")
            return jsonify(aluno_encontrado)
        else:
            print("🔸 CPF não retornou resultados. Passando para próxima etapa...")

    # --- TENTATIVA 2: Busca por Nome (Fallback) ---
    if nome_input and not aluno_encontrado:
        print(f"\n👉 [ETAPA 2] Tentando busca por Nome: '{nome_input}'")
        
        # CORREÇÃO CRÍTICA: Envia variações do nome do parâmetro para garantir match no SQL
        params_nome = {
            "NOME_ALUNO": nome_input,
            "NOME_ALUNO_": nome_input,
            "_NOME_ALUNO_": nome_input,
            "nome": nome_input
        }
        
        res_nomes = execute_report(REPORT_ID_NOME, params_nome, step_name="Busca Nome")
        
        if res_nomes and len(res_nomes) > 0:
            # Pega o primeiro candidato
            candidato = res_nomes[0]
            print(f"   💡 Candidato localizado no relatório de nomes: {candidato}")
            
            # Tenta identificar qual campo é o ID (variações possíveis de retorno)
            id_candidato = candidato.get('ID') or candidato.get('id') or candidato.get('personid') or candidato.get('identificador')
            
            if id_candidato:
                print(f"\n👉 [ETAPA 3] ID '{id_candidato}' encontrado. Buscando detalhes completos...")
                
                # Parâmetro SQL (Relatório 70)
                # Envia variações de 'id' para garantir
                params_detalhe = { 
                    "cod": id_candidato, 
                    "id": id_candidato,
                    "ID": id_candidato 
                }
                
                res_detalhe = execute_report(REPORT_ID_DETALHE, params_detalhe, step_name="Busca Detalhes ID")
                
                if res_detalhe and len(res_detalhe) > 0:
                    aluno_encontrado = res_detalhe[0]
                    print(f"🎉 ALUNO ENCONTRADO (via Nome->ID): {aluno_encontrado.get('nome')}")
                    print("="*60 + "\n")
                    return jsonify(aluno_encontrado)
                else:
                    print("🔸 Falha ao buscar detalhes do ID. Relatório retornou vazio.")
            else:
                print("🔸 Nome encontrado, mas o relatório não retornou uma coluna de ID válida.")
                print(f"   Colunas retornadas: {list(candidato.keys())}")
        else:
            print("🔸 Nome não encontrado no relatório.")

    print("❌ BUSCA FALHOU: Nenhum aluno encontrado.")
    print("="*60 + "\n")
    return jsonify({"error": "Aluno não encontrado por CPF ou Nome."}), 404

@app.route('/proxy/api', methods=['POST'])
def proxy_api():
    """
    Proxy para endpoints padrão da API (Contratos, Financeiro, etc)
    """
    print("\n" + "-"*40)
    print("🔄 PROXY API CALL")
    
    data = request.json
    endpoint = data.get('endpoint')
    params = data.get('params', {})
    url = f"{API_URL}{endpoint}"
    headers = {"X-Token": JWT_TOKEN, "Content-Type": "application/json"}

    try:
        print(f"   URL: {url}")
        print(f"   Params: {params}")
        response = requests.get(url, headers=headers, params=params, timeout=20)
        
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            print(f"   Erro Body: {response.text[:200]}")
            return jsonify({"error": f"Erro Solis: {response.status_code}", "details": response.text}), response.status_code

    except Exception as e:
        print(f"   ❌ Exceção: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("\n--- 🚀 Servidor Proxy Solis DEBUG (v7 - Host Seguro) ---")
    print(f"    - URL Base: {API_URL}")
    print(f"    - Token Carregado: {'SIM' if JWT_TOKEN else 'NÃO'}")
    print("    - Logs: ATIVADOS (Verbose)")
    # CORREÇÃO CRÍTICA: Roda em 127.0.0.1 para evitar problemas de resolução de 'localhost' em IPv6
    print("    - Aguardando requisições em http://127.0.0.1:5000 ...")
    app.run(host='127.0.0.1', port=5000, debug=True)