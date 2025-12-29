import streamlit as st
import pandas as pd
import gspread
import glob
from datetime import datetime

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Diário Insulina", layout="centered")

# --- 2. CONEXÃO SILENCIOSA ---
@st.cache_resource(ttl=600)
def conectar_banco():
    arquivos_json = glob.glob("*.json")
    arquivo_chave = None
    
    if len(arquivos_json) == 0:
        st.error("❌ Erro: Nenhum arquivo .json encontrado.")
        st.stop()
    elif len(arquivos_json) == 1:
        arquivo_chave = arquivos_json[0]
    else:
        for f in arquivos_json:
            if "tranquil" in f or "service" in f:
                arquivo_chave = f
                break
        if not arquivo_chave: arquivo_chave = arquivos_json[0]

    try:
        gc = gspread.service_account(filename=arquivo_chave)
        return gc
    except Exception as e:
        st.error(f"❌ Erro na chave: {e}")
        st.stop()

# --- 3. PREPARAÇÃO ---
def preparar_abas():
    gc = conectar_banco()
    try:
        sh = gc.open("banco_dados_insulina")
    except:
        st.error("❌ Planilha não encontrada.")
        st.stop()

    try:
        sh.worksheet("usuarios")
    except:
        ws = sh.add_worksheet("usuarios", 100, 5)
        ws.append_row(["usuario", "senha", "criado_em"])
            
    try:
        sh.worksheet("registros")
    except:
        ws = sh.add_worksheet("registros", 1000, 10)
        ws.append_row(["usuario", "data", "glicemia", "carbos", "icr", "dose"])
            
    return sh

# --- 4. APP PRINCIPAL ---
def main():
    st.title("💉 Controle de Insulina")
    sh = preparar_abas()

    if 'logado' not in st.session_state: st.session_state.logado = False
    if 'usuario_atual' not in st.session_state: st.session_state.usuario_atual = ""

    # --- TELA DE LOGIN / CADASTRO ---
    if not st.session_state.logado:
        tab1, tab2 = st.tabs(["Login", "Cadastro"])
        
        with tab1:
            with st.form("login"):
                u = st.text_input("Usuário").lower().strip()
                p = st.text_input("Senha", type="password").strip()
                if st.form_submit_button("Entrar"):
                    ws = sh.worksheet("usuarios")
                    try:
                        df = pd.DataFrame(ws.get_all_records()).astype(str)
                    except:
                        df = pd.DataFrame()
                    
                    if not df.empty and 'usuario' in df.columns:
                        achou = df[(df['usuario'] == u) & (df['senha'] == p)]
                        if not achou.empty:
                            st.session_state.logado = True
                            st.session_state.usuario_atual = u
                            st.rerun()
                        else:
                            st.error("Dados incorretos.")
                    else:
                        st.warning("Nenhum usuário cadastrado.")
        
        with tab2:
            with st.form("cadastro"):
                nu = st.text_input("Novo Usuário").lower().strip()
                np = st.text_input("Nova Senha", type="password").strip()
                if st.form_submit_button("Criar Conta"):
                    ws = sh.worksheet("usuarios")
                    existing = ws.col_values(1)
                    if nu in existing:
                        st.error("Usuário já existe.")
                    else:
                        ws.append_row([nu, np, str(datetime.now())])
                        st.success("Criado! Faça login.")

    # --- ÁREA LOGADA ---
    else:
        c_user, c_logout = st.columns([3, 1])
        c_user.success(f"Olá, **{st.session_state.usuario_atual}**!")
        if c_logout.button("Sair"):
            st.session_state.logado = False
            st.rerun()
        
        st.divider()
        
        # 1. FORMULÁRIO DE CÁLCULO
        st.subheader("Nova Medição")
        with st.form("calc"):
            c1, c2 = st.columns(2)
            
            # Glicemia vazia
            glic = c1.number_input("Glicemia (mg/dL)", min_value=0, max_value=900, value=None, placeholder="Digite...")
            
            # Carboidratos (pode ser 0, então deixei 0 como padrão, mas se quiser vazio me avise)
            carbos = c2.number_input("Carboidratos (g)", min_value=0, max_value=500, value=0)
            
            # ICR vazio (Mudança aqui: agora é number_input com value=None)
            icr = st.number_input("Fator ICR (1 UI para X g)", min_value=1, max_value=100, value=None, placeholder="Digite...")
            
            if st.form_submit_button("Calcular e Salvar", use_container_width=True):
                # VERIFICAÇÃO DUPLA: Glicemia E ICR precisam estar preenchidos
                if glic is None or icr is None:
                    st.warning("⚠️ Por favor, informe a Glicemia e o Fator ICR.")
                else:
                    alvo = 100
                    fator = 40
                    corr = (glic - alvo) / fator if glic > alvo else 0
                    ref = carbos / icr
                    dose = round(corr + ref)
                    
                    ws = sh.worksheet("registros")
                    ws.append_row([
                        st.session_state.usuario_atual, 
                        datetime.now().strftime("%Y-%m-%d %H:%M"), 
                        glic, carbos, icr, dose
                    ])
                    st.success(f"✅ Dose Recomendada: **{dose} UI**")
                    st.rerun()

        # 2. VISUALIZAÇÃO DE DADOS
        st.divider()
        
        try:
            ws = sh.worksheet("registros")
            dados = ws.get_all_records()
            
            if dados:
                df = pd.DataFrame(dados)
                df = df[df['usuario'] == st.session_state.usuario_atual]
                
                if not df.empty:
                    df['data'] = pd.to_datetime(df['data'])
                    
                    st.subheader("📈 Evolução da Glicemia")
                    st.line_chart(df, x='data', y='glicemia')
                    
                    st.subheader("📋 Histórico Recente")
                    st.dataframe(
                        df.sort_values(by='data', ascending=False).head(5), 
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("Nenhum registro seu encontrado ainda.")
            else:
                st.info("Comece a registrar para ver o gráfico!")
                
        except Exception as e:
            st.warning(f"Aguardando dados... ({e})")

if __name__ == "__main__":
    main()
