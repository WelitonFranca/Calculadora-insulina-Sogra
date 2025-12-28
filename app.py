import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from fpdf import FPDF
import os
import urllib.parse
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pytz

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Calculadora Insulina", page_icon="💉")

# --- PARÂMETROS FIXOS ---
ALVO = 100
FATOR_SENSIBILIDADE = 40

# --- ESTILO CSS ---
st.markdown("""
    <style>
        .stButton button { width: 100%; height: 50px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# ==================================================
# ☁️ CONEXÃO COM GOOGLE SHEETS (COM DIAGNÓSTICO)
# ==================================================

@st.cache_resource
def conectar_gsheets():
    try:
        # 1. Verifica Secrets
        if "gcp_service_account" not in st.secrets:
            st.error("❌ ERRO: Secrets não configurados.")
            st.stop()

        creds_dict = dict(st.secrets["gcp_service_account"])
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # 2. Tenta abrir a planilha
        try:
            sheet = client.open("banco_dados_insulina")
            return sheet
        except gspread.exceptions.SpreadsheetNotFound:
            st.error("❌ ERRO GRAVE: O Robô não encontrou a planilha 'banco_dados_insulina'.")
            st.info("Verifique:\n1. Se o nome da planilha no Google é EXATAMENTE 'banco_dados_insulina'.\n2. Se você compartilhou a planilha com o e-mail do robô.")
            st.stop()

    except Exception as e:
        st.error(f"❌ Erro de Conexão: {e}")
        st.stop()

# ==================================================
# 👤 GERENCIAMENTO DE USUÁRIOS (COM ESPIÃO DE ABAS)
# ==================================================

def carregar_usuarios():
    sheet = conectar_gsheets()
    try:
        worksheet = sheet.worksheet("usuarios")
        dados = worksheet.get_all_records()
        df = pd.DataFrame(dados)
        df = df.astype(str)
        return df
    except gspread.exceptions.WorksheetNotFound:
        # --- AQUI ESTÁ O PULO DO GATO ---
        # Se não achar a aba, ele lista o que achou
        abas_reais = [ws.title for ws in sheet.worksheets()]
        st.error(f"❌ ERRO DE ABA: O sistema procurou a aba 'usuarios' mas não achou.")
        st.warning(f"👀 O Robô está vendo estas abas na sua planilha: {abas_reais}")
        st.info("Dica: Verifique se não tem um espaço em branco no final do nome (ex: 'usuarios ').")
        st.stop()
    except Exception as e:
        st.error(f"Erro desconhecido: {e}")
        return pd.DataFrame()

def cadastrar_usuario(usuario, senha, palavra_secreta):
    usuario = str(usuario).lower().strip().replace(" ", "")
    senha = str(senha).strip()
    palavra_secreta = str(palavra_secreta).lower().strip()
    
    if len(usuario) < 3: return False, "❌ Usuário curto."
    if len(senha) < 4: return False, "❌ Senha curta."
    
    df = carregar_usuarios()
    if not df.empty and usuario in df['usuario'].values:
        return False, "❌ Usuário já existe."
    
    try:
        sheet = conectar_gsheets()
        worksheet = sheet.worksheet("usuarios")
        worksheet.append_row([usuario, senha, palavra_secreta])
        return True, "✅ Conta criada! Faça login."
    except Exception as e:
        return False, f"Erro nuvem: {e}"

def verificar_login(usuario, senha):
    usuario = str(usuario).lower().strip()
    senha = str(senha).strip()
    df = carregar_usuarios()
    if df.empty: return False
    encontrado = df[(df['usuario'] == usuario) & (df['senha'] == senha)]
    return not encontrado.empty

def resetar_senha(usuario, palavra_secreta, nova_senha):
    usuario = str(usuario).lower().strip()
    palavra_secreta = str(palavra_secreta).lower().strip()
    try:
        sheet = conectar_gsheets()
        worksheet = sheet.worksheet("usuarios")
        dados = worksheet.get_all_records()
        idx = -1
        for i, row in enumerate(dados):
            if str(row['usuario']) == usuario and str(row['palavra_secreta']) == palavra_secreta:
                idx = i + 2
                break
        if idx != -1:
            worksheet.update_cell(idx, 2, nova_senha)
            return True, "✅ Senha atualizada!"
        else:
            return False, "❌ Dados incorretos."
    except Exception as e:
        return False, f"Erro: {e}"

# ==================================================
# 📊 DADOS E FUNÇÕES
# ==================================================

def carregar_dados_paciente(usuario):
    try:
        sheet = conectar_gsheets()
        try:
            worksheet = sheet.worksheet("registros")
        except gspread.exceptions.WorksheetNotFound:
             st.error("❌ ERRO: A aba 'registros' não foi encontrada.")
             st.stop()
             
        dados = worksheet.get_all_records()
        df = pd.DataFrame(dados)
        if not df.empty:
            df = df[df['usuario'] == usuario].copy()
            if 'Data' in df.columns:
                df['Data_DT'] = pd.to_datetime(df['Data'], format="%d/%m/%Y %H:%M", errors='coerce')
            cols = ['Glicemia', 'Carbos', 'ICR', 'Dose']
            for c in cols:
                if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            if 'Data_DT' in df.columns: df = df.sort_values(by='Data_DT')
        return df
    except:
        return pd.DataFrame(columns=["usuario", "Data", "Glicemia", "Carbos", "ICR", "Dose"])

def salvar_dados_paciente(usuario, novo):
    try:
        sheet = conectar_gsheets()
        worksheet = sheet.worksheet("registros")
        worksheet.append_row([usuario, novo['Data'], novo['Glicemia'], novo['Carbos'], novo['ICR'], novo['Dose']])
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

def gerar_pdf(df, user, filtro):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    t = "Relatório de Controle Glicêmico".encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(200, 10, t, ln=True, align='C')
    pdf.set_font("Arial", 'I', 10)
    i = f"Paciente: {user.capitalize()} | {filtro}".encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(200, 10, i, ln=True, align='C')
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
    for index, row in df.iterrows():
        pdf.cell(40, 10, str(row['Data']), 1)
        pdf.cell(30, 10, str(row['Glicemia']), 1)
        pdf.cell(30, 10, str(row['Carbos']), 1)
        pdf.cell(30, 10, str(row['ICR']), 1)
        pdf.cell(30, 10, str(row['Dose']), 1)
        pdf.ln()
    pdf.output("relatorio_final.pdf")

# ==================================================
# APP
# ==================================================

if 'usuario_logado' not in st.session_state: st.session_state.usuario_logado = None
if 'resultado_tela' not in st.session_state: st.session_state.resultado_tela = None

if st.session_state.usuario_logado is None:
    st.title("☁️ Diário na Nuvem")
    st.success("Conexão com Google Sheets ativa.")
    
    t1, t2, t3 = st.tabs(["Entrar", "Criar Conta", "Recuperar"])
    with t1:
        u = st.text_input("Usuário", key="l_u").strip()
        p = st.text_input("Senha", type="password", key="l_p").strip()
        if st.button("ENTRAR", type="primary"):
            if verificar_login(u, p):
                st.session_state.usuario_logado = u.lower()
                st.rerun()
            else: st.error("Login incorreto.")
    with t2:
        nu = st.text_input("Novo Usuário", key="c_u")
        np = st.text_input("Nova Senha", type="password", key="c_p")
        ns = st.text_input("Palavra Secreta", type="password", key="c_s")
        if st.button("CRIAR"):
            ok, m = cadastrar_usuario(nu, np, ns)
            if ok: st.success(m)
            else: st.error(m)
    with t3:
        ru = st.text_input("Usuário", key="r_u")
        rs = st.text_input("Palavra Secreta", type="password", key="r_s")
        rnp = st.text_input("Nova Senha", type="password", key="r_np")
        if st.button("REDEFINIR"):
            ok, m = resetar_senha(ru, rs, rnp)
            if ok: st.success(m)
            else: st.error(m)
    st.stop()

user = st.session_state.usuario_logado
st.title(f"Olá, {user.capitalize()}!")
with st.sidebar:
    if st.button("Sair"):
        st.session_state.usuario_logado = None
        st.rerun()

st.write("---")
c1, c2 = st.columns(2)
glic = c1.number_input("Glicemia", 0, 600)
carb = c2.number_input("Carbos", 0, 300)

if 'data_fixa' not in st.session_state: st.session_state.data_fixa = None
agora = datetime.now(pytz.timezone('America/Sao_Paulo'))
data_final = st.session_state.data_fixa if st.session_state.data_fixa else agora

if st.session_state.data_fixa:
    st.success(f"Data Fixada: {data_final.strftime('%d/%m %H:%M')}")
    if st.button("Usar Agora"): st.session_state.data_fixa = None; st.rerun()
else:
    st.info(f"Hora: {agora.strftime('%H:%M')}")
    if st.button("Mudar Data"): 
        st.session_state.data_fixa = agora
        st.warning("Data manual ativada.")

st.write("---")
icr = st.selectbox("ICR", range(1, 21), index=9)
if st.button("CALCULAR E SALVAR", type="primary"):
    if glic == 0 and carb == 0: st.warning("Preencha dados.")
    else:
        corr = (glic - ALVO)/FATOR_SENSIBILIDADE if glic > ALVO else 0
        ref = carb/icr
        dose = round(corr + ref)
        novo = {"Data": data_final.strftime("%d/%m/%Y %H:%M"), "Glicemia": glic, "Carbos": carb, "ICR": icr, "Dose": dose}
        if salvar_dados_paciente(user, novo):
            st.session_state.resultado_tela = {"dose": dose, "detalhes": f"C: {corr:.1f} + R: {ref:.1f}"}
            st.rerun()

if st.session_state.resultado_tela:
    st.success(f"## Dose: {st.session_state.resultado_tela['dose']} u")
    st.write(st.session_state.resultado_tela['detalhes'])
    if st.button("Novo"): st.session_state.resultado_tela = None; st.rerun()

st.write("---")
st.subheader("📊 Histórico")
df = carregar_dados_paciente(user)
if not df.empty:
    c_f1, c_f2 = st.columns(2)
    with c_f1:
        min_d, max_d = df['Data_DT'].min().date(), df['Data_DT'].max().date()
        p = st.date_input("Período", value=(min_d, max_d), min_value=min_d, max_value=max_d, format="DD/MM/YYYY")
    with c_f2:
        met = st.multiselect("Gráfico", ["Glicemia", "Carbos", "Dose"], default=["Glicemia"])
        if not met: met = ["Glicemia"]
    
    mask = (df['Data_DT'].dt.date >= p[0]) & (df['Data_DT'].dt.date <= p[1]) if isinstance(p, tuple) and len(p) == 2 else True
    df_f = df.loc[mask]
    
    if not df_f.empty:
        fig, ax = plt.subplots(figsize=(8, 4))
        if "Glicemia" in met: ax.plot(df_f['Data'], df_f['Glicemia'], 'bo-', label='Glicemia')
        if "Carbos" in met: ax.plot(df_f['Data'], df_f['Carbos'], 'gs--', label='Carbos')
        if "Dose" in met: ax.plot(df_f['Data'], df_f['Dose'], 'r^-', label='Dose')
        ax.grid(True, alpha=0.3); ax.legend(); plt.xticks(rotation=45); plt.tight_layout()
        st.pyplot(fig); plt.savefig("grafico_temp.png")
        
        st.dataframe(df_f[["Data", "Glicemia", "Carbos", "ICR", "Dose"]], use_container_width=True, hide_index=True)
        c_z, c_p = st.columns(2)
        gerar_pdf(df_f, user, "Personalizado")
        with open("relatorio_final.pdf", "rb") as f: c_p.download_button("PDF", f, "relatorio.pdf")
        msg = urllib.parse.quote(f"Resumo {user}: {len(df_f)} registros.")
        c_z.link_button("WhatsApp", f"https://wa.me/?text={msg}")
    else: st.info("Nada no período.")
else: st.info("Sem dados.")
