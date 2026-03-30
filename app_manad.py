import streamlit as st
import pandas as pd
import re
import gc

st.set_page_config(page_title="Consolidador FOPAG - Ultra Performance", layout="wide")

# --- FUNÇÃO DE LIMPEZA ---
def limpar_sessao():
    for key in st.session_state.keys():
        del st.session_state[key]
    st.cache_data.clear()
    st.rerun()

with st.sidebar:
    st.header("Configurações")
    if st.button("🗑️ Limpar Tudo e Reiniciar"):
        limpar_sessao()
    st.divider()
    st.write("Versão: 3.0 (Memória Otimizada)")

def extrair_valor_bruto(texto):
    padrao = r'\d+(?:\.\d+)*(?:,\d{2})'
    encontrados = re.findall(padrao, texto)
    if encontrados:
        return float(encontrados[-1].replace('.', '').replace(',', '.'))
    return 0.0

st.title("📊 Consolidador Ultra-Light (4.5M Linhas)")
st.warning("⚠️ Otimizado para evitar o erro 'Oh no' (Out of Memory).")

arquivos_enviados = st.file_uploader("Selecione os arquivos MANAD (.txt)", type=['txt'], accept_multiple_files=True)

if arquivos_enviados:
    nomes_arquivos = [arq.name for arq in arquivos_enviados]
    duplicados = [nome for nome in set(nomes_arquivos) if nomes_arquivos.count(nome) > 1]
    
    if duplicados:
        st.error(f"Arquivos duplicados: {', '.join(list(set(duplicados)))}")
    else:
        if st.button("🚀 Iniciar Processamento Pesado"):
            lista_final_dados = []
            progresso = st.progress(0)
            status = st.empty()
            
            contador_global = 1
            total_arqs = len(arquivos_enviados)
            
            for i, arquivo in enumerate(arquivos_enviados):
                status.text(f"Processando arquivo {i+1}/{total_arqs}: {arquivo.name}")
                
                tabela_verbas = {}
                cnpj_full, data_ref = "00000000000000", "01/01/2000"
                
                # Lendo o arquivo de forma eficiente
                linhas = arquivo.getvalue().decode('latin-1').splitlines()
                soma_arquivo = {}

                for linha in linhas:
                    parts = linha.strip().split('|')
                    if not parts or len(parts) < 2: continue
                    reg = parts[0]
                    
                    if reg == '0000':
                        for campo in parts:
                            limpo = re.sub(r'\D', '', campo)
                            if len(limpo) == 14: cnpj_full = limpo
                            if len(limpo) == 8 and campo.isdigit():
                                data_ref = f"01/{limpo[2:4]}/{limpo[4:8]}"
                    
                    elif reg == 'K150' and len(parts) >= 5:
                        tabela_verbas[parts[3].strip()] = parts[4].strip().upper()
                    
                    elif reg == 'K300':
                        try:
                            cod_v = parts[6].strip() if len(parts[6]) > 1 else parts[7].strip()
                            nome_v = tabela_verbas.get(cod_v, f"RUBRICA_{cod_v}")
                            valor = extrair_valor_bruto(linha)
                            if valor > 0:
                                soma_arquivo[nome_v] = soma_arquivo.get(nome_v, 0.0) + valor
                        except: continue

                # Montando os dados deste arquivo
                for rubrica, valor in soma_arquivo.items():
                    lista_final_dados.append({
                        'ID_SEQUENCIAL': f"{contador_global:02d}",
                        'CNPJ_RAIZ': cnpj_full[:8],
                        'DATA_REF': data_ref,
                        'RUBRICA': rubrica,
                        'VALOR': valor,
                        'INSS Patr': valor * 0.20,
                        'Terceiros': valor * 0.058,
                        'RAT/SAT': valor * 0.03,
                        'ORIGEM': arquivo.name
                    })
                    contador_global += 1
                
                # --- AQUI ESTÁ O SEGREDO ---
                # Limpa as variáveis pesadas do arquivo atual antes de ir para o próximo
                del linhas, soma_arquivo, tabela_verbas
                gc.collect() 
                progresso.progress((i + 1) / total_arqs)

            # Criando o DataFrame final
            df_final = pd.DataFrame(lista_final_dados)
            
            if not df_final.empty:
                st.success(f"✅ Processado com sucesso! {len(df_final)} registros.")
                csv_data = df_final.to_csv(index=False, sep=';', decimal=',', encoding='utf-8-sig')
                
                st.download_button(
                    label="📥 Baixar Base para Power BI",
                    data=csv_data,
                    file_name="FOPAG_CONTAX_FINAL.csv",
                    mime="text/csv"
                )
                # Limpa a lista após gerar o DataFrame para liberar RAM
                del lista_final_dados
                gc.collect()
