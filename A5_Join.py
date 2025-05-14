import os
import json
import gspread
import pandas as pd
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from oauth2client.service_account import ServiceAccountCredentials

# 🔐 Lê o segredo e salva como credentials.json
gdrive_credentials = os.getenv("GDRIVE_SERVICE_ACCOUNT")
with open("credentials.json", "w") as f:
    json.dump(json.loads(gdrive_credentials), f)

# 📌 Autenticação com Google
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# ID da pasta no Google Drive
pasta_id = "1p5NgTPjx-CtTlA6pElc7hmCSKX-ebd4l"

# Nome da planilha final que será sobrescrita
nome_planilha_saida = "Financeiro_Completo_Laurinha"

# Função para ler uma planilha pelo nome dentro de uma pasta
def ler_planilha_por_nome(nome_arquivo, pasta_id):
    arquivos = client.list_spreadsheet_files_in_folder(pasta_id)
    for arquivo in arquivos:
        if arquivo['name'] == nome_arquivo:
            planilha = client.open_by_key(arquivo['id'])
            aba = planilha.sheet1  # Primeira aba
            df = get_as_dataframe(aba).dropna(how="all")
            return df
    raise FileNotFoundError(f"Arquivo '{nome_arquivo}' não encontrado na pasta.")

# Lê os dados das planilhas
df_receber = ler_planilha_por_nome("Financeiro_contas_a_receber_Laurinha", pasta_id)
df_pagar = ler_planilha_por_nome("Financeiro_contas_a_pagar_Laurinha", pasta_id)
df_pagamento = ler_planilha_por_nome("Detalhe_centro_pagamento", pasta_id)
df_recebimento = ler_planilha_por_nome("Detalhe_centro_recebimento", pasta_id)

df_receber["tipo"] = "receber"
df_pagar["tipo"] = "pagar"
df_completo = pd.concat([df_receber, df_pagar], ignore_index=True)

# 1º join com Detalhe_centro_pagamento usando financialEvent.id
df_merge = df_completo.merge(
    df_pagamento,
    how="left",
    left_on="financialEvent.id",
    right_on="id",
    suffixes=('', '_detalhe_pagamento')
)

# Filtra os que ainda não foram encontrados (onde campos de detalhe estão nulos)
nao_encontrados = df_merge[df_merge['id_detalhe_pagamento'].isna()].copy()

# 2º join com Detalhe_centro_recebimento usando financialEvent.id
df_enriquecido = nao_encontrados.drop(columns=[col for col in df_pagamento.columns if col != 'id'])
df_enriquecido = df_enriquecido.merge(
    df_recebimento,
    how='left',
    left_on="financialEvent.id",
    right_on="id",
    suffixes=('', '_detalhe_recebimento')
)

# Atualiza as linhas originais com os detalhes de recebimento
df_merge.update(df_enriquecido)

# 📄 Abrir a planilha de saída (já existente)
arquivos = client.list_spreadsheet_files_in_folder(pasta_id)
planilha_saida = None
for arquivo in arquivos:
    if arquivo['name'] == nome_planilha_saida:
        planilha_saida = client.open_by_key(arquivo['id'])
        break

if not planilha_saida:
    raise FileNotFoundError(f"A planilha de saída '{nome_planilha_saida}' não foi encontrada na pasta.")

# Limpa a aba e sobrescreve
aba_saida = planilha_saida.sheet1
aba_saida.clear()
set_with_dataframe(aba_saida, df_merge)

print("✅ Planilha sobrescrita com sucesso.")
