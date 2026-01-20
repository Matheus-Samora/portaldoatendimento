import os
import re
import webbrowser
from datetime import datetime
from dotenv import load_dotenv
# Certifique-se de que o arquivo clienteAPI.py está na mesma pasta
from clienteAPI import SolisAPIClient

def clean_html(raw_html):
    """Remove tags HTML de uma string para melhorar a legibilidade."""
    if not isinstance(raw_html, str):
        return raw_html
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, ' ', raw_html)
    return " ".join(cleantext.split()) # Remove espaços extras e quebras de linha

def format_currency(value):
    """Formata um número para o padrão de moeda brasileiro (R$)."""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def gerar_relatorio_html(person_id, dados_contrato_todos, dados_financeiros):
    """
    Gera uma string HTML contendo o relatório financeiro completo e organizado.
    """
    nome_aluno = "Não encontrado"
    if dados_contrato_todos:
        nome_aluno = dados_contrato_todos[0].get('personName', 'Nome não disponível')

    # --- Início do Template HTML ---
    html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório Financeiro - {nome_aluno}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f4f7f9;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: auto;
            background: #ffffff;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        }}
        h1, h2 {{
            color: #2c3e50;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 10px;
            margin-top: 30px;
        }}
        h1 {{
            text-align: center;
            font-size: 2em;
        }}
        .contrato-info {{
            background: #f8f9fa;
            border-left: 5px solid #3498db;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 15px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            padding: 12px 15px;
            border: 1px solid #e0e0e0;
            text-align: left;
            font-size: 0.95em;
        }}
        th {{
            background-color: #f2f3f5;
            font-weight: 600;
        }}
        tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        .status-pago {{ color: #2ecc71; font-weight: bold; }}
        .status-vencido {{ color: #e74c3c; font-weight: bold; }}
        .status-cancelado {{ color: #95a5a6; text-decoration: line-through; }}
        .status-aberto {{ color: #3498db; }}
        .valor-col, .saldo-col {{ text-align: right; }}
        .lancamentos-section {{ margin-top: 40px; }}
        .lancamentos-section details {{
            border: 1px solid #e0e0e0;
            border-radius: 5px;
            margin-bottom: 10px;
            overflow: hidden;
        }}
        .lancamentos-section summary {{
            padding: 15px;
            background-color: #f8f9fa;
            font-weight: bold;
            cursor: pointer;
        }}
        footer {{
            text-align: center;
            margin-top: 30px;
            font-size: 0.9em;
            color: #7f8c8d;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Relatório Financeiro Completo</h1>
        <p style="text-align:center; font-size: 1.2em;"><strong>Aluno:</strong> {nome_aluno} (ID: {person_id})</p>
    """

    # --- Seção de Contratos ---
    html += "<h2>Contratos Encontrados</h2>"
    if not dados_contrato_todos:
        html += "<p>Nenhum contrato encontrado para este aluno.</p>"
    else:
        for contrato in dados_contrato_todos:
            html += f"""
            <div class="contrato-info">
                <strong>ID Contrato:</strong> {contrato.get('contractId', 'N/A')} | 
                <strong>Status:</strong> {contrato.get('ultimaMovimentacao', {}).get('description', 'N/A')}<br>
                <strong>Curso:</strong> {contrato.get('courseName', 'N/A')}<br>
                <strong>Turma:</strong> {contrato.get('courseVersion', 'N/A')}
            </div>
            """

    # --- Seção de Títulos Financeiros (Resumo) ---
    html += "<h2>Resumo dos Títulos Financeiros</h2>"
    if not dados_financeiros:
        html += "<p>Nenhum título financeiro encontrado para este aluno.</p>"
    else:
        html += """
        <table>
            <thead>
                <tr>
                    <th>Título</th>
                    <th>Parcela</th>
                    <th>Vencimento</th>
                    <th>Data Pagamento</th>
                    <th class="valor-col">Valor Atualizado</th>
                    <th class="valor-col">Valor Pago</th>
                    <th class="saldo-col">Saldo</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
        """
        hoje = datetime.now().date()
        for titulo in dados_financeiros:
            # --- Nova Lógica para calcular valores a partir dos lançamentos ---
            lancamentos = titulo.get('lancamentos', [])
            valor_pago = 0
            valor_atualizado = 0
            data_pagamento = '-'
            
            if lancamentos:
                # Soma todos os créditos (Pagamentos, Descontos, etc.)
                creditos = [lanc for lanc in lancamentos if lanc.get('operationTypeId') == 'C']
                if creditos:
                    valor_pago = sum(float(c.get('value', 0)) for c in creditos)
                
                # Encontra a data do último pagamento/crédito
                datas_pagamento = [
                    datetime.strptime(c['entryDate'], '%d/%m/%Y') 
                    for c in creditos if c.get('entryDate')
                ]
                if datas_pagamento:
                    data_pagamento = max(datas_pagamento).strftime('%d/%m/%Y')

                # Soma todos os débitos (Mensalidades, Juros, etc.) para ter o valor atualizado
                debitos = [lanc for lanc in lancamentos if lanc.get('operationTypeId') == 'D']
                if debitos:
                    valor_atualizado = sum(float(d.get('value', 0)) for d in debitos)
            
            # Se não houver débitos, usa o valor nominal como fallback para o valor atualizado
            if valor_atualizado == 0:
                valor_atualizado = float(titulo.get('nominalValue', 0))

            # --- Lógica de status (existente) ---
            saldo = float(titulo.get('balance', 0))
            is_cancelado = titulo.get('isCanceled') == 'SIM'
            maturity_date_str = titulo.get('maturityDate', '')
            status_class = ""
            status_text = ""

            if is_cancelado:
                status_class = "status-cancelado"
                status_text = "Cancelado"
            elif saldo == 0:
                status_class = "status-pago"
                status_text = "Pago"
            else:
                try:
                    if maturity_date_str and datetime.strptime(maturity_date_str, '%d/%m/%Y').date() < hoje:
                        status_class = "status-vencido"
                        status_text = "Vencido"
                    else:
                        status_class = "status-aberto"
                        status_text = "Em Aberto"
                except (ValueError, TypeError):
                    status_text = "Data Inválida"

            html += f"""
                <tr>
                    <td>{titulo.get('invoiceId', 'N/A')}</td>
                    <td>{titulo.get('parcelNumber', 'N/A')}</td>
                    <td>{maturity_date_str}</td>
                    <td>{data_pagamento}</td>
                    <td class="valor-col">{format_currency(valor_atualizado)}</td>
                    <td class="valor-col">{format_currency(valor_pago)}</td>
                    <td class="saldo-col">{format_currency(saldo)}</td>
                    <td class="{status_class}">{status_text}</td>
                </tr>
            """
        html += "</tbody></table>"

    # --- Seção de Detalhes dos Lançamentos ---
    html += "<div class='lancamentos-section'><h2>Detalhe dos Lançamentos por Título</h2>"
    if not dados_financeiros:
        html += "<p>Nenhum lançamento para exibir.</p>"
    else:
        for titulo in dados_financeiros:
            invoice_id = titulo.get('invoiceId')
            if 'lancamentos' in titulo and titulo['lancamentos']:
                html += f"""
                <details>
                    <summary>Título: {invoice_id}</summary>
                    <table>
                        <thead>
                            <tr>
                                <th>Data</th>
                                <th>Operação</th>
                                <th class="valor-col">Valor</th>
                                <th>Comentários</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                for lanc in titulo['lancamentos']:
                    html += f"""
                        <tr>
                            <td>{lanc.get('entryDate', '-')}</td>
                            <td>{lanc.get('operationDescription', '-')}</td>
                            <td class="valor-col">{format_currency(float(lanc.get('value', 0)))}</td>
                            <td>{clean_html(lanc.get('comments', '-'))}</td>
                        </tr>
                    """
                html += "</tbody></table></details>"
            else:
                html += f"<details><summary>Título: {invoice_id} (Sem lançamentos detalhados)</summary></details>"
    html += "</div>"

    # --- Rodapé e Fim do HTML ---
    data_geracao = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
    html += f"""
        <footer>
            <p>Relatório gerado em {data_geracao}</p>
        </footer>
    </div>
</body>
</html>
    """
    return html

def main():
    """
    Função principal que solicita o ID do aluno, gera o relatório HTML e o abre no navegador.
    """
    print("--- 🚀 Iniciando Consulta Financeira Completa ---")
    load_dotenv()
    
    api_url = os.getenv("SOLIS_API_URL")
    jwt_token = os.getenv("SOLIS_JWT_TOKEN")

    if not api_url or not jwt_token:
        print("❌ ERRO: Defina SOLIS_API_URL e SOLIS_JWT_TOKEN no ficheiro .env")
        return

    cliente_solis = SolisAPIClient(api_url, jwt_token)
    
    while True:
        person_id = input("➡️  Digite o ID do aluno para a consulta (ou 'sair' para terminar): ").strip()
        
        if person_id.lower() == 'sair':
            break
        
        if not person_id.isdigit():
            print("❌ ID inválido. Por favor, digite apenas números.")
            continue

        print(f"\n🔎 Buscando todos os dados para o aluno ID: {person_id}...")
        
        dados_contrato = cliente_solis.consultar_dados_contrato(person_id)
        dados_financeiros = cliente_solis.consultar_financeiro_aluno(person_id)

        if not dados_contrato and not dados_financeiros:
            print(f"❌ Nenhum dado (contrato ou financeiro) foi encontrado para o aluno com ID {person_id}.")
        else:
            print("✅ Dados encontrados. Gerando relatório HTML...")
            html_content = gerar_relatorio_html(person_id, dados_contrato, dados_financeiros)
            
            filename = f"relatorio_{person_id}.html"
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                print(f"📄 Relatório gerado com sucesso: {filename}")
                
                # Abre o arquivo no navegador
                filepath = os.path.realpath(filename)
                webbrowser.open('file://' + filepath)
                print("✅ Relatório aberto no seu navegador.")

            except Exception as e:
                print(f"❌ Ocorreu um erro ao salvar ou abrir o arquivo: {e}")

    print("\n--- ✅ Operação Concluída ---")

if __name__ == '__main__':
    main()

