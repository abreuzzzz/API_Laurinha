import pandas as pd
import streamlit as st
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain.chat_models import ChatOpenAI
from openai import OpenAI
from datetime import datetime

# Chave da API (OpenAI ou DeepSeek)
deepseek_api_key = "sk-0ac91b811ec149b48546f44fcf1ba9b5"  # substitua pela sua chave da DeepSeek
deepseek_base_url = "https://api.deepseek.com"  # URL base correta

# Carregar planilha do Google Sheets
sheet_id = "1F2juE74EInlz3jE6JSOetSgXNAiWPAm7kppzaPqeE4A"
csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
df = pd.read_csv(csv_url)

# Limpeza dos valores
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

# Interface Streamlit
st.set_page_config(page_title="Consultor Financeiro IA", layout="centered")
st.title("Pergunte sobre suas finanças 💰📊")

pergunta = st.text_area("Faça sua pergunta sobre os dados:", height=100)

# Botão
if st.button("Responder"):
    if not pergunta.strip():
        st.warning("Digite uma pergunta.")
    else:
        # Criar agente LangChain com Pandas
        agent = create_pandas_dataframe_agent(
            ChatOpenAI(
                model_name="deepseek-chat",
                temperature=0,
                openai_api_key=deepseek_api_key,
                base_url=deepseek_base_url,
            ),
            df,
            verbose=True,
            allow_dangerous_code=True
        )

        with st.spinner("Pensando..."):
            try:
                resposta = agent.run(pergunta)
                st.success("Resposta:")
                st.write(resposta)
            except Exception as e:
                st.error(f"Erro ao responder: {e}")
