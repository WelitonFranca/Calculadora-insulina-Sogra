import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from fpdf import FPDF
import pytz
import os
import urllib.parse

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Calculadora Insulina", page_icon="💉")

# --- PARÂMETROS FIXOS ---
ALVO = 100
FATOR_SENSIBILIDADE = 40
ARQUIVO_DB = "dados_glicemia.csv" # Nome do nosso banco de dados

# --- FUNÇÕES DE BANCO DE DADOS (PERSISTÊNCIA) ---
def carregar_dados():
    """Lê o arquivo CSV se ele existir, senão cria um vazio"""
    if os.path.exists(ARQUIVO_DB):
        return pd.read_csv(ARQUIVO_DB)
    else:
        return pd.DataFrame(columns=["Data", "Glicemia", "Carbos", "ICR", "Dose"])

def salvar_registro(novo_dado):
    """Adiciona uma nova linha e salva no arquivo"""
    df = carregar_dados()
    novo_df = pd.DataFrame([novo_dado])
    df_final = pd.concat([df, novo_df], ignore_index=True)
    df_final.to_csv(ARQUIVO_DB, index=False)
    return df_final

def atualizar_banco(df_atualizado):
    """Salva o banco inteiro (usado após excluir linhas)"""
    df_atualizado.to_csv(ARQUIVO_DB, index=False)

# --- FUNÇÃO: GERAR PDF ---
def gerar_pdf(df_historico):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "Relatorio de Controle Glicemico", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(10)

    if os.path.exists("grafico_temp.png"):
        pdf.image("grafico_temp.png", x=10, y=40, w=190)
        pdf.ln(100)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(40, 10, "Data/Hora", 1)
    pdf.cell(30, 10, "Glicemia", 1)
    pdf.cell(30, 10, "Carbos", 1)
    pdf.cell(30, 10, "ICR", 1)
    pdf.cell(30, 10, "Dose", 1)
    pdf.ln()
    
    pdf.set_font("Arial", size=10)
    for index, row in df_historico.iterrows():
        pdf.cell(40, 10, str(row['Data']), 1)
        pdf.cell(30, 10, str(row['Glicemia']), 1)
        pdf.cell(30, 10, str(row['Carbos']), 1)
        pdf.cell(30, 10, str(row['ICR']), 1)
        pdf.cell(30, 10, str(row['Dose']), 1)
        pdf.ln()
        
    pdf.output("relatorio_final.pdf")

# --- INTERFACE PRINCIPAL ---
st.title("💉 Controle de Insulina")
st.markdown(f"**Configuração:** Alvo {ALVO} | Sensibilidade {FATOR_SENSIBILIDADE}")

# --- ENTRADA DE DADOS ---
st.write("---")
col1, col2 = st.columns(2)

with col1:
    glicemia = st.number_input("Glicemia Atual (mg/dL)", min_value=0, max_value=600, value=100)

with col2:
    carbos = st.number_input("Carboidratos (g)", min_value=0, max_value=300, value=0)

st.write("Escolha o Fator (ICR):")
icr = st.radio("Quantos gramas 1 unidade cobre?", [8, 10, 15], horizontal=True)

# --- CÁLCULO ---
if st.button("CALCULAR DOSE", type="primary", use_container_width=True):
    if glicemia > ALVO:
        correcao = (glicemia - ALVO) / FATOR_SENSIBILIDADE
    else:
        correcao = 0
    
    refeicao = carbos / icr
    dose_total = correcao + refeicao
    dose_final = round(dose_total)
    
    st.markdown("---")
    
    if glicemia < 70:
        st.error("⚠️ HIPOGLICEMIA! Não aplique insulina. Coma 15g de açúcar.")
    else:
        st.success(f"## Dose Recomendada: {dose_final} Unidades")
        with st.expander("Ver detalhes do cálculo"):
            st.write(f"🔹 Correção: {correcao:.2f} u")
            st.write(f"🔹 Comida: {refeicao:.2f} u")
            st.write(f"🔹 Total exato: {dose_total:.2f} u")

        # SALVAR NO ARQUIVO (PERSISTÊNCIA)
        fuso_br = pytz.timezone('America/Sao_Paulo')
        data_hora_br = datetime.now(fuso_br).strftime("%d/%m %H:%M")
        
        novo_registro = {
            "Data": data_hora_br,
            "Glicemia": glicemia,
            "Carbos": carbos,
            "ICR": icr,
            "Dose": dose_final
        }
        
        salvar_registro(novo_registro)
        st.toast("✅ Dados salvos com sucesso!")

# --- ÁREA DE RELATÓRIOS ---
st.write("---")
st.subheader("📊 Histórico e Ações")

# Carrega os dados do arquivo sempre que a tela atualiza
df = carregar_dados()

if not df.empty:
    
    # --- LIXEIRA (EDIÇÃO) ---
    st.info("Para apagar, marque a caixa 'Excluir' e clique no botão vermelho.")
    
    # Adiciona coluna de controle visualmente (sem salvar no banco ainda)
    df_visual = df.copy()
    df_visual["Excluir"] = False
    
    df_editado = st.data_editor(
        df_visual,
        column_config={"Excluir": st.column_config.CheckboxColumn("Excluir?", default=False)},
        disabled=["Data", "Glicemia", "Carbos", "ICR", "Dose"],
        hide_index=True,
    )
    
    # Botão de Exclusão
    if st.button("🗑️ Apagar Linhas Marcadas"):
        # Filtra apenas o que NÃO foi marcado
        linhas_para_manter = df_editado[df_editado["Excluir"] == False]
        
        # Remove a coluna 'Excluir' antes de salvar no arquivo
        linhas_limpas = linhas_para_manter.drop(columns=["Excluir"])
        
        # Atualiza o arquivo CSV
        atualizar_banco(linhas_limpas)
        st.success("Linhas apagadas com sucesso!")
        st.rerun() # Recarrega a página para mostrar a tabela limpa

    # --- VISUALIZAÇÃO (GRÁFICO E PDF) ---
    # Só mostra se ainda tiver dados após a exclusão
    if not df.empty:
        # Gráfico
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(df['Data'], df['Glicemia'], marker='o', color='blue')
        ax.axhline(y=ALVO, color='red', linestyle='--')
        ax.set_title("Evolução")
        ax.grid(True)
        st.pyplot(fig)
        plt.savefig("grafico_temp.png")
        
        # --- BOTÕES DE EXPORTAÇÃO ---
        st.write("### 📤 Enviar Relatório")
        col_zap, col_pdf = st.columns(2)
        
        # 1. WhatsApp
        ultimo = df.iloc[-1] # Pega o último registro real do banco
        msg_zap = (f"*RELATÓRIO DE INSULINA*\n"
                   f"📅 Data: {ultimo['Data']}\n"
                   f"🩸 Glicemia: {ultimo['Glicemia']} mg/dL\n"
                   f"🍞 Carbos: {ultimo['Carbos']}g\n"
                   f"💉 *DOSE APLICADA: {ultimo['Dose']} unidades*\n"
                   f"------------------\n"
                   f"Calculado pelo App.")
        msg_encoded = urllib.parse.quote(msg_zap)
        link_zap = f"https://wa.me/?text={msg_encoded}"
        col_zap.link_button("💚 Enviar no WhatsApp", link_zap, use_container_width=True)

        # 2. PDF
        gerar_pdf(df)
        with open("relatorio_final.pdf", "rb") as pdf_file:
            col_pdf.download_button(
                label="📄 Baixar PDF (Arquivo)",
                data=pdf_file,
                file_name="relatorio_insulina.pdf",
                mime='application/pdf',
                use_container_width=True
            )

else:
    st.info("Histórico vazio. Faça um cálculo para começar.")
