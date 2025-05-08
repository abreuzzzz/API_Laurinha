import pandas as pd
import streamlit as st
from openai import OpenAI
from datetime import datetime

# Inicialização da API
client = OpenAI(api_key="sk-0ac91b811ec149b48546f44fcf1ba9b5", base_url="https://api.deepseek.com")

# Carregar dados da planilha
sheet_id = "1F2juE74EInlz3jE6JSOetSgXNAiWPAm7kppzaPqeE4A"
sheet_csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
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
df['Vencimento'] = pd.to_datetime(df['Vencimento'])

# Cálculos auxiliares
hoje = pd.Timestamp.today()
df_filtrado = df[~((df['Tipo'] == 'Pagamento') & (df['Vencimento'] > hoje) & (df['unpaid'] > 0))]

df_filtrado['AnoMes'] = df_filtrado['Vencimento'].dt.to_period('M')
df_filtrado['Trimestre'] = df_filtrado['Vencimento'].dt.to_period('Q')

resumo_trimestral = df_filtrado.groupby(['Trimestre', 'Tipo'])[['paid', 'unpaid']].sum().unstack(fill_value=0)
resumo_mensal_categoria = df_filtrado.groupby(['AnoMes', 'Categoria'])['paid'].sum().unstack(fill_value=0)
variacao_mensal_pct = resumo_mensal_categoria.pct_change().fillna(0)
categorias_com_alta = (variacao_mensal_pct > 0.3).apply(lambda row: row[row > 0.3].to_dict(), axis=1).to_dict()

total_recebido = df_filtrado[df_filtrado['Tipo'] == 'Recebimento']['paid'].sum()
total_pago = df_filtrado[df_filtrado['Tipo'] == 'Pagamento']['paid'].sum()
total_pendente = df_filtrado['unpaid'].sum()
saldo_liquido = total_recebido - total_pago
top_categorias = df_filtrado['Categoria'].value_counts().head(3).to_dict()
resumo_mensal_recebimentos = df_filtrado[df_filtrado['Tipo'] == 'Recebimento'].groupby(df_filtrado['Vencimento'].dt.to_period('M'))['paid'].sum()
resumo_mensal_pagamentos = df_filtrado[df_filtrado['Tipo'] == 'Pagamento'].groupby(df_filtrado['Vencimento'].dt.to_period('M'))['paid'].sum()

# Interface Streamlit
st.set_page_config(page_title="Pergunte à IA", layout="centered")
st.title("Pergunte à Soc.ia")

user_question = st.text_area("Escreva sua pergunta sobre os dados financeiros:")

if st.button("Perguntar"):
    if user_question.strip() == "":
        st.warning("Por favor, escreva uma pergunta.")
    else:
        prompt = f"""
Você é um analista financeiro sênior. O usuário fez a seguinte pergunta: {user_question}

Aqui estão dados financeiros agregados:
1. Visão geral:
- Total recebido: R$ {total_recebido:,.2f}
- Total pago: R$ {total_pago:,.2f}
- Total pendente: R$ {total_pendente:,.2f}
- Saldo líquido: R$ {saldo_liquido:,.2f}

2. Top 3 categorias mais frequentes: {top_categorias}

3. Resumo trimestral (valores pagos e pendentes por tipo de transação):
{resumo_trimestral.to_string()}

4. Categorias com aumentos mensais significativos (>30%):
{categorias_com_alta}

Considere:
- Transações com status "ACQUITTED" já foram quitadas.
- Tipo = 'Recebimento' (significa receita, entrada, receita) ou 'Pagamento'(significa despesa, saida, pagamento).
- paid = valores realizados.
- unpaid = valores pendentes.

5. Recebimentos mensais:
{resumo_mensal_recebimentos.to_string()}

5. Pagamentos mensais:
{resumo_mensal_pagamentos.to_string()}


Responda de forma clara e objetiva.
        """

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "Você é um analista financeiro experiente."},
                {"role": "user", "content": prompt}
            ],
            temperature=1.0
        )

        resposta = response.choices[0].message.content
        st.markdown("### Resposta da IA")
        st.write(resposta)
