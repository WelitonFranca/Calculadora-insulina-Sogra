import streamlit as st
import pandas as pd
import gspread
import json
from datetime import datetime, timedelta
import time

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Diário Insulina", layout="centered")
st.title("💉 Controle de Insulina (Modo Diagnóstico)")

# --- 2. DIAGNÓSTICO DE HORA (CRUCIAL PARA JWT) ---
st.markdown("### 🕵️‍♂️ Diagnóstico do Sistema")
hora_servidor = datetime.utcnow()
st.write(f"🕒 **Hora UTC do Servidor:** {hora_servidor.strftime('%H:%M:%S')}")
st.info("Se a hora acima estiver muito errada (mais de 5 min de diferença do horário mundial), o Google bloqueia a conexão.")

# --- 3. UPLOAD COM "VACINA" ---
st.markdown("---")
st.warning("📂 **Arraste seu arquivo JSON abaixo:**")
arquivo_chave = st.file_uploader("Solte o arquivo aqui", type=["json"], key="loader_final")

if arquivo_chave is None:
    st.stop()

try:
    # 1. Lê o arquivo
    credenciais = json.load(arquivo_chave)
    
    # 2. APLICANDO A VACINA (Limpeza forçada da chave)
    # Isso conserta o erro de assinatura na maioria dos casos
    if "private_key" in credenciais:
        chave_original = credenciais["private_key"]
        # Força a troca de quebras de linha escapadas por reais
        credenciais["private_key"] = chave_original.replace("\\n", "\n")
    
    # 3. Tenta conectar com a credencial "vacinada"
    gc = gspread.service_account_from_dict(credenciais)
    email_robo = credenciais.get("client_email")
    
    st.success(f"✅ CONEXÃO BEM SUCEDIDA! (Robô: {email_robo})")
    
except Exception as e:
    st.error(f"❌ O erro persiste: {e}")
    st.stop()

# --- 4. PREPARAÇÃO DA PLANILHA ---
def preparar_abas(gc, email_robo):
    try:
        sh = gc.open("banco_dados_insulina")
        return sh
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("❌ CONECTOU, MAS NÃO ACHOU A PLANILHA")
        st.markdown(f"""
        O erro de JWT foi resolvido! Agora falta permissão.
        
        1. Vá na planilha **banco_dados_insulina**
        2. Compartilhe com:
        """)
        st.code(email_robo, language="text")
        st.stop()
    except Exception as e:
        st.error(f"Erro ao abrir planilha: {e}")
        st.stop()

# Carrega a planilha
sh = preparar_abas(gc, email_robo)

# --- 5. APP FUNCIONANDO ---
if 'logado' not in st.session_state: st.session_state.logado = False
if 'usuario_atual' not in st.session_state: st.session_state.usuario_atual = ""

if not st.session_state.logado:
    st.markdown("---")
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

else:
    st.markdown("---")
    c1, c2 = st.columns([3, 1])
    c1.success(f"Olá, **{st.session_state.usuario_atual}**!")
    if c2.button("Sair"):
        st.session_state.logado = False
        st.rerun()
    
    st.divider()
    st.subheader("Nova Medição")
    with st.form("calc"):
        c_glic, c_carb = st.columns(2)
        glic = c_glic.number_input("Glicemia", min_value=0, max_value=900, value=None)
        carbos = c_carb.number_input("Carboidratos", min_value=0, max_value=500, value=0)
        icr = st.number_input("Fator ICR", min_value=1, max_value=100, value=None)
        
        if st.form_submit_button("Calcular"):
            if glic and icr:
                dose = round(((glic - 100) / 40) + (carbos / icr))
                st.success(f"Dose: {dose} UI")
                ws = sh.worksheet("registros")
                ws.append_row([st.session_state.usuario_atual, str(datetime.now()), glic, carbos, icr, dose])
