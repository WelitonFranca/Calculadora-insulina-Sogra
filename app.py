import streamlit as st
import pandas as pd
import gspread
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Diário Insulina", layout="centered")

# --- 2. CREDENCIAIS BLINDADAS ---
def carregar_credenciais():
    # AQUI ESTÁ O SEGREDO: 
    # Eu quebrei sua chave em linhas. O Python vai montar ela perfeitamente.
    # Não mexa em nada aqui!
    
    pk_linhas = [
        "-----BEGIN PRIVATE KEY-----",
        "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDReGYniVdLvFTr",
        "oIbqejXl2IpU/QJg8HFciqX4kuITEIeyEDL7cRYgUGPWnDAqVIG5jjK85JCkfELy",
        "zL6sLnAEjozQYQ7oY6/tPO3ltJipaYLvmj3ZTxwOWZgLsy2LUTJ+71sXLgDRK80d",
        "XaP1J02shLt2x4GdK8dEcjE3AtSSqcO0VMkYQIbeAa+uRWZXQF9LhJngYDQDVrad",
        "FFdIYszuDSttnf1DUcxTOGn7UPiRmUWhUqeUnI5awMLfoQcAfkOduOsyUm/YHt8y",
        "tYimMaCM2ihanFSTllE05tvAEaHCy7k6Vqp865NM2w72y+MJzFKb+4/Ar3DKPEVz",
        "+XhLXt7/AgMBAAECggEAXC6Y/iMxuJGr6Xnehce8emb+EYK6jkCiErCtc6PoO62V",
        "meYJGaBdtWDLXwGjLK293RPX/kqz4L8Sk1lJO+q/vzGghH+CGQDtxgB/TQxZ9owJ",
        "ZDpDp6Np3GLPR67Vhy73gucA9kV3dJXLEXZJFjTyuM481Xvc7Xb7nYKHaAcl11h0",
        "ZyllLvm/roql2ke+Agn0kGJefMl+cs2ViqMzIdlKWQfrjNQVqiy5Y823gcjnVX1U",
        "/QSIVU+VF/c6MkiRMj7AiykZtj7GUutRrV0s9tjieARb2HIAH+jdJdlCD2Ysx4ek",
        "eis1GwS/6gCetakI1knVr775QVbtbLplODYL/FUWUQKBgQDv2KUH2328dDi38TdA",
        "ZITzm4ZvoACAuWy7UZBsEd3WVN3VxgoTVuBs+9iuadpQ7NVRqVVs4hfm/bcIkrrq",
        "I3KF3euW8whaWuxv9c8Se+YJptVeAq0i4fQgszqaZRNWazNELANYGwdejLLsvE93",
        "Aj+k3dKSv6IGkBCe3MO1WBaA9wKBgQDflAV/EgpD6uw2OlslrMmeB9LuEa9WA7GU",
        "L7wknYG9TJ/1z6F0XT0juUTqLo1As8TvHDw0A9EHw3eULB74QmwIXSC/znxTzZVh",
        "tpqVn1kGeVASNRZpyKHMZNJKdOaqBNanMNJGwuj/9PT0rpJptb1x7fGpoG7KHtVP",
        "2Lbh86MYOQKBgEIJKAbty8SjSyp543h7NI/N9kmth/XpF6LLZjQbBzUH0LwW9pc0",
        "iD35aUM8Kbu2OVVuhfKgnWwf1tEpdQUaFWH+I+s/psEZ35dD2muAaWmm4YAsxHai",
        "N5D5R91SjuxwP4E5jQIpDvJdUrYTct2VZOiDmoKE+JtN9wWGSuwXALspAoGBAI+9",
        "RINbf8oGgPKkNfFU0xKMiSmRqR4tpb9VqSoJMV4Yo0aPxIdhYmtTM2EzqJCOgvAP",
        "QQ1X3s2U944Fh6uoWHhQFzv5bqkaJQ37Lgs/tSaaW8Y45z3/RTZ5I1HHMnzgO3il",
        "xKrFqLLWM54TlgHsW+2hQpsBj/jWNeHtvDYsQxDRAoGABe2oAm62jBBg1yvOs/QP",
        "1HTzHX1oew9ESOUgq+pYz3pLE2yX9TQCGHCNkbh1Bp+WATyMfzZjVLGc+HW9ldJK",
        "iXrIBNShhwHFm11Y3XfKaHgD9+B2KcxrfJnypLdPJdVxWMhCgD3PvH3IyRRYtlRd",
        "TmJ9tV5SF0HC2FKdEwJ/cro=",
        "-----END PRIVATE KEY-----"
    ]
    
    # Reconstrói a chave inserindo as quebras de linha reais
    chave_privada_real = "\n".join(pk_linhas)

    credenciais = {
        "type": "service_account",
        "project_id": "insulina-app-v2",
        "private_key_id": "305b1aadccf01a38484936d7f561cc14ad509aa8",
        "private_key": chave_privada_real,
        "client_email": "robo-insulina@insulina-app-v2.iam.gserviceaccount.com",
        "client_id": "108745775536733403179",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/robo-insulina%40insulina-app-v2.iam.gserviceaccount.com",
        "universe_domain": "googleapis.com"
    }
    return credenciais

# --- 3. CONEXÃO ---
@st.cache_resource(ttl=600)
def conectar_banco():
    credenciais = carregar_credenciais()
    try:
        gc = gspread.service_account_from_dict(credenciais)
        return gc, credenciais.get("client_email")
    except Exception as e:
        st.error(f"❌ Erro de Conexão: {e}")
        st.stop()

# --- 4. PREPARAÇÃO ---
def preparar_abas():
    gc, email_robo = conectar_banco()
    
    try:
        sh = gc.open("banco_dados_insulina")
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("❌ PLANILHA NÃO ENCONTRADA")
        st.markdown(f"""
        **CONEXÃO REALIZADA!** (O erro JWT sumiu! 🎉)
        
        Agora, o último passo:
        1. Vá na planilha **banco_dados_insulina**
        2. Compartilhe com este e-mail (Editor):
        """)
        st.code(email_robo, language="text")
        st.stop()
    except Exception as e:
        st.error(f"Erro ao abrir planilha: {e}")
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

# --- 5. APP PRINCIPAL ---
def main():
    st.title("💉 Controle de Insulina")
    
    sh = preparar_abas()

    if 'logado' not in st.session_state: st.session_state.logado = False
    if 'usuario_atual' not in st.session_state: st.session_state.usuario_atual = ""

    # --- TELA DE LOGIN ---
    if not st.session_state.logado:
        tab1, tab2 = st.tabs(["Login", "Cadastro"])
        
        with tab1:
            with st.form("login"):
                u = st.text_input("Usuário").lower().strip()
                p = st.text_input("Senha", type="password").strip()
                if st.form_submit_button("Entrar"):
                    ws = sh.worksheet("usuarios")
                    try:
                        dados = ws.get_all_records()
                        df = pd.DataFrame(dados).astype(str)
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
                        st.warning("Sem usuários.")
        
        with tab2:
            with st.form("cadastro"):
                nu = st.text_input("Novo Usuário").lower().strip()
                np = st.text_input("Nova Senha", type="password").strip()
                if st.form_submit_button("Criar Conta"):
                    ws = sh.worksheet("usuarios")
                    exist = ws.col_values(1)
                    if nu in exist:
                        st.error("Usuário já existe.")
                    else:
                        d = datetime.now() - timedelta(hours=3)
                        ws.append_row([nu, np, str(d)])
                        st.success("Criado! Faça login.")

    # --- ÁREA LOGADA ---
    else:
        c1, c2 = st.columns([3, 1])
        c1.success(f"Olá, **{st.session_state.usuario_atual}**!")
        if c2.button("Sair"):
            st.session_state.logado = False
            st.rerun()
        
        st.divider()
        
        # CÁLCULO
        st.subheader("Nova Medição")
        with st.form("calc"):
            with st.expander("⚙️ Configurações", expanded=False):
                col_a, col_b = st.columns(2)
                alvo = col_a.number_input("Meta", value=100)
                fator = col_b.number_input("Sensibilidade", value=40)

            c_glic, c_carb = st.columns(2)
            glic = c_glic.number_input("Glicemia", min_value=0, max_value=900, value=None)
            carbos = c_carb.number_input("Carboidratos", min_value=0, max_value=500, value=0)
            icr = st.number_input("Fator ICR", min_value=1, max_value=100, value=None)
            
            if st.form_submit_button("Calcular e Salvar", use_container_width=True):
                if glic is None or icr is None:
                    st.warning("Preencha Glicemia e ICR.")
                else:
                    corr = (glic - alvo) / fator
                    ref = carbos / icr
                    total = max(0, corr + ref)
                    dose = round(total)
                    
                    agora = datetime.now() - timedelta(hours=3)
                    data_txt = agora.strftime("%Y-%m-%d %H:%M")
                    
                    ws = sh.worksheet("registros")
                    ws.append_row([
                        st.session_state.usuario_atual, 
                        data_txt, 
                        glic, carbos, icr, dose
                    ])
                    
                    st.divider()
                    if glic > alvo + 40: st.warning(f"Glicemia Alta ({glic})")
                    elif glic < 70: st.error(f"Hipoglicemia ({glic})")
                    else: st.success(f"Glicemia OK ({glic})")

                    st.markdown(f"<h1 style='text-align:center; color:blue'>{dose} UI</h1>", unsafe_allow_html=True)
                    st.info(f"Cálculo: ({glic}-{alvo})/{fator} + {carbos}/{icr} = {total:.2f}")
                    st.rerun()

        # HISTÓRICO
        st.divider()
        st.subheader("Histórico")
        
        try:
            ws = sh.worksheet("registros")
            dados = ws.get_all_records()
            
            if len(dados) > 0:
                df = pd.DataFrame(dados)
                if 'usuario' in df.columns:
                    df['id_linha'] = df.index + 2
                    df = df[df['usuario'] == st.session_state.usuario_atual].copy()
                    
                    if not df.empty:
                        df['data'] = pd.to_datetime(df['data'], errors='coerce')
                        df['glicemia'] = pd.to_numeric(df['glicemia'], errors='coerce')
                        df = df.dropna(subset=['data', 'glicemia'])

                        st.line_chart(df, x='data', y='glicemia')
                        
                        st.caption("Marque para apagar:")
                        df_show = df.sort_values(by='data', ascending=False).copy()
                        df_show['Apagar'] = False
                        
                        df_edit = st.data_editor(
                            df_show[['Apagar', 'data', 'glicemia', 'carbos', 'dose', 'id_linha']],
                            column_config={
                                "Apagar": st.column_config.CheckboxColumn(default=False),
                                "data": st.column_config.DatetimeColumn(format="DD/MM HH:mm", disabled=True),
                                "id_linha": None
                            },
                            hide_index=True,
                            use_container_width=True
                        )
                        
                        if st.button("🗑️ Apagar Selecionados", type="primary"):
                            linhas = df_edit[df_edit['Apagar'] == True]['id_linha'].tolist()
                            if linhas:
                                for L in sorted(linhas, reverse=True):
                                    ws.delete_rows(L)
                                st.success("Apagado!")
                                st.rerun()
            else:
                st.info("Sem dados.")
        except Exception as e:
            st.error(f"Erro: {e}")

if __name__ == "__main__":
    main()
