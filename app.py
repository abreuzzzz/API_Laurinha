import pandas as pd
import streamlit as st
from openai import OpenAI
from datetime import datetime
import re

client = OpenAI(api_key="sua-chave-aqui", base_url="https://api.deepseek.com")

# Carregar os dados
sheet_id = "1F2juE74EInlz3jE6JSOetSgXNAiWPAm7kppzaPqeE4A"
sheet_csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
df = pd.read_csv(sheet_csv_url)

# Limpar colunas
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
df['Vencimento'] = pd.to_datetime(df['Vencimento'], errors='coerce')

# Filtros fixos
hoje = pd.Timestamp.today()
df_filtrado = df[~((df['Tipo'] == 'Pagamento') & (df['Vencimento'] > hoje) & (df['unpaid'] > 0))]

# Interface
st.set_page_config(page_title="IA Financeira", layout="centered")
st.title("Pergunte à IA sobre seus dados financeiros")

user_question = st.text_area("Faça sua pergunta:")

# Função para extrair mês ou categoria da pergunta
def extrair_filtros(texto):
    filtros = {}
    
    # Mês (ex: março, abril etc.)
    match_mes = re.search(r"(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)", texto, re.IGNORECASE)
    if match_mes:
        nome_mes = match_mes.group(1).lower()
        mes_map = {'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4, 'maio': 5, 'junho': 6,
                   'julho': 7, 'agosto': 8, 'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12}
        filtros['mes'] = mes_map[nome_mes]

    # Categoria (ex: Transporte, Alimentação etc.)
    categorias = df_filtrado['Categoria'].dropna().unique().tolist()
    for cat in categorias:
        if isinstance(cat, str) and cat.lower() in texto.lower():
            filtros['categoria'] = cat
            break

    return filtros

# Processar pergunta
if st.button("Perguntar"):
    if user_question.strip() == "":
        st.warning("Digite uma pergunta primeiro.")
    else:
        filtros = extrair_filtros(user_question)
        df_contexto = df_filtrado.copy()

        if 'mes' in filtros:
            df_contexto = df_contexto[df_contexto['Vencimento'].dt.month == filtros['mes']]
        if 'categoria' in filtros:
            df_contexto = df_contexto[df_contexto['Categoria'] == filtros['categoria']]

        # Reduzir volume para evitar estouro de tokens
        df_resumo = df_contexto[['Descrição', 'Vencimento', 'Tipo', 'paid', 'unpaid', 'Categoria', 'Status']].tail(50)
        json_data = df_resumo.to_dict(orient='records')

        prompt = f"""
Você é um analista financeiro. O usuário fez a seguinte pergunta: {user_question}

Aqui estão transações relevantes extraídas da base de dados (máx. 50):

{json_data}

Cada linha tem:
- descrição (nome do item)
- vencimento (data)
- tipo (Recebimento ou Pagamento)
- paid: valor realizado
- unpaid: valor pendente
- categoria: tipo de gasto ou receita
- status: realizado ou vencido

Responda de forma clara e objetiva com base nessas transações.
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
