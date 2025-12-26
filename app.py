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
            height: 50px;
        }
    </style>
""", unsafe_allow_html=True)

# --- PARÂMETROS FIXOS ---
ALVO = 100
FATOR_SENSIBILIDADE = 40

# --- INICIALIZAÇÃO DA MEMÓRIA (SESSÃO) ---
if 'historico' not in st.session_state:
    st.session_state.historico = []

# Variável para guardar o resultado do cálculo mesmo se a página recarregar
if 'resultado_tela' not in st.session_state:
    st.session_state.resultado_tela = None

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
        
        # SALVA NO HISTÓRICO
        data_str = data_final_para_salvar.strftime("%d/%m/%Y %H:%M")
        novo_registro = {
            "Data": data_str,
            "Glicemia": glicemia,
            "Carbos": carbos,
            "ICR": icr,
            "Dose": dose_final
        }
        st.session_state.historico.append(novo_registro)
        
        # SALVA O RESULTADO NA MEMÓRIA PARA EXIBIR APÓS O REBOOT
        st.session_state.resultado_tela = {
            "glicemia": glicemia,
            "dose_final": dose_final,
            "correcao": correcao,
            "refeicao": refeicao,
            "dose_total": dose_total
        }
        
        # FORÇA A ATUALIZAÇÃO DA PÁGINA (Isso conserta o erro de não aparecer na tabela)
        st.rerun()

# --- EXIBIÇÃO DO RESULTADO (FORA DO BOTÃO) ---
if st.session_state.resultado_tela is not None:
    res = st.session_state.resultado_tela
    
    st.markdown("---")
    
    if res["glicemia"] < 70 and res["glicemia"] > 0:
        st.error("⚠️ HIPOGLICEMIA! Não aplique insulina. Coma 15g de açúcar.")
    else:
        st.success(f"## Dose Recomendada: {res['dose_final']} Unidades")
        with st.expander("Ver detalhes do cálculo"):
            st.write(f"🔹 Correção: {res['correcao']:.2f} u")
            st.write(f"🔹 Comida: {res['refeicao']:.2f} u")
            st.write(f"🔹 Total exato: {res['dose_total']:.2f} u")
            
    if st.button("🔄 Novo Cálculo / Limpar Tela"):
        st.session_state.resultado_tela = None
        st.rerun()

# --- ÁREA DE GERENCIAMENTO DE DADOS (BACKUP) ---
st.write("---")
st.subheader("💾 Gerenciamento de Dados")

# 1. BOTÃO FAZER BACKUP (DOWNLOAD)
st.write("⬇️ **1º Passo: Salvar no Celular**")
if len(st.session_state.historico) > 0:
    df_export = pd.DataFrame(st.session_state.historico)
    try:
        df_export['_dt'] = pd.to_datetime(df_export['Data'], format="%d/%m/%Y %H:%M")
        df_export = df_export.sort_values(by='_dt')
        df_export = df_export.drop(columns=['_dt'])
    except:
        pass
        
    csv = df_export.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Fazer Backup (Salvar)",
        data=csv,
        file_name="backup_insulina.csv",
        mime="text/csv",
        type="primary",
        use_container_width=True
    )
else:
    st.info("Faça um registro primeiro para poder salvar.")

st.write("") 
st.write("") 

# 2. BOTÃO RECUPERAR BACKUP (UPLOAD)
st.write("📂 **2º Passo: Restaurar Antigo**")
arquivo_upload = st.file_uploader(" ", type=["csv"], label_visibility="collapsed")
if arquivo_upload is not None:
    try:
        df_restaurado = pd.read_csv(arquivo_upload)
        st.session_state.historico = df_restaurado.to_dict('records')
        st.success("✅ Backup Restaurado com Sucesso!")
    except:
        st.error("Arquivo inválido.")

# --- ÁREA DE RELATÓRIOS ---
st.write("---")
st.subheader("📊 Histórico e Ações")

if len(st.session_state.historico) > 0:
    
    df = pd.DataFrame(st.session_state.historico)
    
    # Ordenação automática
    try:
        df['_data_temp'] = pd.to_datetime(df['Data'], format="%d/%m/%Y %H:%M")
        df = df.sort_values(by='_data_temp')
        df = df.drop(columns=['_data_temp'])
    except:
        pass 
    
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
        st.session_state.historico = linhas_para_manter.drop(columns=["Excluir"]).to_dict('records')
        st.success("Linhas apagadas!")
        st.rerun()

    if len(st.session_state.historico) > 0:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(df['Data'], df['Glicemia'], marker='o', color='blue')
        ax.axhline(y=ALVO, color='red', linestyle='--')
        ax.set_title("Evolução")
        ax.grid(True)
        plt.xticks(rotation=45)
        st.pyplot(fig)
        plt.savefig("grafico_temp.png")
        
        st.write("### 📤 Enviar Relatório")
        
        ultimo = df.iloc[-1]
        msg_zap = (f"*RELATÓRIO DE INSULINA*\n"
                   f"📅 Data: {ultimo['Data']}\n"
                   f"🩸 Glicemia: {ultimo['Glicemia']} mg/dL\n"
                   f"🍞 Carbos: {ultimo['Carbos']}g\n"
                   f"⚙️ ICR: {ultimo['ICR']}\n"
                   f"💉 *DOSE: {ultimo['Dose']} unidades*")
        msg_encoded = urllib.parse.quote(msg_zap)
        link_zap = f"https://wa.me/?text={msg_encoded}"
        
        st.link_button("💚 Enviar no WhatsApp", link_zap, use_container_width=True)
        
        st.write("") 

        gerar_pdf(df)
        with open("relatorio_final.pdf", "rb") as pdf_file:
            st.download_button("📄 Baixar PDF Completo", pdf_file, "relatorio.pdf", "application/pdf", use_container_width=True)

else:
    st.info("Histórico vazio. Faça um cálculo ou recupere um backup.")

# --- RODAPÉ PERSONALIZADO ---
st.write("---")
st.markdown(
    """
    <div style='text-align: center; color: grey; padding: 20px;'>
        Desenvolvido por <b>Weliton França</b> - Genro da Marina ❤️
    </div>
    """,
    unsafe_allow_html=True
)
