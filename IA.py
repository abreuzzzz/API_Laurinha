import pandas as pd
import openai
import os

# Configurar sua API Key do OpenAI (recomendo usar variável de ambiente)
client = OpenAI(api_key="sk-0ac91b811ec149b48546f44fcf1ba9b5", base_url="https://api.deepseek.com")

# URL da sua planilha Google Sheets exportada como CSV
sheet_id = "1F2juE74EInlz3jE6JSOetSgXNAiWPAm7kppzaPqeE4A"
sheet_csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"

# Ler a planilha do Google Sheets
df = pd.read_csv(sheet_csv_url)

# Limpeza dos valores monetários
def limpar_valores(col):
    return (
        col.astype(str)
           .str.replace(r"[^\d,.-]", "", regex=True)
           .str.replace(".", "", regex=False)
           .str.replace(",", ".", regex=False)
           .pipe(pd.to_numeric, errors="coerce")
    )

df['unpaid'] = limpar_valores(df['unpaid'])
df['paid'] = limpar_valores(df['paid'])

# Gerar resumo simples
total_pago = df['paid'].sum()
total_pendente = df['unpaid'].sum()
top_categorias = df['Categoria'].value_counts().head(3).to_dict()

# Criar prompt para IA generativa
prompt = f"""
Sou um analista financeiro. Com base nesses dados:
- Total pago: R$ {total_pago:,.2f}
- Total pendente: R$ {total_pendente:,.2f}
- Top 3 categorias mais frequentes: {top_categorias}

Me dê insights relevantes e sugestões de ação com base nesses números.
"""

# Chamar o GPT-4 Turbo para gerar insights
response = openai.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "Você é um analista financeiro experiente."},
        {"role": "user", "content": prompt}
    ],
    temperature=1.0
)

# Mostrar insights
print("=== INSIGHTS GERADOS ===")
print(response.choices[0].message.content)
