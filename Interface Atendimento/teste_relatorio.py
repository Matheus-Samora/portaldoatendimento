import requests
import os
import json
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# --- CONFIGURAÇÕES ---
API_URL = os.getenv("SOLIS_API_URL")
JWT_TOKEN = os.getenv("SOLIS_JWT_TOKEN")

# ID do Relatório que você forneceu
REPORT_ID = "6820251203155305" 

def testar_relatorio_generico(cpf_input):
    if not API_URL or not JWT_TOKEN:
        print("❌ ERRO: Verifique se SOLIS_API_URL e SOLIS_JWT_TOKEN estão no arquivo .env")
        return

    # Remove pontuação caso o usuário digite com pontos e traços, 
    # pois o SQL do relatório espera apenas números.
    cpf_limpo = cpf_input.replace('.', '').replace('-', '').strip()

    endpoint = f"/api/basico/relatorio-generico/gerar/{REPORT_ID}"
    url = f"{API_URL}{endpoint}"
    
    # CORREÇÃO: A API da Solis espera os parâmetros dentro de um objeto "par" no CORPO da requisição
    payload = {
        "par": {
            "cpf": cpf_limpo
        }
    }

    headers = {
        "X-Token": JWT_TOKEN,
        "Content-Type": "application/json"
    }

    print(f"\n--- 🧪 Iniciando Teste de Relatório Genérico ---")
    print(f"📍 URL: {url}")
    print(f"🔑 Token (primeiros 10 chars): {JWT_TOKEN[:10]}...")
    print(f"🔎 Buscando CPF: {cpf_limpo}")
    print(f"📦 Payload enviado: {json.dumps(payload)}")
    print("-" * 40)

    try:
        # CORREÇÃO: Usamos 'json=payload' em vez de 'params=...'
        # Isso força o envio dos dados no corpo da requisição, conforme o padrão da Solis
        response = requests.get(url, headers=headers, json=payload, timeout=15)
        
        print(f"📡 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # A API pode retornar uma lista direta ou um objeto com chave 'items'
            items = data if isinstance(data, list) else data.get('items', [])
            
            if items:
                print(f"✅ SUCESSO! Encontrados {len(items)} registros.")
                print("\n📄 Primeiro registro encontrado:")
                record = items[0]
                
                # Exibe campos chave para confirmar se o SQL funcionou
                print(f"   ID (personid): {record.get('identificador')}")
                print(f"   Nome: {record.get('nome')}")
                print(f"   CPF Retornado: {record.get('cpf')}")
                print(f"   Email: {record.get('email')}")
                
                print("\n📦 JSON Completo do primeiro item:")
                print(json.dumps(record, indent=4, ensure_ascii=False))
            else:
                print("⚠️  A requisição funcionou, mas o relatório veio VAZIO.")
                print("   1. Verifique se o CPF existe na tabela 'basphysicalperson'.")
                print("   2. Verifique se o SQL do relatório no Solis aceita o parâmetro 'cpf' (sem $).")
        
        elif response.status_code == 401:
            print("❌ Erro de Autenticação (401). Seu token pode estar expirado ou inválido.")
        
        elif response.status_code == 404:
            print("❌ Erro 404. O endpoint ou o ID do relatório não foram encontrados.")
            
        elif response.status_code == 500:
            print("❌ Erro Interno do Servidor (500). Pode ser um erro na sintaxe SQL do relatório.")
            print(f"   Resposta: {response.text}")
            
        else:
            print(f"❌ Erro desconhecido: {response.text}")

    except Exception as e:
        print(f"❌ Exceção ao executar teste: {e}")

if __name__ == "__main__":
    while True:
        print("\n" + "="*50)
        entrada = input("➡️  Digite o CPF para pesquisar (ou 'sair' para encerrar): ")
        
        if entrada.lower() in ['sair', 'exit']:
            print("Encerrando...")
            break
            
        if entrada.strip():
            testar_relatorio_generico(entrada)
        else:
            print("⚠️  Por favor, digite um CPF válido.")