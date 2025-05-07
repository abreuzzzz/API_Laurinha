import pandas as pd
import requests
import openai
import re

# === CONFIGURAÇÃO ===
sheet_csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQPWhsfQw8myiwFMtIuMRu8JHqx0gXaaJ7bhhIUGpMdNIGJcRtnGMPvDLBfVi29vEBW80r-Yo4BvQvK/pub?output=csv"
openai.api_key = "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"  # Substitua pela sua chave

# === 1. Ler e limpar os dados ===
df = pd.read_csv(sheet_csv_url)

# Remove "R$" e converte colunas para float
def parse_money(value):
    if isinstance(value, str):
        value = value.replace("R$", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(value)
    except:
        return 0.0

df["unpaid"] = df["unpaid"].apply(parse_money)
df["paid"] = df["paid"].apply(parse_money)

# Filtra colunas úteis para análise
df_filtered = df[["Descrição", "Vencimento", "Tipo", "unpaid", "paid", "status", "Categoria"]].copy()

# Limita para 100 linhas (caso o prompt fique grande)
df_sample = df_filtered.head(10000)

# === 2. Preparar o prompt para a IA ===
data_text = df_sample.to_csv(index=False)

prompt = f"""
Você é um analista financeiro.

Abaixo estão registros de pagamentos e recebimentos de uma empresa. Cada linha contém:
- Descrição da transação
- Data de vencimento
- Tipo (Pagamento ou Recebimento)
- Valor ainda não pago (unpaid)
- Valor já pago (paid)
- Status (ACQUITTED = pago, OVERDUE = vencido e não pago, PENDING = ainda não pago)
- Categoria (ex: tarifas, serviços, vendas etc.)

Dados (formato CSV):

{data_text}

Com base nesses dados, forneça insights úteis de negócios, como:
- Categorias com maiores gastos ou receitas no mês anterior e no mês atual
- Tendência de inadimplência (status OVERDUE ou PENDING)
- Valor total ainda a receber ou pagar
- Análise de fluxo de caixa por tipo e categoria
- Recomendações práticas para gestão financeira

Seja direto, claro e objetivo.
"""

# === 3. Chamar a OpenAI ===
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.6,
    max_tokens=700
)

# === 4. Exibir insights no Power BI ===
insights = response['choices'][0]['message']['content']
print(insights)
