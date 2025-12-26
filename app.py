import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from fpdf import FPDF
import pytz
import urllib.parse
import os

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Calculadora Insulina", page_icon="💉")

# --- TRUQUE DE CSS (ESTILO) ---
st.markdown("""
    <style>
        .stFileUploader div[data-testid="stFileUploaderDropzoneInstructions"] > div > span {
            display: none;
        }
        .stFileUploader div[data-testid="stFileUploaderDropzoneInstructions"] > div::after {
            content: "📂 Clique aqui para Recuperar Backup";
            font-size: 18px;
            font-weight: 900;
            color: #000000;
            background-color: rgba(255, 255, 255, 0.8);
            padding: 10px;
            border-radius: 5px;
            display: block;
            text-align: center;
        }
        .stFileUploader small {
            display: none;
        }
        .stButton button {
            width: 100%;
            height: 50px; /* Botões mais altos para facilitar o toque */
        }
    </style>
""", unsafe_allow_html=True)

# --- PARÂMETROS FIXOS ---
ALVO = 100
FATOR_SENSIBILIDADE = 40

# --- INICIALIZAÇÃO DA MEMÓRIA (SESSÃO) ---
if 'historico' not in st.session_state:
    st.session_state.historico = []

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

with st.sidebar:
    st.info("Este aplicativo funciona de modo privado. Seus dados ficam salvos apenas no seu celular.")

st.markdown(f"**Configuração:** Alvo {ALVO} | Sensibilidade {FATOR_SENSIBILIDADE}")

# --- ENTRADA DE DADOS ---
st.write("---")
st.subheader("1. Dados da Medição")

col1, col2 = st.columns(2)
with col1:
    glicemia_input = st.number_input("Glicemia (mg/dL)", min_value=0, max_value=600, value=None, placeholder="0")
with col2:
    carbos_input = st.number_input("Carboidratos (g)", min_value=0, max_value=300, value=None, placeholder="0")

# --- DATA E HORA ---
st.write("---")
st.subheader("2. Quando foi?")

if 'modo_manual' not in st.session_state:
    st.session_state.modo_manual = False
if 'data_fixada' not in st.session_state:
    st.session_state.data_fixada = datetime.now()

fuso_br = pytz.timezone('America/Sao_Paulo')
agora = datetime.now(fuso_br)

if not st.session_state.modo_manual:
    st.info(f"🕒 Horário Automático: **{agora.strftime('%d/%m/%Y %H:%M')}**")
    if st.button("✏️ Alterar Data/Hora"):
        st.session_state.modo_manual = True
        st.rerun()
    data_final_para_salvar = agora
else:
    st.warning("✏️ Editando Data e Hora...")
    c1, c2 = st.columns(2)
    d = c1.date_input("Data", value=agora, format="DD/MM/YYYY")
    t = c2.time_input("Hora", value=agora)
    
    col_save, col_cancel = st.columns(2)
    
    if col_save.button("💾 SALVAR DATA E HORA", type="primary"):
        data_combinada = datetime.combine(d, t)
        st.session_state.data_fixada = data_combinada
        st.session_state.modo_manual = "FIXADO"
        st.rerun()
        
    if col_cancel.button("Cancelar"):
        st.session_state.modo_manual = False
        st.rerun()
    
    data_final_para_salvar = datetime.combine(d, t)

if st.session_state.modo_manual == "FIXADO":
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
    
    glicemia = glicemia_input if glicemia_input is not None else 0
    carbos = carbos_input if carbos_input is not None else 0

    if glicemia == 0 and carbos == 0:
        st.warning("⚠️ Digite a Glicemia ou os Carboidratos.")
    else:
        if glicemia > ALVO:
            correcao = (glicemia - ALVO) / FATOR_SENSIBILIDADE
        else:
            correcao = 0
        
        refeicao = carbos / icr
        dose_total = correcao + refeicao
        dose_final = round(dose_total)
        
        st.markdown("---")
        
        if glicemia < 70 and
