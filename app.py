import streamlit as st
import pandas as pd
import gspread
import json
import time
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta, timezone

# 
# 👇 ÁREA DE CONFIGURAÇÃO DA CHAVE
# 
# 1. Mantenha as três aspas (""") do começo e do fim.
# 2. Apague o texto de aviso dentro.
# 3. Cole todo o conteúdo do seu arquivo JSON nesse espaço.

CHAVE_MESTRA = """{  "type": "service_account",
  "project_id": "insulina-app-v2",
  "private_key_id": "c61fedf8f10ce140776ce5b174938405cadcf8bc",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQCnH9y/zmfYk01z\n6yUfH0YXHP/9sSi94SOVLfZdKmE+eYbYgEPvogut92Rp+claAEOeoa3Tg9J/QoHg\nmVx9O6Aga4Dv+9yvo33hFB4K7XTDiUklD4jsiTFaoGLjFKF9iagIfn7NXt6f7Mei\ngFt4vZIYrbhZ6/i04FiJJBz4Gi87TG13mUi6gapiTJcJzptbTOCk8NrevpggtZA4\nZldDnoUVSzyElBgGSOveZOpNw/IBx0McX43ONQIJqzAU7baYFqtsagwKuXFsph2V\nmnGmG+2ySgjn7eM5YR/zg66kKYgi8hXtMOd32d5I/YR8j/LNN+nxrCsWE9vZsUX4\ntLli6NR5AgMBAAECggEACK7FOGJb/xKlGCAH/1JPwQjozFiBTD8nivs2tN+sKnOk\nI7ijPu6RcoX7Pa3EbiR8HuBZwHbVb3boOj/hgCCiSLjpG56/WBEzi6dwyaLNWZDW\n/+HLHHXivml9hbx3SOdHV3yh8B/NC2xA8XJ/fhoEPnu9C4/wzY3nz6U0i5fJqygP\neOwc5q2vnwMQ9uJ8ky9r+QRUv5lJKOjncEE0JY7L6vVDytp4KvOeLqPgl4OzW3sU\nO+w2C+24ZFRSqf2ZVwrxIhmInT3NRLrbrmWp+gvb5zgbQ8OYXWUGT54m6+egaEqA\nYjzXCetRPhndh766aFQigg4yd6zZNzp5Lb1LdQFvsQKBgQDWKddSii+7zj7rsbfM\nMXJtmPZ0uApqpOR8LgKd3hwBHRXHO0p0RLHG1WCEmfhv6VZurE9wR4U1CDsovSmK\nfWLOGOe7qtxRY5taehSXIR4gCjKDzvsYNIjMrZK+EHSjUUSKX81FuMyC5btaXTsk\nwmbv7EzveWLOltSC/NL9z8uC6QKBgQDHxaLFyzm6RXg4MMec5d3Ih2INNgekqt6A\nRMxyhe3FRyZuJOMfHVytYCdVAnvPmVMC/ypZKDuOtcPmRl58cvM7v2hbzQf9cBWy\n85KurfFV6qGLXc+RZhaJMJweA3BzaB0glPAf9vH6HLdXiTieCBGe9yfgDdxgcI1Q\nxPD9eygrEQKBgQCEQWKPvnar7Do/I4j1uLOJqyTH/7+vDBVt+pvzEe8JYQTJ/HuG\nQcXnnG32dX9O3TJbNl34YLKKhYLDLc4xkC0sSYUSB/n26SRPQ4Tjr7gC4UlAzNmT\noR26CJbOeSsOkGlbar5BiFYDoAuLSnfzw3n+QFdiq/uwyMSD/83soB51wQKBgQCk\nBPCP1TugZElAWUyK1XAypHUsw5+i42eriNETdkKyJqi25jJT6ZeeAcRJV7Cv0gMG\nAtqSOSYtFa+x8TTCmN57v7u/I6fbvZsTQki8grQTBoF8G5nAl0EJgo+rVMeO+Xxw\ns9gzZl1mLQ2bIV8K4TUWf3aNztORmtdr6Uaz19ozAQKBgQCBwepmF7kRqrXhFJTj\nw/dYBkMQcfRv7U7poSVw6PM6hdZ8GipKXqpBe1S94PzR0hQs0l16BJO3+Mg9YpKv\nwl8tLo5p98DKch3ONgzpjQpt/F6/HusaMrO/1tq6l1BhTTtauyU63v5E3CQOITyx\nqfeDDhZx5I+PbYI80yNvnG8CBQ==\n-----END PRIVATE KEY-----\n",
  "client_email": "robo-insulina@insulina-app-v2.iam.gserviceaccount.com",
  "client_id": "108745775536733403179",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/robo-insulina%40insulina-app-v2.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}"""
# 


# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Diário Insulina", layout="centered")

# --- 2. CONEXÃO AUTOMÁTICA (SEM UPLOAD) ---
def conectar_seguro():
    if 'conexao_google' in st.session_state:
        return st.session_state.conexao_google

    # Tenta ler a chave que você colou acima
    try:
        if "COLE_O_CONTEUDO" in CHAVE_MESTRA:
            st.error("⚠️ VOCÊ PRECISA COLAR A CHAVE NO CÓDIGO!")
            st.info("Abra o arquivo 'app.py', procure a variável 'CHAVE_MESTRA' no topo e cole o conteúdo do seu JSON lá.")
            st.stop()

        info_conta = json.loads(CHAVE_MESTRA)
        
        escopos = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(info_conta, scopes=escopos)
        gc = gspread.authorize(creds)
        email = info_conta.get("client_email")
        
        st.session_state.conexao_google = (gc, email)
        return st.session_state.conexao_google

    except json.JSONDecodeError:
        st.error("❌ Erro ao ler a chave colada.")
        st.warning("Verifique se você copiou o JSON completo, incluindo as chaves { e }.")
        st.stop()
    except Exception as e:
        st.error(f"❌ Erro de conexão: {e}")
        st.stop()

# --- 3. PREPARAÇÃO DA PLANILHA ---
def preparar_planilha(gc, email):
    try: sh = gc.open("banco_dados_insulina")
    except: st.error("❌ PLANILHA NÃO ENCONTRADA"); st.stop()
    try: sh.worksheet("usuarios")
    except: sh.add_worksheet("usuarios", 100, 5).append_row(["usuario", "senha", "criado_em"])
    try: sh.worksheet("registros")
    except: sh.add_worksheet("registros", 1000, 10).append_row(["usuario", "data", "glicemia", "carbos", "icr", "dose"])
    return sh

# --- 4. APP PRINCIPAL ---
def main():
    st.title("💉 Controle de Insulina")
    
    # Conecta automaticamente usando a CHAVE_MESTRA
    gc, email_robo = conectar_seguro()
    sh = preparar_planilha(gc, email_robo)

    if 'logado' not in st.session_state: st.session_state.logado = False
    if 'usuario_atual' not in st.session_state: st.session_state.usuario_atual = ""
    if 'ultimo_resultado' not in st.session_state: st.session_state.ultimo_resultado = None

    # --- TELA DE LOGIN ---
    if not st.session_state.logado:
        tab1, tab2 = st.tabs(["Login", "Cadastro"])
        with tab1:
            with st.form("login"):
                u = st.text_input("Usuário").lower().strip()
                p = st.text_input("Senha", type="password").strip()
                if st.form_submit_button("Entrar"):
                    ws = sh.worksheet("usuarios")
                    try: dados = ws.get_all_records(); df = pd.DataFrame(dados).astype(str)
                    except: df = pd.DataFrame()
                    if not df.empty and 'usuario' in df.columns:
                        if not df[(df['usuario'] == u) & (df['senha'] == p)].empty:
                            st.session_state.logado = True; st.session_state.usuario_atual = u; st.rerun()
                        else: st.error("Dados incorretos.")
                    else: st.warning("Sem usuários.")
        with tab2:
            with st.form("cadastro"):
                nu = st.text_input("Novo Usuário").lower().strip()
                np = st.text_input("Nova Senha", type="password").strip()
                if st.form_submit_button("Criar Conta"):
                    ws = sh.worksheet("usuarios")
                    if nu in ws.col_values(1): st.error("Existe.")
                    else: ws.append_row([nu, np, str(datetime.now())]); st.success("Criado!")

    # --- ÁREA LOGADA ---
    else:
        c1, c2 = st.columns([3, 1])
        c1.success(f"Olá, **{st.session_state.usuario_atual}**!")
        if c2.button("Sair"): st.session_state.logado = False; st.rerun()
        
        st.divider()
        
        # --- CÁLCULO ---
        st.subheader("Nova Medição")
        with st.form("calc"):
            with st.expander("⚙️ Configurações (Meta e Fator)", expanded=True):
                col_a, col_b = st.columns(2)
                alvo = col_a.number_input("Meta", value=100, step=10)
                fator = col_b.number_input("Sensibilidade", value=40, step=5)

            c_glic, c_carb = st.columns(2)
            glic = c_glic.number_input("Glicemia", min_value=0, max_value=900, value=None)
            carbos = c_carb.number_input("Carboidratos (g)", min_value=0, max_value=500, value=0)
            icr = st.number_input("Fator ICR", min_value=1, max_value=100, value=None)
            
            if st.form_submit_button("Calcular e Salvar", use_container_width=True):
                if glic and icr:
                    correcao = (glic - alvo) / fator
                    bolus_alim = carbos / icr
                    total = max(0, correcao + bolus_alim)
                    dose = round(total)
                    
                    fuso_brasilia = timezone(timedelta(hours=-3))
                    agora = datetime.now(fuso_brasilia)
                    data_formatada = agora.strftime("%d/%m/%Y %H:%M")
                    
                    ws = sh.worksheet("registros")
                    ws.append_row([st.session_state.usuario_atual, data_formatada, glic, carbos, icr, dose])
                    
                    # AQUI ESTAVA O ERRO, AGORA CORRIGIDO COM O SINAL < CORRETO
                    msg_status = "Glicemia Alta" if glic > alvo + 40 else "Hipoglicemia" if glic < 70 else "Glicemia OK"

                    st.session_state.ultimo_resultado = {
                        "glic": glic, "alvo": alvo, "fator": fator,
                        "carbos": carbos, "icr": icr,
                        "correcao": correcao, "bolus": bolus_alim,
                        "total": total, "dose": dose,
                        "msg": msg_status
                    }
                    
                    st.toast("💾 Salvando e atualizando...")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.warning("Preencha Glicemia e ICR.")

        # --- MEMÓRIA DE CÁLCULO ---
        if st.session_state.ultimo_resultado:
            res = st.session_state.ultimo_resultado
            st.markdown("---")
            st.markdown(f"<h3 style='text-align:center'>Resultado: {res['dose']} UI</h3>", unsafe_allow_html=True)
            st.warning(f"""
            **📝 Memória de Cálculo:**
            1. **Correção:** ({res['glic']} - {res['alvo']}) ÷ {res['fator']} = **{res['correcao']:.2f}**
            2. **Comida:** {res['carbos']}g ÷ {res['icr']} = **{res['bolus']:.2f}**
            3. **Soma:** {res['correcao']:.2f} + {res['bolus']:.2f} = **{res['total']:.2f}**
            👉 **Dose Final:** {res['dose']} UI
            """)
            if st.button("Limpar Resultado"):
                st.session_state.ultimo_resultado = None
                st.rerun()

        # --- HISTÓRICO E GRÁFICOS ---
        st.divider()
        st.subheader("📊 Análise e Histórico")
        
        try:
            ws = sh.worksheet("registros")
            dados = ws.get_all_records()
            
            if len(dados) > 0:
                df = pd.DataFrame(dados)
                if 'usuario' in df.columns:
                    df = df[df['usuario'] == st.session_state.usuario_atual].copy()
                    
                    if not df.empty:
                        df['data_original'] = df['data'].astype(str)
                        df['data_obj'] = pd.to_datetime(df['data_original'], dayfirst=True, errors='coerce')
                        
                        df['glicemia'] = pd.to_numeric(df['glicemia'], errors='coerce').fillna(0)
                        df['carbos'] = pd.to_numeric(df['carbos'], errors='coerce').fillna(0)
                        df['dose'] = pd.to_numeric(df['dose'], errors='coerce').fillna(0)
                        
                        df_grafico = df.dropna(subset=['data_obj']).sort_values('data_obj')
                        df_grafico['Data_X'] = df_grafico['data_obj'].dt.strftime('%d/%m %H:%M')
                        
                        col_tipo, col_dados = st.columns([1, 2])
                        with col_tipo:
                            tipo_grafico = st.selectbox("Tipo de Gráfico:", ["Linha", "Barra", "Área", "Dispersão (Pontos)"])
                        with col_dados:
                            opcoes = st.multiselect("Dados:", ["Glicemia", "Carboidratos", "Dose Insulina"], default=["Glicemia"])
                        
                        mapa = {"Glicemia": "glicemia", "Carboidratos": "carbos", "Dose Insulina": "dose"}
                        
                        if opcoes and not df_grafico.empty:
                            cols = [mapa[o] for o in opcoes]
                            if tipo_grafico == "Linha": st.line_chart(df_grafico, x='Data_X', y=cols)
                            elif tipo_grafico == "Barra": st.bar_chart(df_grafico, x='Data_X', y=cols)
                            elif tipo_grafico == "Área": st.area_chart(df_grafico, x='Data_X', y=cols)
                            elif tipo_grafico == "Dispersão (Pontos)": st.scatter_chart(df_grafico, x='Data_X', y=cols)
                        elif df_grafico.empty:
                            st.info("Aguardando dados válidos...")
                        else:
                            st.info("Selecione um dado.")

                        st.markdown("### 📋 Tabela Detalhada")
                        df['id'] = df.index + 2
                        df_show = df.sort_values('id', ascending=False)
                        df_show['Apagar'] = False
                        
                        config_tabela = {
                            "data_original": st.column_config.TextColumn("Data/Hora"),
                            "glicemia": st.column_config.NumberColumn("Glicemia", format="%d"),
                            "carbos": st.column_config.NumberColumn("Carbos (g)", format="%d"),
                            "dose": st.column_config.NumberColumn("Dose (UI)", format="%d"),
                            "Apagar": st.column_config.CheckboxColumn(default=False),
                            "id": None
                        }

                        edit = st.data_editor(
                            df_show[['Apagar', 'data_original', 'glicemia', 'carbos', 'dose', 'id']], 
                            column_config=config_tabela,
                            hide_index=True, use_container_width=True
                        )
                        
                        if st.button("🗑️ Apagar Selecionados"):
                            for L in sorted(edit[edit['Apagar']]['id'].tolist(), reverse=True): ws.delete_rows(L)
                            st.success("Apagado!"); time.sleep(1); st.rerun()
            else: st.info("Sem dados.")
        except Exception as e: 
            st.error(f"Erro ao ler histórico: {e}")

if __name__ == "__main__":
    main()
