import pandas as pd
import streamlit as st
from openai import OpenAI

# Inicialização da API (substitua por sua chave real)
client = OpenAI(api_key="sk-0ac91b811ec149b48546f44fcf1ba9b5", base_url="https://api.deepseek.com")

# Carregar dados da planilha Google
sheet_id = "xxx"
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

# Interface Streamlit
st.set_page_config(page_title="Pergunte à IA", layout="centered")
st.title("Pergunte à IA Financeira")

user_question = st.text_area("Escreva sua pergunta sobre os dados financeiros:")

if st.button("Perguntar"):
    if user_question.strip() == "":
        st.warning("Por favor, escreva uma pergunta.")
    else:
        # Criar contexto com base no dataframe
        preview = df.head(10).to_dict(orient="records")  # apenas amostra para o contexto

        prompt = f"""
Você é um analista financeiro. O usuário fez a seguinte pergunta:

{user_question}

Aqui está uma amostra dos dados disponíveis (cada linha é uma transação):

{preview}

As colunas são: id, Descrição, Vencimento, Tipo (Recebimento ou Pagamento), valores pagos e pendentes, status e categoria.

Com base nesses dados, responda de forma clara e objetiva.
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