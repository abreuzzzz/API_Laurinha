import pandas as pd
from openai import OpenAI
import os

# Configurar sua API Key do OpenAI
client = OpenAI(api_key="sk-0ac91b811ec149b48546f44fcf1ba9b5", base_url="https://api.deepseek.com")

# URL da planilha Google Sheets exportada como CSV
sheet_id = "1F2juE74EInlz3jE6JSOetSgXNAiWPAm7kppzaPqeE4A"
sheet_csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"

# Ler a planilha
df = pd.read_csv(sheet_csv_url)

# Limpar valores monetários
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

# Converter coluna de data
df['Vencimento'] = pd.to_datetime(df['Vencimento'])

# Criar colunas auxiliares
df['AnoMes'] = df['Vencimento'].dt.to_period('M')
df['Trimestre'] = df['Vencimento'].dt.to_period('Q')

# Resumo trimestral: valores pagos e pendentes por tipo
resumo_trimestral = df.groupby(['Trimestre', 'Tipo'])[['paid', 'unpaid']].sum().unstack(fill_value=0)

# Variação mensal por categoria
resumo_mensal_categoria = df.groupby(['AnoMes', 'Categoria'])['paid'].sum().unstack(fill_value=0)
variacao_mensal_pct = resumo_mensal_categoria.pct_change().fillna(0)
categorias_com_alta = (variacao_mensal_pct > 0.3).apply(lambda row: row[row > 0.3].to_dict(), axis=1).to_dict()

# Valores totais
total_recebido = df[df['Tipo'] == 'Recebimento']['paid'].sum()
total_pago = df[df['Tipo'] == 'Pagamento']['paid'].sum()
total_pendente = df['unpaid'].sum()
saldo_liquido = total_recebido - total_pago
top_categorias = df['Categoria'].value_counts().head(3).to_dict()

# Criar prompt detalhado
prompt = f"""
Você é um analista financeiro sênior. Recebi um extrato financeiro com as seguintes informações agregadas:

1. Visão geral:
- Total recebido (entradas): R$ {total_recebido:,.2f}
- Total pago (saídas): R$ {total_pago:,.2f}
- Total pendente (a pagar ou a receber): R$ {total_pendente:,.2f}
- Saldo líquido (entradas - saídas): R$ {saldo_liquido:,.2f}

2. Top 3 categorias mais frequentes: {top_categorias}

3. Resumo trimestral (valores pagos e pendentes por tipo de transação):
{resumo_trimestral.to_string()}

4. Categorias com aumentos mensais significativos (acima de 30% de um mês para o outro):
{categorias_com_alta}

Considere que:
- Transações com status "ACQUITTED" já foram quitadas.
- O campo 'Tipo' indica se é uma entrada ("Recebimento") ou saída ("Pagamento").
- 'paid' são os valores já pagos ou recebidos.
- 'unpaid' são valores ainda pendentes.

Por favor, me forneça:
- Para o seu estudo, desconsidere as linhas de pagamento que estão no futuro e como pendente (a partir de hoje).
- Insights sobre a saúde financeira e tendências.
- Sinais de alerta (pendências, desequilíbrios).
- Oportunidades de otimização (redução de custos ou melhoria na previsibilidade).
- Recomendações práticas com base no histórico recente (por trimestre e por categoria).

Seja objetivo, claro e direto.
"""

# Chamar a IA
response = client.chat.completions.create(
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
