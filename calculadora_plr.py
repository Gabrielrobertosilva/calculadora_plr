# Calculadora de PLR – v2 (Streamlit)
# Rodar com: streamlit run calculadora_plr.py

import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

st.set_page_config(page_title="Calculadora de PLR", layout="wide")

# =========================
# Sidebar: Parâmetros Globais
# =========================
st.sidebar.title("Parâmetros Globais")
st.sidebar.markdown("Configure regras gerais, datas e tetos do programa de PLR.")

ano_ref = st.sidebar.selectbox("Ano de referência", options=list(range(2023, 2031)), index=2)
moeda = st.sidebar.selectbox("Moeda", ["BRL", "USD"], index=0)

# Data de assinatura da CCT
if "data_assinatura_cct" not in st.session_state:
    st.session_state.data_assinatura_cct = pd.to_datetime("2025-09-01").date()

data_assinatura_cct = st.sidebar.date_input(
    "Data de assinatura da CCT",
    value=st.session_state.data_assinatura_cct,
    help="Usada nas regras de elegibilidade dos parágrafos."
)
st.session_state.data_assinatura_cct = data_assinatura_cct

# Elegibilidade base (parâmetros gerais adicionais)
st.sidebar.subheader("Elegibilidade (parâmetros gerais)")
min_tempo_casa_meses = st.sidebar.number_input("Tempo mínimo de casa (meses)", min_value=0, value=0, step=1)
proporcional_por_mes = st.sidebar.checkbox("Pagar proporcional por mês completo (regra genérica)", value=True)

# Tetos & pisos (para outras lógicas opcionais)
st.sidebar.subheader("Tetos & Pisos (geral)")
teto_multiplo_salario = st.sidebar.number_input("Teto (x salário)", min_value=0.0, value=3.0, step=0.1)
piso_valor = st.sidebar.number_input("Piso (valor mínimo)", min_value=0.0, value=0.0, step=100.0)

# Antecipação PLR 2025 (conforme cláusula)
st.sidebar.subheader("Antecipação PLR 2025")
lucro_liquido_1s2025 = st.sidebar.number_input(
    "Lucro líquido 1º semestre/2025 (BRL)",
    min_value=0.0,
    value=0.0,
    step=100000.0,
    help="Valor global do lucro líquido do 1º semestre de 2025."
)
compensar_planos_proprios = st.sidebar.checkbox(
    "Compensar valores já pagos em 2025 (Regra Básica)", value=False
)

st.title("Calculadora de PLR – Antecipação 2025")
st.caption("Inclui regras da cláusula (Regra Básica, Parcela Adicional) e parágrafos 1º a 4º.")

aba_config, aba_metas, aba_import, aba_calc, aba_sim, aba_export = st.tabs([
    "Configuração de Regras", "Metas & Pesos", "Base (Manual/Upload)", "Apuração", "Simulações", "Exportação"
])

# =========================
# 1) Configuração de Regras (genéricas)
# =========================
with aba_config:
    st.subheader("Regras do Programa (genéricas)")
    col1, col2, col3 = st.columns(3)
    with col1:
        regra_proporcional_entrada = st.selectbox("Proporcional p/ admissões?", ["Não", "Sim por dias", "Sim por meses"], index=1)
    with col2:
        regra_proporcional_saida = st.selectbox("Proporcional p/ desligamentos?", ["Não", "Sim por dias", "Sim por meses"], index=1)
    with col3:
        considerar_ferias_licencas = st.selectbox("Afastamentos contam?", ["Ignorar", "Descontar proporcional", "Manter integral"], index=2)

    st.info("Estas opções são auxiliares e não sobrepõem a regra de antecipação explicitada na cláusula.")

# =========================
# 2) Metas & Pesos (mantido para uso futuro)
# =========================
with aba_metas:
    st.subheader("Metas e Pesos (Empresa/Área/Individual – opcional)")
    metas_df = st.data_editor(
        pd.DataFrame({
            "nivel": ["Empresa", "Área", "Individual"],
            "peso": [0.4, 0.4, 0.2],
            "performace_realizada": [1.0, 1.0, 1.0],
        }),
        num_rows="dynamic",
        use_container_width=True,
        key="metas_editor",
        column_config={
            "nivel": st.column_config.SelectboxColumn("Nível", options=["Empresa", "Área", "Individual"]),
            "peso": st.column_config.NumberColumn("Peso", min_value=0.0, max_value=1.0, step=0.05, format="%0.2f"),
            "performace_realizada": st.column_config.NumberColumn("Performance realizada (0–2.0)", min_value=0.0, max_value=2.0, step=0.05, format="%0.2f"),
        }
    )
    if abs(metas_df["peso"].sum() - 1.0) > 1e-6:
        st.warning("A soma dos pesos deve ser 1.0.")

# =========================
# 3) Base (Cadastro manual ou Upload)
# =========================
with aba_import:
    st.subheader("Cadastro da Base: Manual ou Upload")

    required_cols = [
        "Matricula", "Nome", "Cargo", "Salario_Base", "Verbas_Fixas_Salariais",
        "Data_Admissao", "Data_Desligamento", "Diretoria", "Centro_Custo",
        "Valor_Pago_2025", "Motivo_Afastamento", "Conta_Ativa"
    ]

    if "manual_df" not in st.session_state:
        st.session_state.manual_df = pd.DataFrame(columns=required_cols)

    modo = st.radio("Como deseja informar os dados?", ["Cadastro manual", "Upload (CSV/Excel)"])

    if modo == "Cadastro manual":
        with st.form("form_manual"):
            colA, colB, colC = st.columns(3)
            with colA:
                matricula = st.text_input("Matrícula")
                nome = st.text_input("Nome")
                cargo = st.text_input("Cargo")
                diretoria = st.text_input("Diretoria")
            with colB:
                salario = st.number_input("Salário-base (vigente em 01/09/2025)", min_value=0.0, step=100.0)
                verbas = st.number_input("Verbas fixas salariais", min_value=0.0, step=50.0)
                cc = st.text_input("Centro de Custo")
                valor_pago = st.number_input("Valor já pago em 2025 (compensação)", min_value=0.0, step=50.0)
            with colC:
                dt_adm = st.date_input("Data de admissão")
                dt_desl = st.date_input("Data de desligamento (se houver)", value=None)
                motivo = st.selectbox("Motivo de afastamento", ["nenhum", "doença", "acidente", "licença-maternidade"])
                conta_ativa = st.selectbox("Conta corrente ativa no banco?", ["sim", "não"])        
            add = st.form_submit_button("Adicionar à base")

        if add:
            nova = {
                "Matricula": matricula,
                "Nome": nome,
                "Cargo": cargo,
                "Salario_Base": salario,
                "Verbas_Fixas_Salariais": verbas,
                "Data_Admissao": pd.to_datetime(dt_adm),
                "Data_Desligamento": pd.to_datetime(dt_desl) if dt_desl else None,
                "Diretoria": diretoria,
                "Centro_Custo": cc,
                "Valor_Pago_2025": valor_pago,
                "Motivo_Afastamento": motivo,
                "Conta_Ativa": conta_ativa,
            }
            st.session_state.manual_df = pd.concat([st.session_state.manual_df, pd.DataFrame([nova])], ignore_index=True)

        st.markdown("### Base (Cadastro manual)")
        st.session_state.manual_df = st.data_editor(
            st.session_state.manual_df,
            num_rows="dynamic",
            use_container_width=True,
            key="editor_manual"
        )

        # Template CSV
        tmpl = pd.DataFrame(columns=required_cols)
        csv_bytes = tmpl.to_csv(index=False).encode("utf-8")
        st.download_button("Baixar template CSV", data=csv_bytes, file_name="template_plr.csv", mime="text/csv")

        base = st.session_state.manual_df.copy()

    else:
        st.markdown("Faça upload do arquivo com as colunas mínimas exigidas.")

        exemplo = pd.DataFrame({
            "Matricula": [1001, 1002, 1003],
            "Nome": ["Ana", "Bruno", "Carla"],
            "Cargo": ["Analista", "Coordenador", "Gerente"],
            "Salario_Base": [8000.0, 12000.0, 20000.0],
            "Verbas_Fixas_Salariais": [500.0, 1500.0, 2500.0],
            "Data_Admissao": ["2023-02-10", "2024-01-15", "2022-05-01"],
            "Data_Desligamento": [None, None, None],
            "Diretoria": ["Tech", "Ops", "Produtos"],
            "Centro_Custo": ["TI", "Operações", "Prod"],
            "Valor_Pago_2025": [0.0, 0.0, 0.0],
            "Motivo_Afastamento": ["nenhum", "nenhum", "nenhum"],
            "Conta_Ativa": ["sim", "sim", "sim"],
        })

        up = st.file_uploader("CSV ou Excel (UTF-8). Use o template, se possível.", type=["csv", "xlsx"])

        if up is None:
            st.info("Sem arquivo carregado – usando base de exemplo.")
            base = exemplo.copy()
        else:
            if up.name.endswith(".csv"):
                base = pd.read_csv(up)
            else:
                base = pd.read_excel(up)

        for col in required_cols:
            if col not in base.columns:
                base[col] = np.nan

        st.dataframe(base, use_container_width=True)

    # Validação básica
    faltantes = [c for c in ["Matricula","Nome","Salario_Base","Data_Admissao"] if c not in base.columns or base[c].isna().all()]
    if faltantes:
        st.warning(f"Atenção: verifique as colunas obrigatórias/valores: {faltantes}")

# =========================
# 4) Apuração (Regra da Cláusula)
# =========================
with aba_calc:
    st.subheader("Apuração – Antecipação 2025")

    # Índice composto (mantido para uso futuro)
    peso_sum = metas_df["peso"].sum() if len(metas_df) else 0
    indice_plr = float((metas_df["peso"] * metas_df["performace_realizada"]).sum()) if peso_sum > 0 else 0.0
    st.metric("Índice Composto (livre)", f"{indice_plr:0.2f}x")

    # ===== Parâmetros legais =====
    FIXO_BASICA = 2005.82
    LIMITE_BASICA_INDIV = 10760.26
    PCT_LUCRO_BASICA = 0.128  # 12,8%
    PCT_LUCRO_ADIC = 0.022    # 2,2%
    LIMITE_ADIC_INDIV = 3471.13

    # ===== Elegibilidade/Proporcionalidade conforme parágrafos =====
    def calcular_proporcionalidade_especial(row, data_assinatura):
        admissao = pd.to_datetime(row.get("Data_Admissao"))
        desligamento = pd.to_datetime(row.get("Data_Desligamento")) if row.get("Data_Desligamento") not in [None, "", np.nan] else None
        motivo = str(row.get("Motivo_Afastamento", "")).lower().strip()

        def meses_12avos(inicio, fim):
            # conta meses por fração >=15 dias
            if pd.isna(inicio) or pd.isna(fim) or inicio > fim:
                return 0.0
            total = 0
            cur = pd.Timestamp(year=inicio.year, month=inicio.month, day=1)
            end = pd.Timestamp(year=fim.year, month=fim.month, day=1)
            while cur <= end:
                mes_ini = cur
                mes_fim = (cur + pd.offsets.MonthEnd(0))
                seg_ini = max(admissao, mes_ini)
                seg_fim = min(fim, mes_fim)
                dias = (seg_fim - seg_ini).days + 1
                if dias >= 15:
                    total += 1
                cur = cur + pd.offsets.MonthBegin(1)
            return min(12.0, float(total))

        assinatura = pd.to_datetime(data_assinatura)

        # §1º – admitido até 31/12/2023, afastado (doença/acidente/licença-maternidade), no quadro na assinatura
        if (admissao <= pd.Timestamp("2023-12-31")) and (motivo in ["doença", "acidente", "licença-maternidade"]) and (desligamento is None or desligamento > assinatura):
            return 1.0

        # §2º – admitido a partir de 01/01/2024, em efetivo exercício na assinatura (mesmo que afastado)
        if (admissao >= pd.Timestamp("2024-01-01")) and (desligamento is None or desligamento > assinatura):
            meses = meses_12avos(admissao, pd.Timestamp("2024-12-31"))
            return float(meses / 12.0)

        # §3º – dispensado sem justa causa entre 02/08/2024 e a assinatura
        if (desligamento is not None) and (pd.Timestamp("2024-08-02") <= desligamento <= assinatura):
            meses = meses_12avos(admissao, desligamento)
            return float(meses / 12.0)

        # §4º – não elegível
        return 0.0

    base_calc = base.copy()
    base_calc["Proporcionalidade"] = base_calc.apply(lambda r: calcular_proporcionalidade_especial(r, data_assinatura_cct), axis=1)

    elegiveis = base_calc[base_calc["Proporcionalidade"] > 0].copy()
    n_elegiveis = int(elegiveis.shape[0])

    # ===== Regra Básica =====
    elegiveis["Base_PLR_Basica"] = (0.54 * (elegiveis["Salario_Base"].astype(float) + elegiveis["Verbas_Fixas_Salariais"].astype(float)) + FIXO_BASICA)
    # aplica proporcionalidade dos parágrafos
    elegiveis["Base_PLR_Basica"] = elegiveis["Base_PLR_Basica"] * elegiveis["Proporcionalidade"]
    # cap individual
    elegiveis["Basica_Indiv_Cap"] = elegiveis["Base_PLR_Basica"].clip(upper=LIMITE_BASICA_INDIV)

    # cap global 12,8% do lucro
    total_basica_pre_cap = float(elegiveis["Basica_Indiv_Cap"].sum())
    limite_global_basica = PCT_LUCRO_BASICA * float(lucro_liquido_1s2025)
    fator_cap = 1.0
    if limite_global_basica > 0 and total_basica_pre_cap > limite_global_basica:
        fator_cap = limite_global_basica / total_basica_pre_cap
    elegiveis["Basica_Pos_Global"] = elegiveis["Basica_Indiv_Cap"] * fator_cap

    # compensação
    if compensar_planos_proprios:
        pagos = elegiveis["Valor_Pago_2025"].astype(float).fillna(0.0)
        elegiveis["Basica_Final"] = (elegiveis["Basica_Pos_Global"] - pagos).clip(lower=0.0)
    else:
        elegiveis["Basica_Final"] = elegiveis["Basica_Pos_Global"]

    # ===== Parcela Adicional =====
    pool_adic = PCT_LUCRO_ADIC * float(lucro_liquido_1s2025)
    adic_unitario = 0.0
    if n_elegiveis > 0:
        adic_unitario = pool_adic / n_elegiveis
    adic_unitario = min(adic_unitario, LIMITE_ADIC_INDIV)
    elegiveis["Adicional_Final"] = adic_unitario

    # Merge de volta
    base_calc = base_calc.merge(
        elegiveis[["Matricula", "Basica_Final", "Adicional_Final", "Basica_Pos_Global", "Basica_Indiv_Cap", "Base_PLR_Basica", "Proporcionalidade"]],
        on="Matricula",
        how="left"
    )
    for col in ["Basica_Final", "Adicional_Final", "Basica_Pos_Global", "Basica_Indiv_Cap", "Base_PLR_Basica"]:
        base_calc[col] = base_calc[col].fillna(0.0)

    base_calc["PLR_Antecipacao_Total"] = base_calc["Basica_Final"] + base_calc["Adicional_Final"]

    # Métricas
    colm1, colm2, colm3, colm4 = st.columns(4)
    with colm1:
        st.metric("Elegíveis", f"{n_elegiveis}")
    with colm2:
        st.metric("Total Regra Básica (após cap)", f"{base_calc['Basica_Final'].sum():,.2f}")
    with colm3:
        st.metric("Total Parcela Adicional", f"{base_calc['Adicional_Final'].sum():,.2f}")
    with colm4:
        st.metric("Antecipação Total", f"{base_calc['PLR_Antecipacao_Total'].sum():,.2f}")

    st.markdown("### Resultado por Colaborador")
    st.dataframe(
        base_calc[[
            "Matricula", "Nome", "Cargo", "Diretoria", "Centro_Custo",
            "Salario_Base", "Verbas_Fixas_Salariais", "Motivo_Afastamento", "Proporcionalidade",
            "Base_PLR_Basica", "Basica_Indiv_Cap", "Basica_Pos_Global", "Basica_Final",
            "Adicional_Final", "PLR_Antecipacao_Total"
        ]].round(2), use_container_width=True
    )

    st.markdown("### Verificações e Totais")
    st.write(
        {
            "Limite Global Regra Básica (12,8% do lucro)": limite_global_basica,
            "Soma Individuais antes do cap": total_basica_pre_cap,
            "Fator de Redução Aplicado": fator_cap,
            "Pool Parcela Adicional (2,2% do lucro)": pool_adic,
            "Adicional unitário (após limite indiv.)": adic_unitario,
        }
    )

    st.markdown("### Totais por Diretoria")
    if "Diretoria" in base_calc.columns:
        tot_dir = base_calc.groupby("Diretoria", as_index=False)["PLR_Antecipacao_Total"].sum()
        st.dataframe(tot_dir.rename(columns={"PLR_Antecipacao_Total": "Total_Antecipacao"}).round(2), use_container_width=True)

# =========================
# 5) Simulações simples
# =========================
with aba_sim:
    st.subheader("Simulações Rápidas (índice livre/teto geral)")
    colA, colB = st.columns(2)
    with colA:
        sim_indice = st.slider("Simular índice composto (x)", min_value=0.0, max_value=3.0, value=float(indice_plr), step=0.05)
    with colB:
        sim_teto = st.slider("Simular teto (x salário)", min_value=0.0, max_value=6.0, value=float(teto_multiplo_salario), step=0.1)

    sim = base.copy()
    # proporção genérica (não legal) – apenas para brincar com cenários
    def prop_generica(row):
        meses = row.get("Tempo_Casa_Meses", np.nan)
        if pd.isna(meses):
            return 1.0
        if meses < min_tempo_casa_meses:
            return 0.0
        return min(1.0, max(0.0, meses / 12.0)) if proporcional_por_mes else 1.0

    if "Tempo_Casa_Meses" not in sim.columns:
        sim["Tempo_Casa_Meses"] = np.nan

    sim["Proporcionalidade_Generica"] = sim.apply(lambda r: prop_generica(r), axis=1)
    sim["PLR_Sim"] = sim["Salario_Base"].astype(float) * sim_indice * sim["Proporcionalidade_Generica"]
    sim["PLR_Sim"] = sim["PLR_Sim"].clip(lower=piso_valor, upper=sim["Salario_Base"].astype(float) * sim_teto)

    st.dataframe(sim[["Matricula", "Nome", "Salario_Base", "Proporcionalidade_Generica", "PLR_Sim"]].round(2), use_container_width=True)
    st.metric(label="Custo Total Simulado (" + moeda + ")", value=f"{sim['PLR_Sim'].sum():,.2f}")

# =========================
# 6) Exportação
# =========================
with aba_export:
    st.subheader("Exportar Resultado")

    def to_excel_bytes(df_dict):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            for name, df in df_dict.items():
                df.to_excel(writer, index=False, sheet_name=name)
        return output.getvalue()

    if 'base_calc' in locals():
        bytes_file = to_excel_bytes({
            "Resultado_Antecipacao": base_calc.round(2),
            "Totais_Diretoria": base_calc.groupby("Diretoria", as_index=False)["PLR_Antecipacao_Total"].sum() if "Diretoria" in base_calc.columns else pd.DataFrame(),
        })
        st.download_button(
            label="Baixar Excel com Antecipação 2025",
            data=bytes_file,
            file_name=f"PLR_Antecipacao_{ano_ref}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Calcule primeiro para habilitar a exportação.")
