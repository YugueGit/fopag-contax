import streamlit as st
import pandas as pd
import re
import gc

# 1. Configuração da Página
st.set_page_config(page_title="Consolidador FOPAG - Ultra Performance", layout="wide")

# Função de Limpeza de Memória e Sessão
def limpar_sessao():
    for key in st.session_state.keys():
        del st.session_state[key]
    st.cache_data.clear()
    st.rerun()

# Barra Lateral
with st.sidebar:
    st.header("Configurações")
    if st.button("🗑️ Limpar Tudo e Reiniciar"):
        limpar_sessao()
    st.divider()
    st.write("Versão: 3.3 (Correção de Parsing e Rubricas)")

def extrair_valor_bruto(linha_texto):
    # Procura valores no formato 1.234,56 ou 1234,56
    padrao = r'\d+(?:\.\d+)*(?:,\d{2})'
    encontrados = re.findall(padrao, linha_texto)
    if encontrados:
        # Retorna o valor que geralmente está na posição de montante (antes dos indicadores P/D)
        return float(encontrados[-1].replace('.', '').replace(',', '.'))
    return 0.0

st.title("📊 Consolidador Ultra-Light (4.5M Linhas)")
st.info("Otimizado para Contax: Auditoria de Rubricas e Encargos Sociais.")

# Upload de arquivos
arquivos_enviados = st.file_uploader("Selecione os arquivos MANAD (.txt)", type=['txt'], accept_multiple_files=True)

if arquivos_enviados:
    nomes_arquivos = [arq.name for arq in arquivos_enviados]
    duplicados = [nome for nome in set(nomes_arquivos) if nomes_arquivos.count(nome) > 1]
    
    if duplicados:
        st.error(f"⚠️ Arquivos duplicados detectados: {', '.join(list(set(duplicados)))}")
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
                
                # Lê o conteúdo do arquivo
                linhas = arquivo.getvalue().decode('latin-1').splitlines()
                soma_arquivo = {}

                for linha in linhas:
                    parts = linha.strip().split('|')
                    if not parts or len(parts) < 2: continue
                    reg = parts[0]
                    
                    # Registro 0000: Dados da Unidade
                    if reg == '0000':
                        for campo in parts:
                            limpo = re.sub(r'\D', '', campo)
                            if len(limpo) == 14: cnpj_full = limpo
                            if len(limpo) == 8 and campo.isdigit() and not cnpj_full.startswith(limpo):
                                data_ref = f"01/{limpo[2:4]}/{limpo[4:8]}"
                    
                    # Registro K150: Tabela de Rubricas
                    elif reg == 'K150' and len(parts) >= 5:
                        tabela_verbas[parts[3].strip()] = parts[4].strip().upper()
                    
                    # Registro K300: Lançamentos da Folha
                    elif reg == 'K300' and len(parts) >= 7:
                        try:
                            # Ajuste de Precisão: Identifica qual campo é o código (numérico simples) 
                            # e qual é o valor (que contém vírgula)
                            campo_6 = parts[6].strip()
                            campo_7 = parts[7].strip() if len(parts) > 7 else ""
                            
                            # Se o campo 6 tem vírgula, ele é o valor, então o código está no 5 ou 7
                            # No MANAD padrão, o código da verba costuma ser o campo index 6
                            if "," in campo_6:
                                cod_v = parts[5].strip() 
                            else:
                                cod_v = campo_6
                                
                            valor = extrair_valor_bruto(linha)
                            
                            if valor > 0 and cod_v:
                                nome_v = tabela_verbas.get(cod_v, f"RUBRICA_NÃO_MAPEADA")
                                chave = (cod_v, nome_v)
                                soma_arquivo[chave] = soma_arquivo.get(chave, 0.0) + valor
                        except: continue

                # Transfere os dados consolidados para a lista final
                for (cod_v, nome_v), valor in soma_arquivo.items():
                    lista_final_dados.append({
                        'ID_SEQUENCIAL': f"{contador_global:02d}",
                        'CNPJ_RAIZ': cnpj_full[:8],
                        'CNPJ_COMPLETO': cnpj_full,
                        'DATA_REF': data_ref,
                        'RUBRICA': nome_v,
                        'CODIGO_RUBRICA': cod_v,
                        'VALOR': valor,
                        'INSS Patr': valor * 0.20,
                        'Terceiros': valor * 0.058,
                        'RAT/SAT': valor * 0.03,
                        'ORIGEM': arquivo.name
                    })
                    contador_global += 1
                
                # Limpeza de memória por ciclo
                del linhas, soma_arquivo, tabela_verbas
                gc.collect() 
                progresso.progress((i + 1) / total_arqs)

            # Geração do DataFrame e Download
            df_final = pd.DataFrame(lista_final_dados)
            if not df_final.empty:
                st.success(f"✅ Concluído! {len(df_final)} registros processados.")
                csv_data = df_final.to_csv(index=False, sep=';', decimal=',', encoding='utf-8-sig')
                st.download_button(
                    label="📥 Baixar Base para Power BI",
                    data=csv_data,
                    file_name="FOPAG_CONTAX_AUDITORIA.csv",
                    mime="text/csv"
                )
                del lista_final_dados, df_final
                gc.collect()
