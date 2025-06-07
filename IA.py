import json
import pandas as pd
from openai import OpenAI
import os
from datetime import datetime
import gspread
from gspread_dataframe import set_with_dataframe
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2.service_account import Credentials

# Configurar API Key do DeepSeek
client = OpenAI(api_key="sk-0ac91b811ec149b48546f44fcf1ba9b5", base_url="https://api.deepseek.com")

# IDs das planilhas
sheet_id = "1jTuY_4wcegFjkt_e4dV2ZoM_7ZIUSlpZIGgZ-sNr7o4"
sheet_csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
SHEET_ID2 = "1jsZRht1ENIfamTMyZcQFm-V-HybkwpAxU8BRHav_zWs"

# Carregar dados
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

# Conversão segura de datas
def parse_data_segura(coluna):
    datas = pd.to_datetime(
        coluna.apply(lambda x: '-'.join(x.split('-')[:3]) if isinstance(x, str) and '-' in x else None),
        format='%Y-%m-%d',
        errors='coerce'
    )
    return datas

df['lastAcquittanceDate'] = parse_data_segura(df['lastAcquittanceDate'])
df['dueDate'] = parse_data_segura(df['dueDate'])

# Filtrar por ano corrente
ano_corrente = datetime.today().year
df = df[df['lastAcquittanceDate'].dt.year == ano_corrente]

# Colunas auxiliares
df['AnoMes'] = df['lastAcquittanceDate'].dt.to_period('M')
df['Trimestre'] = df['lastAcquittanceDate'].dt.to_period('Q')
df['AnoMes_Caixa'] = df['lastAcquittanceDate'].dt.to_period('M')
df['Trimestre_Caixa'] = df['lastAcquittanceDate'].dt.to_period('Q')

# Resumo trimestral
resumo_trimestral = df.groupby(['Trimestre', 'tipo'])[['categoriesRatio.value', 'unpaid']].sum().unstack(fill_value=0)

# Variação mensal por categoria
resumo_mensal_categoria = df.groupby(['AnoMes', 'categoriesRatio.category'])['categoriesRatio.value'].sum().unstack(fill_value=0)
variacao_mensal_pct = resumo_mensal_categoria.pct_change().fillna(0)
categorias_com_alta = (variacao_mensal_pct > 0.3).apply(lambda row: row[row > 0.3].to_dict(), axis=1).to_dict()
categorias_com_alta_str = json.dumps({str(k): v for k, v in categorias_com_alta.items()}, indent=2, ensure_ascii=False)

# Totais
total_recebido = df[(df['tipo'] == 'Receita') & (df['status'] == 'ACQUITTED')]['categoriesRatio.value'].sum()
total_pago = df[(df['tipo'] == 'Despesa') & (df['status'] == 'ACQUITTED')]['categoriesRatio.value'].sum()
total_pendente_despesa = df[(df['tipo'] == 'Despesa') & (df['status'] == 'OVERDUE')]['categoriesRatio.value'].sum()
total_pendente_receita = df[(df['tipo'] == 'Receita') & (df['status'] == 'OVERDUE')]['categoriesRatio.value'].sum()
saldo_liquido = total_recebido - total_pago
top_categorias = df['categoriesRatio.category'].value_counts().head(3).to_dict()
top_categorias_str = json.dumps(top_categorias, ensure_ascii=False)

# Fluxo de Caixa
hoje = pd.to_datetime(datetime.today().date())
df_realizadas = df[df['lastAcquittanceDate'] <= hoje].copy()
df_realizadas['valor_ajustado'] = df_realizadas.apply(
    lambda row: abs(row['categoriesRatio.value']) if row['tipo'] == 'Receita' else -abs(row['categoriesRatio.value']),
    axis=1
)
fluxo_caixa = df_realizadas.groupby('AnoMes_Caixa')['valor_ajustado'].sum().reset_index()
fluxo_caixa['saldo_acumulado'] = fluxo_caixa['valor_ajustado'].cumsum()
fluxo_caixa_str = fluxo_caixa.to_string(index=False)

# Rentabilidade
df_receitas = df_realizadas[df_realizadas['tipo'].str.lower() == 'receita']
df_despesas = df_realizadas[df_realizadas['tipo'].str.lower() == 'despesa']
receitas_mensais = df_receitas.groupby('AnoMes')['categoriesRatio.value'].sum().reset_index()
despesas_mensais = df_despesas.groupby('AnoMes')['categoriesRatio.value'].sum().reset_index()

rentabilidade = pd.merge(receitas_mensais, despesas_mensais, on='AnoMes', how='outer', suffixes=('_receita', '_despesa')).fillna(0)
rentabilidade['lucro'] = rentabilidade['categoriesRatio.value_receita'] - rentabilidade['categoriesRatio.value_despesa']
rentabilidade['margem_lucro'] = rentabilidade['lucro'] / rentabilidade['categoriesRatio.value_receita'].replace(0, pd.NA)
rentabilidade_str = rentabilidade.to_string(index=False)

# Pendências vencidas
df_pendentes = df[(df['unpaid'] > 0) & (df['dueDate'] <= hoje) & (df['status'] == 'OVERDUE')]
pendentes_por_tipo = df_pendentes.groupby('tipo')['unpaid'].sum().to_dict()
pendentes_por_tipo_str = json.dumps(pendentes_por_tipo, indent=2, ensure_ascii=False)

# Inadimplência
total_vencido = df_pendentes[df_pendentes['tipo'] == 'Receita']['categoriesRatio.value'].sum()
inadimplencia = total_vencido / total_recebido if total_recebido else 0

# ================== PROMPT ==================

prompt = f"""
Você é um analista financeiro sênior. Abaixo estão dados financeiros consolidados do ano corrente.

### Visão Geral:
- Total Recebido (Receita): R$ {total_recebido:,.2f}
- Total Pago (Despesa): R$ {total_pago:,.2f}
- Receita Pendente: R$ {total_pendente_receita:,.2f}
- Despesa Pendente: R$ {total_pendente_despesa:,.2f}
- Saldo Líquido: R$ {saldo_liquido:,.2f}

### Categorias e Padrões:
- Top 3 Categorias mais recorrentes: {top_categorias_str}
- Categorias com aumento mensal > 30%:
{categorias_com_alta_str}

### Resumo Trimestral (Valores Pagos e Pendentes por Tipo):
{resumo_trimestral.to_string()}

### Fluxo de Caixa Mensal:
{fluxo_caixa_str}

### Rentabilidade por Mês:
{rentabilidade_str}

### Pendências Vencidas:
- Por Tipo: {pendentes_por_tipo_str}
- Inadimplência: {inadimplencia:.2%}

---

## Instruções:

Com base nos dados fornecidos, forneça uma análise financeira executiva:

1. **Resumo Executivo**
2. **Insights Financeiros**
3. **Alertas e Riscos**
4. **Oportunidades de Otimização**
5. **Recomendações Práticas**

Seja objetivo, técnico e use estrutura clara.
"""

# Chamar a IA
response = client.chat.completions.create(
    model="deepseek-reasoner",
    messages=[
        {"role": "system", "content": "Você é um analista financeiro experiente."},
        {"role": "user", "content": prompt}
    ],
    temperature=1.0
)

# Obter conteúdo gerado
conteudo_ia = response.choices[0].message.content

# ================== EXPORTAÇÃO PARA GOOGLE SHEETS ==================

json_secret = os.getenv("GDRIVE_SERVICE_ACCOUNT")
creds_dict = json.loads(json_secret)
creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])

gc = gspread.authorize(creds)
spreadsheet = gc.open_by_key(SHEET_ID2)
worksheet = spreadsheet.get_worksheet(0)
worksheet.clear()

# Organizar texto para colunas
blocos = conteudo_ia.split("####")
dados = []

for bloco in blocos:
    bloco = bloco.strip()
    if not bloco:
        continue
    if bloco.startswith("**"):
        partes = bloco.split("**")
        if len(partes) >= 3:
            titulo = partes[1].strip()
            conteudo = partes[2].strip()
            dados.append([titulo, conteudo])

worksheet.update("A1", dados)