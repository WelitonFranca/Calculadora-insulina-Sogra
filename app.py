import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import os

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Calculadora Insulina", page_icon="💉")

# --- PARÂMETROS FIXOS ---
ALVO = 100
FATOR_SENSIBILIDADE = 40

# --- TÍTULO ---
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

# --- BOTÃO DE CALCULAR ---
if st.button("CALCULAR DOSE", type="primary", use_container_width=True):
    
    # 1. Cálculo de Correção
    if glicemia > ALVO:
        correcao = (glicemia - ALVO) / FATOR_SENSIBILIDADE
    else:
        correcao = 0
        
    # 2. Cálculo da Refeição
    refeicao = carbos / icr
    
    # 3. Total
    dose_total = correcao + refeicao
    
    # 4. Arredondamento (Regra de 1 em 1)
    dose_final = round(dose_total)
    
    # --- RESULTADO NA TELA ---
    st.markdown("---")
    
    if glicemia < 70:
        st.error("⚠️ HIPOGLICEMIA! Não aplique insulina. Coma 15g de açúcar.")
    else:
        st.success(f"## Dose Recomendada: {dose_final} Unidades")
        
        # Detalhes (para conferência)
        with st.expander("Ver detalhes do cálculo"):
            st.write(f"🔹 Para corrigir a glicemia: {correcao:.2f} u")
            st.write(f"🔹 Para cobrir a comida: {refeicao:.2f} u")
            st.write(f"🔹 Soma exata: {dose_total:.2f} u")
            st.caption("O valor foi arredondado para o número inteiro mais próximo.")

        # --- SALVAR NO HISTÓRICO (Temporário na sessão) ---
        if 'historico' not in st.session_state:
            st.session_state.historico = []
            
        st.session_state.historico.append({
            "Data": datetime.now().strftime("%d/%m %H:%M"),
            "Glicemia": glicemia,
            "Carbos": carbos,
            "ICR": icr,
            "Dose": dose_final
        })

# --- EXIBIR HISTÓRICO ---
st.write("---")
st.subheader("Histórico Recente")
if 'historico' in st.session_state and st.session_state.historico:
    df = pd.DataFrame(st.session_state.historico)
    st.table(df)
else:
    st.info("Nenhum cálculo feito ainda nesta sessão.")
