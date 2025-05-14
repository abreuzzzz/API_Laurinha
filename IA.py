import pandas as pd
from openai import OpenAI
import os
from datetime import datetime

# Configurar sua API Key do OpenAI
client = OpenAI(api_key="sk-0ac91b811ec149b48546f44fcf1ba9b5", base_url="https://api.deepseek.com")

# URL da planilha Google Sheets exportada como CSV
sheet_id = "1jTuY_4wcegFjkt_e4dV2ZoM_7ZIUSlpZIGgZ-sNr7o4"
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
df['categoriesRatio.value'] = limpar_valores(df['categoriesRatio.value'])

# Converter coluna de data
df['financialEvent.competenceDate'] = pd.to_datetime(df['financialEvent.competenceDate'])

# Criar colunas auxiliares
df['AnoMes'] = df['financialEvent.competenceDate'].dt.to_period('M')
df['Trimestre'] = df['financialEvent.competenceDate'].dt.to_period('Q')

# Resumo trimestral: valores pagos e pendentes por tipo
resumo_trimestral = df.groupby(['Trimestre', 'tipo'])[['paid', 'unpaid']].sum().unstack(fill_value=0)

# Variação mensal por categoria
resumo_mensal_categoria = df.groupby(['AnoMes', 'categoriesRatio.category'])['paid'].sum().unstack(fill_value=0)
variacao_mensal_pct = resumo_mensal_categoria.pct_change().fillna(0)
categorias_com_alta = (variacao_mensal_pct > 0.3).apply(lambda row: row[row > 0.3].to_dict(), axis=1).to_dict()

# Valores totais
total_recebido = df[
    (df['tipo'] == 'Receita') & (df['status'] == 'ACQUITTED')
]['categoriesRatio.value'].sum()
total_pago = df[
    (df['tipo'] == 'Despesa') & (df['status'] == 'ACQUITTED')
]['categoriesRatio.value'].sum()
total_pendente = df['unpaid'].sum()
saldo_liquido = total_recebido - total_pago
top_categorias = df['categoriesRatio.category'].value_counts().head(3).to_dict()

# ================= CÁLCULOS COMPLEMENTARES ===================

# Filtrar transações realizadas
hoje = pd.to_datetime(datetime.today().date())
df_realizadas = df[(df['financialEvent.competenceDate'] <= hoje) & (df['categoriesRatio.value'] > 0)].copy()

# Ajustar valores: receitas positivas, despesas negativas
df_realizadas['valor_ajustado'] = df_realizadas.apply(
    lambda row: row['categoriesRatio.value'] if row['tipo'].lower() == 'Receita' else -row['categoriesRatio.value'], axis=1
)

# Fluxo de Caixa
fluxo_caixa = df_realizadas.groupby('AnoMes')['valor_ajustado'].sum().reset_index()
fluxo_caixa['saldo_acumulado'] = fluxo_caixa['valor_ajustado'].cumsum()

# Receitas e despesas por mês
df_receitas = df_realizadas[df_realizadas['tipo'].str.lower() == 'Receita']
df_despesas = df_realizadas[df_realizadas['tipo'].str.lower() == 'Despesa']

receitas_mensais = df_receitas.groupby('AnoMes')['categoriesRatio.value'].sum().reset_index()
despesas_mensais = df_despesas.groupby('AnoMes')['categoriesRatio.value'].sum().reset_index()

# Rentabilidade
rentabilidade = pd.merge(
    receitas_mensais,
    despesas_mensais,
    on='AnoMes',
    how='outer',
    suffixes=('_receita', '_despesa')
).fillna(0)

rentabilidade['lucro'] = rentabilidade['categoriesRatio.value_receita'] - rentabilidade['categoriesRatio.value_despesa']
rentabilidade['margem_lucro'] = rentabilidade['lucro'] / rentabilidade['categoriesRatio.value_receita'].replace(0, pd.NA)

# Pendências e vencidos
df_pendentes = df[(df['unpaid'] > 0) & (df['financialEvent.competenceDate'] <= hoje)]
pendentes_por_tipo = df_pendentes.groupby('tipo')['unpaid'].sum().to_dict()

# Inadimplência
total_vencido = df_pendentes[df_pendentes['tipo'] == 'Receita']['unpaid'].sum()
inadimplencia = total_vencido / total_recebido if total_recebido else 0

# Prompt detalhado
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

5. Fluxo de caixa mensal, me de também o mês a mês:
{fluxo_caixa.to_string(index=False)}

6. Rentabilidade mensal (lucro e margem de lucro):
{rentabilidade[['AnoMes', 'lucro', 'margem_lucro']].to_string(index=False)}

7. Pendências vencidas por tipo:
{pendentes_por_tipo}

8. Inadimplência (proporção de valores vencidos sobre receitas realizadas): {inadimplencia:.2%}

Considere que:
- Transações com status "ACQUITTED" já foram quitadas.
- O campo 'tipo' indica se é uma entrada ("Receita") ou saída ("Despesa").
- 'paid' são os valores já pagos ou recebidos.
- 'unpaid' são valores ainda pendentes.

Por favor, me forneça:
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
