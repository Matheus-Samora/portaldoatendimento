import os
import datetime
from google.cloud import bigquery
import flask

def get_billing_data(request):
    # 1. Configuração de CORS (Para permitir que seu HTML acesse esta função)
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    headers = {'Access-Control-Allow-Origin': '*'}

    try:
        # 2. Configurações
        # Você deve definir essa variável de ambiente na Cloud Function
        # Formato: projeto.dataset.gcp_billing_export_v1_XXXXXX_XXXXXX_XXXXXX
        table_id = os.environ.get('BILLING_TABLE_ID')
        
        if not table_id:
            return (flask.jsonify({"error": "Configuração pendente: BILLING_TABLE_ID não encontrada"}), 500, headers)

        client = bigquery.Client()

        # 3. A Query SQL (Pega os custos do mês atual agrupados por serviço)
        query = f"""
            SELECT
                service.description as service_name,
                SUM(cost) as total_cost
            FROM `{table_id}`
            WHERE
                DATE(_PARTITIONDATE) >= DATE_TRUNC(CURRENT_DATE(), MONTH)
            GROUP BY 1
            ORDER BY 2 DESC
        """

        query_job = client.query(query)
        results = query_job.result()

        # 4. Formatação da Resposta para o HTML
        breakdown = {}
        total_geral = 0.0

        for row in results:
            service = row.service_name
            cost = row.total_cost
            
            # Agrupa serviços menores em "Outros" para não poluir o gráfico
            if cost > 0.001: 
                breakdown[service] = cost
            
            total_geral += cost

        response_data = {
            "total": total_geral,
            "breakdown": breakdown,
            "currency": "BRL",
            "updated_at": datetime.datetime.now().isoformat()
        }

        return (flask.jsonify(response_data), 200, headers)

    except Exception as e:
        print(f"Erro interno: {e}")
        return (flask.jsonify({"error": str(e)}), 500, headers)