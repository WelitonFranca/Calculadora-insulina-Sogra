import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from fpdf import FPDF
import pytz
import os

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Calculadora Insulina", page_icon="💉")

# --- PARÂMETROS FIXOS ---
ALVO = 100
FATOR_SENSIBILIDADE = 40

# --- FUNÇÃO: GERAR PDF ---
def gerar_pdf(df_historico):
    pdf = FPDF()
    pdf.add_page()
    
    # Cabeçalho
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "Relatorio de Controle Glicemico", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(10)

    # Inserir Gráfico no PDF
    if os.path.exists("grafico_temp.png"):
        pdf.image("grafico_temp.png", x=10, y=40, w=190)
        pdf.ln(100)
    
    # Tabela
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(40, 10, "Data/Hora", 1)
    pdf.cell(30, 10, "Glicemia", 1)
    pdf.cell(30, 10, "Carbos", 1)
    pdf.cell(30, 10, "ICR", 1)
    pdf.cell(30, 10, "Dose", 1)
    pdf.ln()
    
    pdf.set_font("Arial", size=10)
    # Itera sobre o DataFrame
    for index, row in df_historico.iterrows():
        pdf.cell(40, 10, str(row['Data']), 1)
        pdf.cell(30, 10, str(row['Glicemia']), 1)
        pdf.cell(30, 10, str(row['Carbos']), 1)
        pdf.cell(30, 10, str(row['ICR']), 1)
        pdf.cell(30, 10, str(row['Dose']), 1)
        pdf.ln()
        
    # Salva temporariamente
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
    
    # Lógica de Cálculo
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

        # Salvar no Histórico (Sessão)
        if 'historico' not in st.session_state:
            st.session_state.historico = []
            
        fuso_br = pytz.timezone('America/Sao_Paulo')
        data_hora_br = datetime.now(fuso_br).strftime("%d/%m %H:%M")
        
        st.session_state.historico.append({
            "Data": data_hora_br,
            "Glicemia": glicemia,
            "Carbos": carbos,
            "ICR": icr,
            "Dose": dose_final,
            "Excluir": False # Campo novo para controle
        })

# --- ÁREA DE RELATÓRIOS E GRÁFICOS ---
st.write("---")
st.subheader("📊 Histórico e Relatórios")

if 'historico' in st.session_state and len(st.session_state.historico) > 0:
    
    # Prepara o DataFrame
    df = pd.DataFrame(st.session_state.historico)
    
    # --- ÁREA DE EDIÇÃO (LIXEIRA) ---
    st.info("Para apagar um registro errado, marque a caixinha 'Excluir' e clique no botão abaixo.")
    
    # Tabela Editável
    df_editado = st.data_editor(
        df,
        column_config={
            "Excluir": st.column_config.CheckboxColumn(
                "Excluir?",
                help="Marque para remover esta linha",
                default=False,
            )
        },
        disabled=["Data", "Glicemia", "Carbos", "ICR", "Dose"], # Trava as outras colunas
        hide_index=True,
    )
    
    # Botão de Ação de Exclusão
    if st.button("🗑️ Apagar Linhas Marcadas"):
        # Filtra mantendo apenas o que NÃO está marcado para excluir
        linhas_para_manter = df_editado[df_editado["Excluir"] == False]
        
        # Atualiza o histórico removendo a coluna 'Excluir' antes de salvar
        st.session_state.historico = linhas_para_manter.drop(columns=["Excluir"]).to_dict('records')
        st.rerun() # Recarrega a página para atualizar o gráfico

    # --- SÓ MOSTRA GRÁFICO E PDF SE TIVER DADOS (PÓS EXCLUSÃO) ---
    if len(st.session_state.historico) > 0:
        df_final = pd.DataFrame(st.session_state.historico)
        
        # 1. MOSTRAR GRÁFICO
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(df_final['Data'], df_final['Glicemia'], marker='o', linestyle='-', color='blue')
        ax.axhline(y=ALVO, color='red', linestyle='--', label='Alvo')
        ax.set_title("Evolução da Glicemia")
        ax.set_ylabel("mg/dL")
        ax.grid(True)
        plt.xticks(rotation=45)
        st.pyplot(fig)
        
        # Salva gráfico para usar no PDF
        plt.savefig("grafico_temp.png")
        
        # 2. BOTÃO DE DOWNLOAD DO PDF
        gerar_pdf(df_final)
        
        with open("relatorio_final.pdf", "rb") as pdf_file:
            PDFbyte = pdf_file.read()

        st.download_button(label="📄 Baixar Relatório em PDF",
                            data=PDFbyte,
                            file_name="relatorio_insulina.pdf",
                            mime='application/octet-stream')
    else:
        st.warning("Histórico vazio.")

else:
    st.info("Faça o primeiro cálculo para gerar o gráfico e o relatório.")
