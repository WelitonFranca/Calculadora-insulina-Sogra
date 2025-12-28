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
        .stButton button {
            width: 100%;
            height: 50px;
            font-weight: bold;
        }
        div[data-testid="stMetricValue"] {
            font-size: 24px;
        }
    </style>
""", unsafe_allow_html=True)

# ==================================================
# ☁️ CONEXÃO COM GOOGLE SHEETS (BLINDADA)
# ==================================================

@st.cache_resource
def conectar_gsheets():
    """
    Conecta ao Google Sheets e guarda a conexão na memória (Cache)
    para o app não ficar lento reconectando toda hora.
    """
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        # Lê as credenciais dos Segredos do Streamlit
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # Abre a planilha
        sheet = client.open("banco_dados_insulina")
        return sheet
    except Exception as e:
        st.error(f"❌ Erro Crítico de Conexão: {e}")
        st.stop()

# ==================================================
# 👤 GERENCIAMENTO DE USUÁRIOS
# ==================================================

def carregar_usuarios():
    try:
        sheet = conectar_gsheets()
        worksheet = sheet.worksheet("usuarios")
        dados = worksheet.get_all_records()
        df = pd.DataFrame(dados)
        # Converte tudo para texto para evitar erros de login
        df = df.astype(str)
        return df
    except:
        return pd.DataFrame(columns=["usuario", "senha", "palavra_secreta"])

def cadastrar_usuario(usuario, senha, palavra_secreta):
    # Limpeza rigorosa
    usuario = str(usuario).lower().strip().replace(" ", "")
    senha = str(senha).strip()
    palavra_secreta = str(palavra_secreta).lower().strip()
    
    if len(usuario) < 3: return False, "❌ Usuário muito curto (min 3 letras)."
    if len(senha) < 4: return False, "❌ Senha muito curta (min 4 dígitos)."
    
    df = carregar_usuarios()
    if not df.empty and usuario in df['usuario'].values:
        return False, "❌ Usuário já existe."
    
    try:
        sheet = conectar_gsheets()
        worksheet = sheet.worksheet("usuarios")
        worksheet.append_row([usuario, senha, palavra_secreta])
        return True, "✅ Conta criada com sucesso! Faça login."
    except Exception as e:
        return False, f"Erro na nuvem: {e}"

def verificar_login(usuario, senha):
    usuario = str(usuario).lower().strip()
    senha = str(senha).strip()
    
    df = carregar_usuarios()
    if df.empty: return False
    
    # Busca exata
    encontrado = df[(df['usuario'] == usuario) & (df['senha'] == senha)]
    return not encontrado.empty

def resetar_senha(usuario, palavra_secreta, nova_senha):
    usuario = str(usuario).lower().strip()
    palavra_secreta = str(palavra_secreta).lower().strip()
    
    try:
        sheet = conectar_gsheets()
        worksheet = sheet.worksheet("usuarios")
        dados = worksheet.get_all_records()
        
        linha_para_editar = -1
        # gspread usa índice base 1 + 1 do cabeçalho = começa em 2
        for i, row in enumerate(dados):
            if str(row['usuario']) == usuario and str(row['palavra_secreta']) == palavra_secreta:
                linha_para_editar = i + 2 
                break
        
        if linha_para_editar != -1:
            worksheet.update_cell(linha_para_editar, 2, nova_senha) # Coluna 2 é senha
            return True, "✅ Senha atualizada!"
        else:
            return False, "❌ Dados incorretos."
    except Exception as e:
        return False, f"Erro: {e}"

# ==================================================
# 📊 GERENCIAMENTO DE DADOS DO PACIENTE
# ==================================================

def carregar_dados_paciente(usuario):
    try:
        sheet = conectar_gsheets()
        worksheet = sheet.worksheet("registros")
        dados = worksheet.get_all_records()
        df = pd.DataFrame(dados)
        
        # Filtra apenas o usuário atual
        if not df.empty:
            df = df[df['usuario'] == usuario].copy()
            
            # CONVERSÃO BLINDADA DE DADOS (CRÍTICO)
            # Garante que números sejam números e datas sejam datas
            if 'Data' in df.columns:
                df['Data_DT'] = pd.to_datetime(df['Data'], format="%d/%m/%Y %H:%M", errors='coerce')
            
            cols_numericas = ['Glicemia', 'Carbos', 'ICR', 'Dose']
            for col in cols_numericas:
                if col in df.columns:
                    # Força conversão para número, se der erro vira 0
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # Ordena por data
            if 'Data_DT' in df.columns:
                df = df.sort_values(by='Data_DT')
                
        return df
    except:
        return pd.DataFrame(columns=["usuario", "Data", "Glicemia", "Carbos", "ICR", "Dose"])

def salvar_dados_paciente(usuario, novo_dado):
    try:
        sheet = conectar_gsheets()
        worksheet = sheet.worksheet("registros")
        
        # Ordem exata das colunas na planilha
        linha = [
            usuario,
            novo_dado['Data'],
            novo_dado['Glicemia'],
            novo_dado['Carbos'],
            novo_dado['ICR'],
            novo_dado['Dose']
        ]
        worksheet.append_row(linha)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

# ==================================================
# 📄 GERADOR DE PDF
# ==================================================

def gerar_pdf(df_historico, usuario_nome, filtro_msg="Geral"):
    pdf = FPDF()
    pdf.add_page()
    
    # Título com codificação correta para acentos
    pdf.set_font("Arial", 'B', 16)
    titulo = "Relatório de Controle Glicêmico".encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(200, 10, titulo, ln=True, align='C')
    
    pdf.set_font("Arial", 'I', 10)
    info = f"Paciente: {usuario_nome.capitalize()} | {filtro_msg}".encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(200, 10, info, ln=True, align='C')
    
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(10)

    if os.path.exists("grafico_temp.png"):
        pdf.image("grafico_temp.png", x=10, y=50, w=190)
        pdf.ln(100)
    
    # Cabeçalho da Tabela
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(40, 10, "Data/Hora", 1)
    pdf.cell(30, 10, "Glicemia", 1)
    pdf.cell(30, 10, "Carbos", 1)
    pdf.cell(30, 10, "ICR", 1)
    pdf.cell(30, 10, "Dose", 1)
    pdf.ln()
    
    # Dados da Tabela
    pdf.set_font("Arial", size=10)
    for index, row in df_historico.iterrows():
        pdf.cell(40, 10, str(row['Data']), 1)
        pdf.cell(30, 10, str(row['Glicemia']), 1)
        pdf.cell(30, 10, str(row['Carbos']), 1)
        pdf.cell(30, 10, str(row['ICR']), 1)
        pdf.cell(30, 10, str(row['Dose']), 1)
        pdf.ln()
        
    pdf.output("relatorio_final.pdf")

# ==================================================
# 📱 INTERFACE DO APLICATIVO
# ==================================================

if 'usuario_logado' not in st.session_state: st.session_state.usuario_logado = None
if 'resultado_tela' not in st.session_state: st.session_state.resultado_tela = None

# --- TELA DE LOGIN ---
if st.session_state.usuario_logado is None:
    st.title("☁️ Diário na Nuvem")
    st.success("Sistema conectado ao Google Sheets. Seus dados estão seguros.")
    
    tab1, tab2, tab3 = st.tabs(["Entrar", "Criar Conta", "Recuperar"])
    
    with tab1:
        st.write("Acesse sua conta:")
        l_u = st.text_input("Usuário", key="login_u").strip()
        l_p = st.text_input("Senha", type="password", key="login_p").strip()
        
        if st.button("ENTRAR", type="primary"):
            if verificar_login(l_u, l_p):
                st.session_state.usuario_logado = l_u.lower()
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

    with tab2:
        st.write("Novo cadastro:")
        c_u = st.text_input("Novo Usuário", key="cad_u")
        c_p = st.text_input("Nova Senha", type="password", key="cad_p")
        c_s = st.text_input("Palavra Secreta (Recuperação)", type="password", key="cad_s")
        
        if st.button("CRIAR CONTA"):
            ok, msg = cadastrar_usuario(c_u, c_p, c_s)
            if ok: st.success(msg)
            else: st.error(msg)

    with tab3:
        st.write("Recuperar acesso:")
        r_u = st.text_input("Usuário", key="rec_u")
        r_s = st.text_input("Palavra Secreta", type="password", key="rec_s")
        r_np = st.text_input("Nova Senha", type="password", key="rec_np")
        
        if st.button("REDEFINIR SENHA"):
            ok, msg = resetar_senha(r_u, r_s, r_np)
            if ok: st.success(msg)
            else: st.error(msg)
    
    st.stop()

# --- ÁREA LOGADA ---
user = st.session_state.usuario_logado
st.title(f"Olá, {user.capitalize()}!")

with st.sidebar:
    st.info(f"Conectado como: **{user}**")
    if st.button("Sair"):
        st.session_state.usuario_logado = None
        st.session_state.resultado_tela = None
        st.rerun()

# 1. ENTRADA DE DADOS
st.write("---")
st.subheader("1. Novo Registro")

c1, c2 = st.columns(2)
glicemia = c1.number_input("Glicemia (mg/dL)", 0, 600)
carbos = c2.number_input("Carboidratos (g)", 0, 300)

# 2. DATA E HORA
st.write("---")
st.subheader("2. Data e Hora")

if 'modo_manual' not in st.session_state: st.session_state.modo_manual = False
if 'data_fixada' not in st.session_state: st.session_state.data_fixada = datetime.now()

fuso_br = pytz.timezone('America/Sao_Paulo')
agora = datetime.now(fuso_br)

if not st.session_state.modo_manual:
    st.info(f"🕒 Data Automática: **{agora.strftime('%d/%m/%Y %H:%M')}**")
    if st.button("✏️ Mudar Data/Hora"):
        st.session_state.modo_manual = True
        st.rerun()
    data_final = agora
else:
    st.warning("✏️ Editando Data...")
    c_d, c_h = st.columns(2)
    d = c_d.date_input("Dia", value=agora)
    t = c_h.time_input("Hora", value=agora)
    
    col_ok, col_cancel = st.columns(2)
    if col_ok.button("✅ Confirmar Data"):
        st.session_state.data_fixada = datetime.combine(d, t)
        st.session_state.modo_manual = "FIXADO"
        st.rerun()
    if col_cancel.button("Cancelar"):
        st.session_state.modo_manual = False
        st.rerun()
    data_final = datetime.combine(d, t)

if st.session_state.modo_manual == "FIXADO":
    st.success(f"🔒 Data Fixada: **{st.session_state.data_fixada.strftime('%d/%m/%Y %H:%M')}**")
    if st.button("🔄 Voltar para Agora"):
        st.session_state.modo_manual = False
        st.rerun()
    data_final = st.session_state.data_fixada

# 3. CÁLCULO
st.write("---")
st.subheader("3. Calcular")
icr = st.selectbox("Fator ICR", range(1, 21), index=9)

if st.button("CALCULAR E SALVAR NA NUVEM", type="primary"):
    if glicemia == 0 and carbos == 0:
        st.warning("⚠️ Preencha Glicemia ou Carbos.")
    else:
        correcao = (glicemia - ALVO)/FATOR_SENSIBILIDADE if glicemia > ALVO else 0
        refeicao = carbos / icr
        dose_total = correcao + refeicao
        dose_final = round(dose_total)
        
        novo_registro = {
            "Data": data_final.strftime("%d/%m/%Y %H:%M"),
            "Glicemia": glicemia, "Carbos": carbos, "ICR": icr, "Dose": dose_final
        }
        
        with st.spinner("Salvando no Google..."):
            sucesso = salvar_dados_paciente(user, novo_registro)
        
        if sucesso:
            st.session_state.resultado_tela = {
                "dose": dose_final,
                "detalhes": f"Correção: {correcao:.1f} + Comida: {refeicao:.1f}"
            }
            st.rerun()

# RESULTADO
if st.session_state.resultado_tela:
    res = st.session_state.resultado_tela
    st.markdown("---")
    st.success(f"## Dose: {res['dose']} Unidades")
    st.info(f"Detalhes: {res['detalhes']}")
    if st.button("Limpar"):
        st.session_state.resultado_tela = None
        st.rerun()

# 4. RELATÓRIOS
st.write("---")
st.subheader("📊 Histórico Completo")

df = carregar_dados_paciente(user)

if not df.empty:
    # Filtros
    c_f1, c_f2 = st.columns(2)
    with c_f1:
        min_d = df['Data_DT'].min().date()
        max_d = df['Data_DT'].max().date()
        periodo = st.date_input("Período", value=(min_d, max_d), min_value=min_d, max_value=max_d, format="DD/MM/YYYY")
    with c_f2:
        metricas = st.multiselect("Ver no Gráfico", ["Glicemia", "Carbos", "Dose"], default=["Glicemia"])
        if not metricas: metricas = ["Glicemia"]

    # Aplica Filtro
    mask = (df['Data_DT'].dt.date >= periodo[0]) & (df['Data_DT'].dt.date <= periodo[1]) if isinstance(periodo, tuple) and len(periodo) == 2 else True
    df_filt = df.loc[mask]

    if not df_filt.empty:
        # Gráfico
        fig, ax = plt.subplots(figsize=(8, 4))
        if "Glicemia" in metricas: ax.plot(df_filt['Data'], df_filt['Glicemia'], 'bo-', label='Glicemia')
        if "Carbos" in metricas: ax.plot(df_filt['Data'], df_filt['Carbos'], 'gs--', label='Carbos')
        if "Dose" in metricas: ax.plot(df_filt['Data'], df_filt['Dose'], 'r^-', label='Dose')
        ax.grid(True, alpha=0.3)
        ax.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig)
        plt.savefig("grafico_temp.png")

        # Tabela (Mostra TUDO independente do filtro do gráfico)
        st.write("📋 **Tabela Detalhada**")
        cols_show = ["Data", "Glicemia", "Carbos", "ICR", "Dose"]
        # Garante que as colunas existem antes de mostrar
        cols_existentes = [c for c in cols_show if c in df_filt.columns]
        st.dataframe(df_filt[cols_existentes], use_container_width=True, hide_index=True)
        
        # Exportação
        c_zap, c_pdf = st.columns(2)
        gerar_pdf(df_filt, user, "Personalizado")
        with open("relatorio_final.pdf", "rb") as f:
            c_pdf.download_button("📄 Baixar PDF", f, "relatorio.pdf", "application/pdf", use_container_width=True)
        
        msg = urllib.parse.quote(f"Resumo {user}: {len(df_filt)} registros.")
        c_zap.link_button("💚 WhatsApp", f"https://wa.me/?text={msg}", use_container_width=True)
    else:
        st.info("Nenhum dado neste período.")
else:
    st.info("Nenhum registro encontrado na nuvem.")

st.write("---")
st.markdown("<div style='text-align: center; color: grey;'>Desenvolvido por <b>Weliton França</b> ❤️</div>", unsafe_allow_html=True)
