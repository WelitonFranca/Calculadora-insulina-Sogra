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
ARQUIVO_DB = "dados_glicemia.csv"

# --- FUNÇÕES DE BANCO DE DADOS ---
def carregar_dados():
    if os.path.exists(ARQUIVO_DB):
        return pd.read_csv(ARQUIVO_DB)
    else:
        return pd.DataFrame(columns=["Data", "Glicemia", "Carbos", "ICR", "Dose"])

def salvar_registro(novo_dado):
    df = carregar_dados()
    novo_df = pd.DataFrame([novo_dado])
    df_final = pd.concat([df, novo_df], ignore_index=True)
    df_final.to_csv(ARQUIVO_DB, index=False)
    return df_final

def atualizar_banco(df_atualizado):
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

# --- BARRA LATERAL (COFRE DE SEGURANÇA) ---
with st.sidebar:
    st.header("📂 Segurança dos Dados")
    st.info("Se o app atualizar, use este botão para carregar seus dados antigos.")
    
    # Botão de Upload (Restaurar)
    arquivo_upload = st.file_uploader("Restaurar Backup (CSV)", type=["csv"])
    if arquivo_upload is not None:
        try:
            df_restaurado = pd.read_csv(arquivo_upload)
            atualizar_banco(df_restaurado)
            st.success("✅ Histórico restaurado!")
        except:
            st.error("Erro ao ler arquivo.")

st.markdown(f"**Configuração:** Alvo {ALVO} | Sensibilidade {FATOR_SENSIBILIDADE}")

# --- ENTRADA DE DADOS ---
st.write("---")
st.subheader("1. Dados da Medição")

# Colunas para Glicemia e Carbos
col1, col2 = st.columns(2)
with col1:
    glicemia = st.number_input("Glicemia (mg/dL)", min_value=0, max_value=600, value=100)
with col2:
    carbos = st.number_input("Carboidratos (g)", min_value=0, max_value=300, value=0)

# --- NOVA SEÇÃO: DATA E HORA ---
st.write("Quando foi essa medição?")
col_data, col_hora = st.columns(2)

# Pega a hora atual de Brasília para preencher o padrão
fuso_br = pytz.timezone('America/Sao_Paulo')
agora = datetime.now(fuso_br)

with col_data:
    data_input = st.date_input("Data", value=agora)
with col_hora:
    hora_input = st.time_input("Hora", value=agora)

# --- SELEÇÃO DE ICR ---
st.write("---")
st.subheader("2. Configuração")
lista_opcoes = list(range(1, 21))
icr = st.selectbox("Fator ICR (Quantos gramas 1 unidade cobre?)", options=lista_opcoes, index=9)

# --- CÁLCULO ---
if st.button("CALCULAR E SALVAR", type="primary", use_container_width=True):
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

        # SALVAR NO ARQUIVO (USANDO A DATA/HORA ESCOLHIDA)
        # Combina a data e hora escolhidas pelo usuário
        data_completa = datetime.combine(data_input, hora_input)
        data_formatada = data_completa.strftime("%d/%m %H:%M")
        
        novo_registro = {
            "Data": data_formatada,
            "Glicemia": glicemia,
            "Carbos": carbos,
            "ICR": icr,
            "Dose": dose_final
        }
        
        salvar_registro(novo_registro)
        st.toast("✅ Dados salvos com a data selecionada!")

# --- ÁREA DE RELATÓRIOS ---
st.write("---")
st.subheader("📊 Histórico e Ações")

df = carregar_dados()

if not df.empty:
    
    # --- BOTÃO DE BACKUP ---
    st.warning("💾 **Dica:** Baixe o backup regularmente.")
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="💾 BAIXAR BACKUP (Salvar no Celular)",
        data=csv,
        file_name="backup_insulina.csv",
        mime="text/csv",
        type="secondary"
    )
    
    st.write("---")

    # --- LIXEIRA ---
    st.info("Para apagar, marque a caixa 'Excluir' e clique no botão vermelho.")
    
    df_visual = df.copy()
    df_visual["Excluir"] = False
    
    df_editado = st.data_editor(
        df_visual,
        column_config={"Excluir": st.column_config.CheckboxColumn("Excluir?", default=False)},
        disabled=["Data", "Glicemia", "Carbos", "ICR", "Dose"],
        hide_index=True,
    )
    
    if st.button("🗑️ Apagar Linhas Marcadas"):
        linhas_para_manter = df_editado[df_editado["Excluir"] == False]
        linhas_limpas = linhas_para_manter.drop(columns=["Excluir"])
        atualizar_banco(linhas_limpas)
        st.success("Linhas apagadas!")
        st.rerun()

    if not df.empty:
        # Gráfico
        fig, ax = plt.subplots(figsize=(8, 4))
        # Tenta converter para data para ordenar o gráfico corretamente, caso insira fora de ordem
        try:
            df['Data_Ordenada'] = pd.to_datetime(df['Data'], format="%d/%m %H:%M", errors='coerce')
            df_sorted = df.sort_values(by='Data_Ordenada')
            ax.plot(df_sorted['Data'], df_sorted['Glicemia'], marker='o', color='blue')
        except:
            ax.plot(df['Data'], df['Glicemia'], marker='o', color='blue')
            
        ax.axhline(y=ALVO, color='red', linestyle='--')
        ax.set_title("Evolução")
        ax.grid(True)
        # Rotaciona as datas para caber melhor
        plt.xticks(rotation=45)
        st.pyplot(fig)
        plt.savefig("grafico_temp.png")
        
        # --- BOTÕES DE EXPORTAÇÃO ---
        st.write("### 📤 Enviar Relatório")
        col_zap, col_pdf = st.columns(2)
        
        # WhatsApp
        ultimo = df.iloc[-1]
        msg_zap = (f"*RELATÓRIO DE INSULINA*\n"
                   f"📅 Data: {ultimo['Data']}\n"
                   f"🩸 Glicemia: {ultimo['Glicemia']} mg/dL\n"
                   f"🍞 Carbos: {ultimo['Carbos']}g\n"
                   f"⚙️ ICR Usado: {ultimo['ICR']}\n"
                   f"💉 *DOSE APLICADA: {ultimo['Dose']} unidades*\n"
                   f"------------------\n"
                   f"Calculado pelo App.")
        msg_encoded = urllib.parse.quote(msg_zap)
        link_zap = f"https://wa.me/?text={msg_encoded}"
        col_zap.link_button("💚 Enviar no WhatsApp", link_zap, use_container_width=True)

        # PDF
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
