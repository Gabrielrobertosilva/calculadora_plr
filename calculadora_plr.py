# calculadora_plr.py – v5 (regra de antecipação da PLR, com deduplicação e flag de elegibilidade)
# Rodar com: streamlit run calculadora_plr.py

import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

st.set_page_config(page_title="Calculadora de PLR – Antecipação 2025", layout="wide")

# =========================
# Colunas e defaults globais
# =========================
REQUIRED_COLS = [
    "Matricula", "Nome", "Cargo",
    "Salario_Base", "Verbas_Fixas_Salariais",
    "Data_Admissao", "Data_Desligamento",
    "Diretoria", "Centro_Custo",
    "Valor_Pago_2025", "Motivo_Afastamento", "Conta_Ativa"
]

DEFAULTS = {
    "Verbas_Fixas_Salariais": 0.0,
    "Data_Desligamento": None,
    "Diretoria": "",
    "Centro_Custo": "",
    "Valor_Pago_2025": 0.0,
    "Motivo_Afastamento": "nenhum",
    "Conta_Ativa": "sim",
}

# Estado inicial
if "manual_df" not in st.session_state:
    st.session_state.manual_df = pd.DataFrame(columns=REQUIRED_COLS)

if "data_assinatura_cct" not in st.session_state:
    st.session_state.data_assinatura_cct = pd.to_datetime("2025-09-01").date()

# =========================
# Sidebar
# =========================
st.sidebar.title("Parâmetros Globais")
st.sidebar.markdown("Informe datas e valores da cláusula de **antecipação**.")

ano_ref = st.sidebar.selectbox("Ano de referência", options=list(range(2023, 2031)), index=2)
moeda = st.sidebar.selectbox("Moeda", ["BRL", "USD"], index=0)

data_assinatura_cct = st.sidebar.date_input(
    "Data de assinatura da CCT",
    value=st.session_state.data_assinatura_cct,
    help="Usada nas regras de elegibilidade do caput e dos parágrafos."
)
st.session_state.data_assinatura_cct = data_assinatura_cct

st.sidebar.subheader("Antecipação PLR 2025")
lucro_liquido_1s2025 = st.sidebar.number_input(
    "Lucro líquido 1º semestre/2025 (BRL)",
    min_value=0.0, value=0.0, step=100000.0,
    help="Base do teto global (12,8%) e da parcela adicional (2,2%)."
)
compensar_planos_proprios = st.sidebar.checkbox(
    "Compensar valores já pagos em 2025 (Regra Básica)", value=False
)

# =========================
# Título e abas
# =========================
st.title("Calculadora de PLR – Antecipação 2025")
st.caption("Aplica apenas a **regra de antecipação** (caput + §1º–§4º).")

aba_base, aba_calc, aba_export = st.tabs(
    ["Base (Manual/Upload)", "Apuração", "Exportação"]
)

# =========================
# Base (Manual/Upload)
# =========================
with aba_base:
    st.subheader("Cadastro da Base: Manual ou Upload")

    dedup_toggle = st.checkbox("Remover duplicatas por Matrícula (manter a última)", value=True)

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
            substituir = st.checkbox("Substituir se Matrícula já existir", value=True)
            add = st.form_submit_button("Adicionar à base")

        if add:
            if not matricula:
                st.error("Informe a Matrícula antes de adicionar.")
            else:
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
                df = st.session_state.manual_df.copy()
                if substituir and "Matricula" in df.columns:
                    df = df[df["Matricula"] != matricula]
                st.session_state.manual_df = pd.concat([df, pd.DataFrame([nova])], ignore_index=True)

        st.markdown("### Base (Cadastro manual)")
        st.session_state.manual_df = st.data_editor(
            st.session_state.manual_df,
            num_rows="dynamic",
            use_container_width=True,
            key="editor_manual"
        )

        # Template CSV
        tmpl = pd.DataFrame(columns=REQUIRED_COLS)
        csv_bytes = tmpl.to_csv(index=False).encode("utf-8")
        st.download_button("Baixar template CSV", data=csv_bytes, file_name="template_plr.csv", mime="text/csv")

        base = st.session_state.manual_df.copy()

    else:
        st.markdown("Faça upload do arquivo com as colunas mínimas exigidas (use o template, se possível).")
        up = st.file_uploader("CSV ou Excel (UTF-8)", type=["csv", "xlsx"])

        if up is None:
            # Base vazia (não quebra cálculos)
            base = pd.DataFrame(columns=REQUIRED_COLS)
            st.info("Nenhum arquivo carregado. A base está vazia (você pode usar o cadastro manual).")
        else:
            if up.name.endswith(".csv"):
                base = pd.read_csv(up)
            else:
                base = pd.read_excel(up)

        # Normalização e defaults
        base.columns = base.columns.str.strip()
        for col in REQUIRED_COLS:
            if col not in base.columns:
                base[col] = DEFAULTS.get(col, np.nan)

        st.dataframe(base, use_container_width=True)

    # Tipos e limpeza (sempre)
    base.columns = base.columns.str.strip()
    for col in REQUIRED_COLS:
        if col not in base.columns:
            base[col] = DEFAULTS.get(col, np.nan)

    for c in ["Salario_Base", "Verbas_Fixas_Salariais", "Valor_Pago_2025"]:
        base[c] = pd.to_numeric(base[c], errors="coerce").fillna(0.0)

    for c in ["Data_Admissao", "Data_Desligamento"]:
        base[c] = pd.to_datetime(base[c], errors="coerce")

    # Deduplicação por Matrícula (mantém a última)
    if dedup_toggle and "Matricula" in base.columns:
        base = base.drop_duplicates(subset=["Matricula"], keep="last").reset_index(drop=True)

    must_have_values = ["Matricula", "Nome", "Salario_Base", "Data_Admissao"]
    faltantes = [c for c in must_have_values if base[c].isna().all()]
    if faltantes:
        st.warning(f"Estas colunas estão vazias na base: {faltantes}. Preencha/edite antes de apurar.")

# =========================
# Elegibilidade (caput + §1–§4) -> retorna (proporção, motivo)
# =========================
def calcular_proporcionalidade_especial(row, data_assinatura):
    # Parse seguro de datas
    admissao_raw = row.get("Data_Admissao")
    desligamento_raw = row.get("Data_Desligamento")

    admissao = pd.to_datetime(admissao_raw, errors="coerce")
    if pd.isna(admissao):
        return 0.0, "Dados insuficientes"

    # Trata NaT/None/"" como None (ativo)
    if pd.isna(desligamento_raw) or desligamento_raw in (None, "", "nan"):
        desligamento = None
    else:
        desligamento = pd.to_datetime(desligamento_raw, errors="coerce")
        if pd.isna(desligamento):
            desligamento = None

    motivo = str(row.get("Motivo_Afastamento", "")).lower().strip()
    # aceita com ou sem acento
    if motivo == "licenca-maternidade":
        motivo = "licença-maternidade"

    assinatura = pd.to_datetime(data_assinatura)

    def meses_12avos(inicio, fim):
        # Conta 1/12 por mês com fração >= 15 dias
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

    # §1º – admitido até 31/12/2023, afastado, ativo na assinatura → integral
    if (admissao <= pd.Timestamp("2023-12-31")) and (motivo in ["doença", "acidente", "licença-maternidade"]) and (desligamento is None or desligamento > assinatura):
        return 1.0, "§1º"

    # §2º – admitido a partir de 01/01/2024, em efetivo exercício na assinatura (mesmo afastado) → proporcional até 31/12/2024
    if (admissao >= pd.Timestamp("2024-01-01")) and (desligamento is None or desligamento > assinatura):
        meses = meses_12avos(admissao, pd.Timestamp("2024-12-31"))
        return float(meses / 12.0), "§2º"

    # §3º – dispensado sem justa causa entre 02/08/2024 e a assinatura → proporcional até desligamento
    if (desligamento is not None) and (pd.Timestamp("2024-08-02") <= desligamento <= assinatura):
        meses = meses_12avos(admissao, desligamento)
        return float(meses / 12.0), "§3º"

    # CAPUT – empregado ativo na data da assinatura (não desligado até a assinatura) → integral
    if (desligamento is None) or (desligamento > assinatura):
        return 1.0, "Caput"

    # §4º – não elegível
    return 0.0, "§4º – Não elegível"

# =========================
# Apuração
# =========================
with aba_calc:
    st.subheader("Apuração – Antecipação 2025")

    calcular = st.button("Calcular Antecipação", type="primary")

    if not calcular:
        st.info("Preencha o sidebar e a base, depois clique em **Calcular Antecipação**.")
    else:
        if base.empty:
            st.warning("Nenhuma base carregada ou cadastrada. Use a aba 'Base (Manual/Upload)'.")
        else:
            # Parâmetros da cláusula
            FIXO_BASICA = 2005.82
            LIMITE_BASICA_INDIV = 10760.26
            PCT_LUCRO_BASICA = 0.128   # 12,8%
            PCT_LUCRO_ADIC   = 0.022   # 2,2%
            LIMITE_ADIC_INDIV = 3471.13

            base_calc = base.copy()

            # Proporcionalidade (caput + parágrafos)
            props = base_calc.apply(lambda r: calcular_proporcionalidade_especial(r, data_assinatura_cct), axis=1)
            base_calc["Proporcionalidade"] = props.apply(lambda x: x[0])
            base_calc["Motivo_Elegibilidade"] = props.apply(lambda x: x[1])
            base_calc["Elegivel"] = np.where(base_calc["Proporcionalidade"] > 0, "Sim", "Não")

            # Elegíveis
            elegiveis = base_calc[base_calc["Proporcionalidade"] > 0].copy()

            # Deduplicação por Matrícula antes de qualquer soma/merge
            if "Matricula" in elegiveis.columns:
                elegiveis = elegiveis.drop_duplicates(subset=["Matricula"], keep="last")

            n_elegiveis = int(elegiveis.shape[0])

            if n_elegiveis == 0:
                st.warning("Nenhum colaborador elegível pelas regras (caput/§§). Confira datas e motivos de afastamento.")
            else:
                # Regra Básica: 54% * (Salário + Verbas Fixas) + FIXO, vezes proporcionalidade
                elegiveis["Base_PLR_Basica"] = (
                    0.54 * (elegiveis["Salario_Base"].astype(float) + elegiveis["Verbas_Fixas_Salariais"].astype(float))
                    + FIXO_BASICA
                ) * elegiveis["Proporcionalidade"]

                # Cap individual
                elegiveis["Basica_Indiv_Cap"] = elegiveis["Base_PLR_Basica"].clip(upper=LIMITE_BASICA_INDIV)

                # Cap global 12,8% do lucro 1S/2025
                total_basica_pre_cap = float(elegiveis["Basica_Indiv_Cap"].sum())
                limite_global_basica = PCT_LUCRO_BASICA * float(lucro_liquido_1s2025)
                fator_cap = 1.0
                if limite_global_basica == 0:
                    st.warning("O lucro 1S/2025 está 0. O teto global (12,8%) zera a Regra Básica.")
                if limite_global_basica > 0 and total_basica_pre_cap > limite_global_basica:
                    fator_cap = limite_global_basica / total_basica_pre_cap
                elegiveis["Basica_Pos_Global"] = elegiveis["Basica_Indiv_Cap"] * fator_cap

                # Compensação
                if compensar_planos_proprios:
                    pagos = elegiveis["Valor_Pago_2025"].astype(float).fillna(0.0)
                    elegiveis["Basica_Final"] = (elegiveis["Basica_Pos_Global"] - pagos).clip(lower=0.0)
                else:
                    elegiveis["Basica_Final"] = elegiveis["Basica_Pos_Global"]

                # Parcela Adicional
                pool_adic = PCT_LUCRO_ADIC * float(lucro_liquido_1s2025)
                adic_unitario = min((pool_adic / n_elegiveis) if n_elegiveis > 0 else 0.0, LIMITE_ADIC_INDIV)
                if pool_adic == 0:
                    st.warning("O lucro 1S/2025 está 0. A Parcela Adicional (2,2%) será 0.")
                elegiveis["Adicional_Final"] = adic_unitario

                # Merge back (com base sem duplicatas por Matrícula)
                base_calc = base_calc.drop_duplicates(subset=["Matricula"], keep="last")
                base_calc = base_calc.merge(
                    elegiveis[[
                        "Matricula", "Basica_Final", "Adicional_Final",
                        "Basica_Pos_Global", "Basica_Indiv_Cap", "Base_PLR_Basica"
                    ]],
                    on="Matricula", how="left"
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

                # Exibição segura
                desired_cols = [
                    "Matricula", "Nome", "Cargo", "Diretoria", "Centro_Custo",
                    "Salario_Base", "Verbas_Fixas_Salariais",
                    "Elegivel", "Motivo_Elegibilidade", "Proporcionalidade",
                    "Base_PLR_Basica", "Basica_Indiv_Cap", "Basica_Pos_Global", "Basica_Final",
                    "Adicional_Final", "PLR_Antecipacao_Total"
                ]
                display_cols = [c for c in desired_cols if c in base_calc.columns]
                missing_cols = [c for c in desired_cols if c not in base_calc.columns]
                if missing_cols:
                    st.info(f"Colunas ausentes ocultadas: {missing_cols}")

                st.markdown("### Resultado por Colaborador")
                st.dataframe(base_calc[display_cols].round(2), use_container_width=True)

                st.markdown("### Totais por Diretoria")
                if "Diretoria" in base_calc.columns and not base_calc["Diretoria"].isna().all():
                    tot_dir = base_calc.groupby("Diretoria", as_index=False)["PLR_Antecipacao_Total"].sum()
                    st.dataframe(tot_dir.rename(columns={"PLR_Antecipacao_Total": "Total_Antecipacao"}).round(2), use_container_width=True)

                st.markdown("### Verificações e Limites")
                st.write({
                    "Teto Global Regra Básica (12,8% do lucro)": limite_global_basica,
                    "Soma Individuais antes do cap": total_basica_pre_cap,
                    "Fator de Redução Aplicado": fator_cap,
                    "Pool Parcela Adicional (2,2% do lucro)": pool_adic,
                    "Adicional unitário (após limite indiv.)": adic_unitario,
                })

# =========================
# Exportação
# =========================
with aba_export:
    st.subheader("Exportar Resultado")

    def to_excel_bytes(df_dict):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            for name, df in df_dict.items():
                df.to_excel(writer, index=False, sheet_name=name)
        return output.getvalue()

    if "base_calc" in locals() and 'PLR_Antecipacao_Total' in base_calc.columns and not base.empty:
        sheets = {"Resultado_Antecipacao": base_calc.round(2)}
        if "Diretoria" in base_calc.columns and not base_calc["Diretoria"].isna().all():
            sheets["Totais_Diretoria"] = base_calc.groupby("Diretoria", as_index=False)["PLR_Antecipacao_Total"].sum().round(2)
        bytes_file = to_excel_bytes(sheets)
        st.download_button(
            label="Baixar Excel com Antecipação 2025",
            data=bytes_file,
            file_name=f"PLR_Antecipacao_{ano_ref}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Calcule na aba 'Apuração' para habilitar a exportação.")
