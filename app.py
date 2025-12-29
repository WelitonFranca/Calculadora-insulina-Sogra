import streamlit as st
import pandas as pd
import gspread
import glob
from datetime import datetime, timedelta

# 1. CONFIGURAÇÃO
st.set_page_config(page_title="Diário Insulina", layout="centered")

# 2. CONEXÃO
@st.cache_resource(ttl=600)
def conectar_banco():
    arquivos = glob.glob("*.json")
    if not arquivos:
        st.error("Erro: Nenhum arquivo .json encontrado.")
        st.stop()
    
    # Pega o primeiro arquivo json que encontrar
    chave = arquivos[0]
    
    try:
        return gspread.service_account(filename=chave)
    except Exception as e:
        st.error(f"Erro na chave: {e}")
        st.stop()

# 3. PREPARAÇÃO
def preparar_abas():
    gc = conectar_banco()
    try:
        sh = gc.open("banco_dados_insulina")
    except:
        st.error("Planilha não encontrada.")
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

# 4. APP PRINCIPAL
def main():
    st.title("💉 Controle de Insulina")
    sh = preparar_abas()

    if 'logado' not in st.session_state: st.session_state.logado = False
    if 'usuario_atual' not in st.session_state: st.session_state.usuario_atual = ""

    # TELA DE LOGIN
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

    # ÁREA LOGADA
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

        # HISTÓRICO E EXCLUSÃO
        st.divider()
        st.subheader("Histórico")
        
        try:
            ws = sh.worksheet("registros")
            dados = ws.get_all_records()
            
            if len(dados) > 0:
                df = pd.DataFrame(dados)
                if 'usuario' in df.columns:
                    # Adiciona ID da linha para apagar
                    df['id_linha'] = df.index + 2
                    
                    # Filtra usuário
                    df = df[df['usuario'] == st.session_state.usuario_atual].copy()
                    
                    if not df.empty:
                        # Arruma dados
                        df['data'] = pd.to_datetime(df['data'], errors='coerce')
                        df['glicemia'] = pd.to_numeric(df['glicemia'], errors='coerce')
                        df = df.dropna(subset=['data', 'glicemia'])

                        # Gráfico
                        st.line_chart(df, x='data', y='glicemia')
                        
                        # Tabela de Exclusão
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
