import streamlit as st
import pandas as pd
import re
import gc

st.set_page_config(page_title="Consolidador FOPAG - Auditoria Contax", layout="wide")

# --- FUNÇÃO DE LIMPEZA ---
def limpar_sessao():
    for key in st.session_state.keys():
        del st.session_state[key]
    st.cache_data.clear()
    st.rerun()

# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.header("Configurações")
    if st.button("🗑️ Limpar Tudo e Reiniciar"):
        limpar_sessao()
    st.divider()
    st.write("Versão: 2.1 (Proteção de Dados)")

def extrair_valor_bruto(texto):
    padrao = r'\d+(?:\.\d+)*(?:,\d{2})'
    encontrados = re.findall(padrao, texto)
    if encontrados:
        return float(encontrados[-1].replace('.', '').replace(',', '.'))
    return 0.0

st.title("📊 Consolidador de Alta Performance - Auditoria e Encargos")
st.info("Verificador de arquivos duplicados e cálculos de encargos ativos.")

# Upload de múltiplos arquivos
arquivos_enviados = st.file_uploader("Selecione os arquivos MANAD (.txt)", type=['txt'], accept_multiple_files=True)

if arquivos_enviados:
    # --- VERIFICADOR DE DUPLICIDADE DE ARQUIVOS ---
    nomes_arquivos = [arq.name for arq in arquivos_enviados]
    duplicados = [nome for nome in set(nomes_arquivos) if nomes_arquivos.count(nome) > 1]
    
    if duplicados:
        st.error(f"⚠️ **Atenção:** Os seguintes arquivos foram enviados mais de uma vez: {', '.join(list(set(duplicados)))}")
        st.warning("Remova os arquivos duplicados da lista acima para liberar o botão de consolidação.")
    else:
        if st.button("🚀 Iniciar Consolidação com Encargos"):
            lista_final_dados = []
            progresso = st.progress(0)
            status = st.empty()
            
            contador_global = 1
            total_arquivos = len(arquivos_enviados)
            
            for i, arquivo in enumerate(arquivos_enviados):
                status.text(f"Processando: {arquivo.name} ({i+1}/{total_arquivos})")
                
                tabela_verbas = {}
                cnpj_full, data_ref = "00000000000000", "01/01/2000"
                nome_arquivo_origem = arquivo.name
                
                conteudo = arquivo.getvalue().decode('latin-1').splitlines()
                soma_arquivo = {}

                for linha in conteudo:
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

                cnpj_raiz = cnpj_full[:8]
                
                for rubrica, valor in soma_arquivo.items():
                    inss_patr = valor * 0.20
                    terceiros = valor * 0.058
                    rat_sat = valor * 0.03
                    
                    lista_final_dados.append({
                        'ID_SEQUENCIAL': f"{contador_global:02d}",
                        'CNPJ_RAIZ': cnpj_raiz,
                        'CNPJ_COMPLETO': cnpj_full,
                        'DATA_REF': data_ref,
                        'RUBRICA': rubrica,
                        'VALOR': valor,
                        'INSS Patr': inss_patr,
                        'Terceiros': terceiros,
                        'RAT/SAT': rat_sat,
                        'ORIGEM': nome_arquivo_origem
                    })
                    contador_global += 1
                
                del conteudo, soma_arquivo
                gc.collect()
                progresso.progress((i + 1) / total_arquivos)

            df_final = pd.DataFrame(lista_final_dados)
            
            if not df_final.empty:
                df_final = df_final.drop_duplicates()
                st.success(f"✅ Sucesso! {len(df_final)} linhas consolidadas sem duplicidade de arquivos.")
                
                csv_data = df_final.to_csv(index=False, sep=';', decimal=',', encoding='utf-8-sig')
                
                st.download_button(
                    label="📥 Baixar Base FOPAG com Encargos (CSV)",
                    data=csv_data,
                    file_name="FOPAG_CONTAX_BI.csv",
                    mime="text/csv"
                )
