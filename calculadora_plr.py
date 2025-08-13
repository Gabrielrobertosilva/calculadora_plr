def calcular_proporcionalidade_especial(row, data_assinatura):
    # Parse seguro de datas (NaT -> None)
    admissao_raw = row.get("Data_Admissao")
    desligamento_raw = row.get("Data_Desligamento")

    admissao = pd.to_datetime(admissao_raw, errors="coerce")
    if pd.isna(admissao):
        return 0.0  # sem admissão não dá pra calcular

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
    if (admissao <= pd.Timestamp("2023-12-31")) and (motivo in ["doença","acidente","licença-maternidade"]) and (desligamento is None or desligamento > assinatura):
        return 1.0

    # §2º – admitido a partir de 01/01/2024, em efetivo exercício na assinatura (mesmo afastado) → proporcional até 31/12/2024
    if (admissao >= pd.Timestamp("2024-01-01")) and (desligamento is None or desligamento > assinatura):
        meses = meses_12avos(admissao, pd.Timestamp("2024-12-31"))
        return float(meses / 12.0)

    # §3º – dispensado sem justa causa entre 02/08/2024 e a assinatura → proporcional até desligamento
    if (desligamento is not None) and (pd.Timestamp("2024-08-02") <= desligamento <= assinatura):
        meses = meses_12avos(admissao, desligamento)
        return float(meses / 12.0)

    # CAPUT – empregado ativo na data da assinatura (não desligado até a assinatura) → integral
    if (desligamento is None) or (desligamento > assinatura):
        return 1.0

    # §4º – não elegível
    return 0.0
