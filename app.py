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

# --- BARRA LATERAL (COFRE) ---
with st.sidebar:
    st.header("📂 Segurança")
    arquivo_upload = st.file_uploader("Restaurar Backup (CSV)", type=["csv"])
    if arquivo_upload is not None:
        try:
            df_restaurado = pd.read_csv(arquivo_upload)
            atualizar_banco(df_restaurado)
            st.success("✅ Restaurado!")
        except:
            st.error("Erro ao ler arquivo.")

st.markdown(f"**Configuração:** Alvo {ALVO} | Sensibilidade {FATOR_SENSIBILIDADE}")

# --- ENTRADA DE DADOS ---
st.write("---")
st.subheader("1. Dados da Medição")

col1, col2 = st.columns(2)
with col1:
    glicemia = st.number_input("Glicemia (mg/dL)", min_value=0, max_value=600, value=100)
with col2:
    carbos = st.number_input("Carboidratos (g)", min_value=0, max_value=300, value=0)

# --- LÓGICA DE DATA E HORA COM BOTÃO DE SALVAR ---
st.write("---")
st.subheader("2. Quando foi?")

# Inicializa variáveis de controle na memória
if 'modo_manual' not in st.session_state:
    st.session_state.modo_manual = False
if 'data_fixada' not in st.session_state:
    st.session_state.data_fixada = datetime.now()

fuso_br = pytz.timezone('America/Sao_Paulo')
agora = datetime.now(fuso_br)

# Lógica de Exibição
if not st.session_state.modo_manual:
    # MODO AUTOMÁTICO (MOSTRA SÓ O TEXTO)
    st.info(f"🕒 Horário Automático: **{agora.strftime('%d/%m/%Y %H:%M')}**")
    if st.button("✏️ Alterar Data/Hora"):
        st.session_state.modo_manual = True
        st.rerun()
    data_final_para_salvar = agora
else:
    # MODO DE EDIÇÃO (MOSTRA OS CAMPOS E O BOTÃO SALVAR)
    st.warning("✏️ Editando Data e Hora...")
    c1, c2 = st.columns(2)
    d = c1.date_input("Data", value=agora, format="DD/MM/YYYY")
    t = c2.time_input("Hora", value=agora)
    
    col_save, col_cancel = st.columns(2)
    
    # O BOTÃO QUE VOCÊ PEDIU:
    if col_save.button("💾 SALVAR DATA E HORA", type="primary"):
        # Combina e salva na memória
        data_combinada = datetime.combine(d, t)
        st.session_state.data_fixada = data_combinada
        st.session_state.modo_manual = "FIXADO" # Estado especial: Manual mas travado
        st.rerun()
        
    if col_cancel.button("Cancelar"):
        st.session_state.modo_manual = False
        st.rerun()
    
    data_final_para_salvar = datetime.combine(d, t)

# ESTADO FIXADO (QUANDO O USUÁRIO JÁ CLICOU EM SALVAR)
if st.session_state.modo_manual == "FIXADO":
    # Mostra a data travada e opção de destrancar
    st.success(f"🔒 Data Fixada: **{st.session_state.data_fixada.strftime('%d/%m/%Y %H:%M')}**")
    if st.button("🔄 Liberar / Usar Agora"):
        st.session_state.modo_manual = False
        st.rerun()
    data_final_para_salvar = st.session_state.data_fixada

# --- SELEÇÃO DE ICR ---
st.write("---")
st.subheader("3. Configuração")
lista_opcoes = list(range(1, 21))
icr = st.selectbox("Fator ICR", options=lista_opcoes, index=9)

# --- CÁLCULO ---
if st.button("CALCULAR E REGISTRAR", type="primary", use_container_width=True):
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

        # SALVAR
        data_str = data_final_para_salvar.strftime("%d/%m/%Y %H:%M")
        
        novo_registro = {
            "Data": data_str,
            "Glicemia": glicemia,
            "Carbos": carbos,
            "ICR": icr,
            "Dose": dose_final
        }
        
        salvar_registro(novo_registro)
        st.toast("✅ Dados salvos com sucesso!")
        
        # Opcional: Voltar para automático após salvar
        # st.session_state.modo_manual = False 

# --- ÁREA DE RELATÓRIOS ---
st.write("---")
st.subheader("📊 Histórico e Ações")

df = carregar_dados()

if not df.empty:
    st.warning("💾 **Dica:** Baixe o backup regularmente.")
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("💾 BAIXAR BACKUP", csv, "backup_insulina.csv", "text/csv")
    
    st.write("---")
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
        try:
            df['Data_Ordenada'] = pd.to_datetime(df['Data'], format="%d/%m/%Y %H:%M", errors='coerce')
            df_sorted = df.sort_values(by='Data_Ordenada')
            ax.plot(df_sorted['Data'], df_sorted['Glicemia'], marker='o', color='blue')
        except:
            ax.plot(df['Data'], df['Glicemia'], marker='o', color='blue')
            
        ax.axhline(y=ALVO, color='red', linestyle='--')
        ax.set_title("Evolução")
        ax.grid(True)
        plt.xticks(rotation=45)
        st.pyplot(fig)
        plt.savefig("grafico_temp.png")
        
        # Exportação
        st.write("### 📤 Enviar Relatório")
        col_zap, col_pdf = st.columns(2)
        
        ultimo = df.iloc[-1]
        msg_zap = (f"*RELATÓRIO DE INSULINA*\n"
                   f"📅 Data: {ultimo['Data']}\n"
                   f"🩸 Glicemia: {ultimo['Glicemia']} mg/dL\n"
                   f"🍞 Carbos: {ultimo['Carbos']}g\n"
                   f"⚙️ ICR: {ultimo['ICR']}\n"
                   f"💉 *DOSE: {ultimo['Dose']} unidades*")
        msg_encoded = urllib.parse.quote(msg_zap)
        link_zap = f"https://wa.me/?text={msg_encoded}"
