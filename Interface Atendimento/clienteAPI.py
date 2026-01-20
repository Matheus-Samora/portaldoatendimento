import requests
import json
import logging

# Configuração básica de logs para facilitar a depuração no VS Code
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SolisAPIClient:
    """
    Cliente para integração com a API da Solis GE.
    Gerencia autenticação e consultas acadêmicas e financeiras.
    """

    def __init__(self, base_url, token):
        """
        Inicializa o cliente da API.

        :param base_url: URL base da API (ex: https://academico.faculdadeimes.org.br)
        :param token: Token JWT para autenticação (X-Token)
        """
        self.base_url = base_url.rstrip('/')  # Remove barra final se houver
        self.headers = {
            "X-Token": token,
            "Content-Type": "application/json",
            "User-Agent": "IntegracaoPython/1.0"
        }

    def _make_request(self, endpoint, params=None):
        """
        Método interno genérico para fazer requisições GET.
        """
        url = f"{self.base_url}{endpoint}"
        try:
            logging.info(f"Consultando endpoint: {url} | Params: {params}")
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            # Verifica se a resposta foi bem-sucedida (200 OK)
            response.raise_for_status()
            
            data = response.json()
            
            # A API Solis geralmente retorna listas dentro de uma chave 'items', mas às vezes retorna a lista direta.
            # Esta lógica normaliza o retorno para sempre ser uma lista ou dicionário limpo.
            if isinstance(data, dict) and 'items' in data:
                return data['items']
            return data

        except requests.exceptions.HTTPError as err:
            logging.error(f"Erro HTTP ao acessar Solis: {err}. Status: {response.status_code}. Resposta: {response.text}")
            return None
        except requests.exceptions.ConnectionError:
            logging.error("Erro de Conexão: Não foi possível conectar ao servidor da Solis.")
            return None
        except requests.exceptions.Timeout:
            logging.error("Erro de Timeout: A API demorou muito para responder.")
            return None
        except Exception as e:
            logging.error(f"Erro inesperado: {e}")
            return None

    def consultar_pessoa(self, termo_busca):
        """
        Busca uma pessoa por Nome, CPF ou ID.
        Endpoint sugerido: /v1/person/search
        """
        endpoint = "/v1/person/search"
        # A Solis geralmente aceita um parâmetro genérico 'q' ou específicos como 'name'/'cpf'
        # Ajuste o parâmetro 'body' ou 'q' conforme a doc específica da sua versão
        params = {"q": termo_busca} 
        return self._make_request(endpoint, params)

    def consultar_dados_contrato(self, person_id):
        """
        Retorna os contratos acadêmicos de um aluno.
        Utilizado para determinar se é Graduação (com contrato) ou Pós.
        
        :param person_id: ID numérico da pessoa no sistema.
        """
        endpoint = "/v1/academic/contract"
        params = {"personId": person_id}
        
        contratos = self._make_request(endpoint, params)
        
        if contratos is None:
            return []
            
        # Filtragem opcional: Retornar apenas contratos ativos ou relevantes
        # Exemplo: contratos_ativos = [c for c in contratos if c.get('status') == 'ATIVO']
        return contratos

    def consultar_financeiro_aluno(self, person_id):
        """
        Retorna os títulos financeiros (boletos/mensalidades) do aluno.
        Inclui dados de lançamentos (débitos e créditos) para cálculo de saldo.
        
        :param person_id: ID numérico da pessoa no sistema.
        """
        endpoint = "/v1/financial/title"
        params = {
            "personId": person_id,
            "limit": 100,  # Garante que puxe um bom histórico
            "order": "maturityDate:desc"  # Ordena pelos mais recentes
        }
        
        titulos = self._make_request(endpoint, params)
        
        if titulos is None:
            return []
            
        return titulos

# --- Bloco de Teste Rápido (Executa se rodar o arquivo diretamente no VS Code) ---
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    # Tenta carregar .env se existir localmente para teste
    load_dotenv()

    # Valores de teste (Substitua por dados reais ou use .env)
    API_URL = os.getenv("SOLIS_API_URL", "https://academico.faculdadeimes.org.br")
    TOKEN = os.getenv("SOLIS_JWT_TOKEN", "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyIjoiMTUwMzg2ODU2NzYiLCJoYXNoIjoiMmQxNDIwZjgzZjZlZjRjNDQ0NjExOGM2YWYzYTcyYWQiLCJ1bml0SWQiOm51bGx9.xSuLZxq2F2ujoOfgP9MQS3rHs9yADrxSAsYzUMUrDCk")
    ALUNO_TESTE_ID = "37930" # Substitua por um ID real para testar

    if TOKEN == "SEU_TOKEN_AQUI":
        print("⚠️  AVISO: Configure o token no arquivo .env ou no código para testar.")
    else:
        print(f"--- 🧪 Iniciando Teste do Cliente API Solis ---")
        client = SolisAPIClient(API_URL, TOKEN)

        print(f"\n🔎 Buscando Contratos para ID {ALUNO_TESTE_ID}...")
        contratos = client.consultar_dados_contrato(ALUNO_TESTE_ID)
        print(f"✅ Encontrados {len(contratos)} contratos.")
        if contratos:
            print(f"   Exemplo: {contratos[0].get('courseName', 'Sem nome')}")

        print(f"\n💰 Buscando Financeiro para ID {ALUNO_TESTE_ID}...")
        financeiro = client.consultar_financeiro_aluno(ALUNO_TESTE_ID)
        print(f"✅ Encontrados {len(financeiro)} títulos.")
        if financeiro:
            print(f"   Exemplo Título: Valor {financeiro[0].get('nominalValue')} - Vencimento {financeiro[0].get('maturityDate')}")