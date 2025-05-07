import pandas as pd
import os
from openai import OpenAI

# Sua chave de API da OpenAI (por segurança, use variável de ambiente em produção)
openai_api_key = "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"

# Conecta à API da OpenAI
client = OpenAI(api_key=openai_api_key)

# Link do Google Sheets em formato CSV
sheet_csv_url = "https://docs.google.com/spreadsheets/d/1F2juE74EInlz3jE6JSOetSgXNAiWPAm7kppzaPqeE4A/export?format=csv"

# Lê os dados
df = pd.read_csv(sheet_csv_url)

# Conversões e limpeza
df.columns = df.columns.str.strip()
df['Vencimento'] = pd.to_datetime(df['Vencimento'], errors='coerce')
df['unpaid'] = df['unpaid'].replace('R$ ', '', regex=True).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).astype(float)
df['paid'] = df['paid'].replace('R$ ', '', regex=True).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).astype(float)

# Resumo numérico
total_recebido = df[df["Tipo"] == "Recebimento"]["paid"].sum()
total_pendente = df[df["status"] != "ACQUITTED"]["unpaid"].sum()
gastos_categoria = df.groupby("Categoria")["paid"].sum().sort_values(ascending=False).head(5)

# Monta prompt
prompt = f"""
Você é um analista financeiro. Abaixo está um resumo dos dados de recebimentos e pagamentos de uma empresa:

- Total recebido: R$ {total_recebido:,.2f}
- Total pendente: R$ {total_pendente:,.2f}
- Categorias com mais pagamentos:
{gastos_categoria.to_string()}

Com base nisso, gere insights em linguagem natural. Aponte padrões, possíveis riscos ou oportunidades de otimização.
"""

# Chamada ao modelo GPT-4
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "Você é um assistente financeiro que ajuda a interpretar dados."},
        {"role": "user", "content": prompt}
    ],
    temperature=0.7
)

# Exibe resposta
print("🔍 Insights gerados pela IA:\n")
print(response.choices[0].message.content)
