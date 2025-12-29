        # 2. VISUALIZAÇÃO DE DADOS
        st.divider()
        st.subheader("📋 Histórico")
        
        try:
            # Força a leitura atualizada da planilha
            ws = sh.worksheet("registros")
            dados = ws.get_all_records()
            
            # Se a lista não estiver vazia
            if len(dados) > 0:
                df = pd.DataFrame(dados)
                
                # Garante que as colunas existem (evita erro se a planilha estiver estranha)
                if 'usuario' in df.columns and 'data' in df.columns:
                    # Filtra pelo usuário logado
                    df_filtrado = df[df['usuario'] == st.session_state.usuario_atual].copy()
                    
                    if not df_filtrado.empty:
                        # Converte data
                        df_filtrado['data'] = pd.to_datetime(df_filtrado['data'], errors='coerce')
                        
                        # Mostra Gráfico
                        st.caption("Evolução da Glicemia")
                        st.line_chart(df_filtrado, x='data', y='glicemia')
                        
                        # Mostra Tabela (Do mais recente para o mais antigo)
                        st.caption("Últimos Registros")
                        st.dataframe(
                            df_filtrado.sort_values(by='data', ascending=False).head(10), 
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.info("Nenhum registro encontrado para este usuário.")
                else:
                    st.warning("A estrutura da planilha parece incorreta. Tente excluir a aba 'registros' novamente.")
            else:
                st.info("O histórico está vazio. Faça seu primeiro registro acima! 👆")
                
        except Exception as e:
            st.error(f"Erro ao carregar histórico: {e}")
            # Dica: Se der erro aqui, geralmente um 'Reboot app' resolve.

if __name__ == "__main__":
    main()
