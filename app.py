import streamlit as st
import pandas as pd
import gspread
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Diário Insulina", layout="centered")

# --- 2. CREDENCIAIS (COM CORREÇÃO DE FORMATAÇÃO) ---
def carregar_credenciais():
    # Dicionário com suas credenciais
    credenciais = {
      "type": "service_account",
      "project_id": "insulina-app-v2",
      "private_key_id": "8aaa2ffb2ea8d252cb73e15fffb49901503825c9",
      "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQCxyu/XEwHPuHEj\nEtJXwbdwwoKCH4xl5JjzDhKB9k3aUkkGnslZrL/o7UQmmXG4OXWoRYH7FGK3iSQg\nDHnNN4eSlQNTqXP//gDyAjg/7PqPEGNMOhxdsJnBZM65k7C+R229i0LtUNqvvXXe\nEvIyWSMCdjhn7esDeje58jNpXDgDa3Q1d/4kj4glFr30/b6UESkMeDDCFZSbZZe3\nvtpcN7Hn/y0EAEBYwObvcc3IQvEHXHexYBInWj/aMDpT/hFGXUsbJzzJWiWXAAyd\no+X5C42Zd2nOQvnu9ZWxF9uPGBCO4RIC4W5RzEtEutafaD7FuSTawSTqqdUUlZLz\n3eQUhu1/AgMBAAECggEAE1WlZXc8sDE3pH/Mfhyj7VBJzwrNQttsQqpaGuYFK2Pd\naynjbawapqL+0U/IjSc6g1UjwIFEBv+T/SQ+LrIGPUuVNAjug31E7wyMv27vBJXc\nppJ/OTUWU3C6BnZoNxkfdwho+9PaJFhvM/pNemo1I3Rlx++YqiUlYERVkPSlZsGf\nRr1HTbTxw7jUwDSJJsTr2R1mAZNX5t4NwT+vxMlKzmxga87yNKhZypS+YtiD7dp/\nfIJg+GcnTQpG3nwUOucfRy2wRzlkvjakqtzNApP36Q3lbKCjrxwLPdl+pUiZSjKc\nJBeZcKe+pj+6Pqge5EKsA/fNfjmBTHnl3KBlz6RDyQKBgQDhFJuECZzGEVo5pxSf\nEytt4K5U6UZNvd1LIWqK+nUUO820SWs/6sz6CBUklxIDC523g03e2zss9G8bQcTP\n9KKkJTj1rxhG7HWA9bE1IyJt/3+CZYJLwdQSfYQZ+8WXbZVkyAWVSvltJPIMbyJK\nvCIsHyNiLRSo1gZT9NoP5wI32wKBgQDKN1zsp2Kz+P2fUI7zonGdyZM4cu3Banur\nQsOf7tCaczfMjxHuFrg/IGIfNAhGzLX5XSquL8a4zcZw1UUMDQm0fdoupPSJJ8eK\nodMoZhffl3YAPzD0TPcvulJUGZ4HF5nTbF2SHKgBJWkCkZpF67hd97dtQCaqNzBe\nscc3bDIULQKBgQCgoyl+qbGW9sly/hjMk0zahZFGDprbXxcxyK6Wc7vdbfUYp5GA\ns54JEH2ueJclT0QHthF8bPCl2+n0BRNm64ysI9isF4P3EkmmeTM43lNzN/cT5EiC\nstodPDFsrfDOaypFHDBH5ZNwXv7U+vf5aJ3m6W5CYjQtb1pizwxWbyN5IwKBgQCO\n/7Gl5QTGsphf9i7xGXnxFCAY9iUt9ug3hwIh8lbwMfROowoR7V0jvvnEiR4lOxSg\noALTpROJknL3TcoDKKEpUypce+g1qbzRS3iwg+n0Av6+U/GBgX/373HS6T64UzdD\nrMlKzxr7nIHzABYxxezd/pRnHMt66YY6IMv5ZHjRjQKBgAwwrGMTDPeMoiK9ecFZ\ngt0n99EuN3wpm+F4FIHlDNMk8w1YH5tiK+Hp5IAA7NZ/X7crNBu41HN3MTOvA4Zq\nlqqZ/EdRfSuykjv8x7FEjdLkEqVhlHlKMZYDKpUoTqMoD5FbncpSYFLwyW+KF/L6\nuVoj3siDZOpf4WS+NRyb2lPe\n-----END PRIVATE KEY-----\n",
      "client_email": "robo-insulina@insulina-app-v2.iam.gserviceaccount.com",
      "client_id": "108745775536733403179",
      "auth_uri": "https://accounts.google.com/o/oauth2/auth",
      "token_uri": "https://oauth2.googleapis.com/token",
      "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
      "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/robo-insulina%40insulina-app-v2.iam.gserviceaccount.com",
      "universe_domain": "googleapis.com"
    }
    
    # --- CORREÇÃO MÁGICA ---
    # Isso garante que o Python entenda as quebras de linha corretamente
    credenciais["private_key"] = credenciais["private_key"].replace("\\n", "\n")
    
    return credenciais

# --- 3. CONEXÃO ---
@st.cache_resource(ttl=600)
def conectar_banco():
    credenciais = carregar_credenciais()
    
    try:
        # Conecta usando o dicionário direto
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
        **Conexão realizada com sucesso!** (O erro JWT sumiu 🎉)
        
        Agora só falta a permissão na planilha.
        
        1. Vá na planilha **banco_dados_insulina** no Google Drive.
        2. Clique em **Compartilhar**.
        3. Cole este e-mail abaixo e dê permissão de **EDITOR**:
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
