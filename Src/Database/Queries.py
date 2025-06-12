from .Connection import db
import streamlit as st


@st.cache_data(show_spinner="Carregando produtos...")
def buscar_produtos(cd_empresa):
    empresas = {
        40: (1, 10),
        50: (52, 0),
        60: (5, 0),
        7: (7, 0)
    }

    _querie = f"""
    SELECT
        I.CD_ITEM, I.DS_ITEM, S.DS_APLICACAO, M.DS_MARCA AS FABRICANTE,
        I.CD_FORNECEDOR1, 0 AS QNT_COMPRAR, I.CD_SECAO,
        SUM(IIF(N.DT_EMISSAO BETWEEN PRIMEIRODIAMES(DATEADD(YEAR, -1, CURRENT_DATE))
            AND ULTIMODIAMES(DATEADD(MONTH, -1, CURRENT_DATE)), COALESCE(IT.PS_ITEMNOTA, IT.QT_ITEMNOTA), 0)) MES_12,
        SUM(IIF(N.DT_EMISSAO BETWEEN PRIMEIRODIAMES(CURRENT_DATE)
            AND CURRENT_DATE, COALESCE(IT.PS_ITEMNOTA, IT.QT_ITEMNOTA), 0)) MES_ATUAL,
        DATEDIFF(DAY, PRIMEIRODIAMES(CURRENT_DATE), CURRENT_DATE) DIAS_ATUAL,
        I.CD_GRUPO AS CD_GRUPO,
        SUBSTRING(I.CD_SUBGRUPO FROM CHAR_LENGTH(I.CD_GRUPO)+1 FOR 3) AS CD_SUBGRUPO,
        SUBSTRING(I.CD_SECAO FROM CHAR_LENGTH(I.CD_SUBGRUPO)+1 FOR 3) AS CD_PECA
    FROM
        NOTA N
        INNER JOIN ITEMNOTA IT ON (IT.CD_EMPRESA = N.CD_EMPRESA
            AND IT.NR_LANCAMENTO = N.NR_LANCAMENTO
            AND IT.TP_NOTA = N.TP_NOTA
            AND IT.CD_SERIE = N.CD_SERIE)
        INNER JOIN ITEM I ON (I.CD_ITEM = IT.CD_ITEM
            AND I.ST_ATIVO = 'S')
        INNER JOIN SECAO S ON (I.CD_SECAO = S.CD_SECAO)
        INNER JOIN MARCA M ON (M.CD_MARCA = I.CD_MARCA)
        INNER JOIN MOVIMENTACAO MO ON (MO.CD_MOVIMENTACAO = IT.CD_MOVIMENTACAO)
    WHERE
        N.ST_NOTA = 'V'
        AND N.TP_NOTA = 'S'
        AND N.CD_EMPRESA IN {empresas[cd_empresa]}
        AND N.DT_EMISSAO BETWEEN PRIMEIRODIAMES(DATEADD(YEAR, -1, CURRENT_DATE)) AND CURRENT_DATE
        AND MO.ST_RECEITA = 'S'
    GROUP BY
        I.CD_ITEM, I.DS_ITEM, S.DS_APLICACAO, FABRICANTE,
        I.CD_FORNECEDOR1, I.CD_SECAO, CD_GRUPO, I.PS_LIQUIDO, CD_SUBGRUPO, CD_PECA

    """
    return db.read_sql(query=_querie)


def buscar_estoque_item(cd_item: int):
    _querie = f"""
    SELECT
        E.QT_ESTOQUE
    FROM ITEMLOCAL IL
    INNER JOIN ESTOQUE E ON (E.CD_EMPRESA = 52
        AND E.CD_TIPOLOCAL = IL.CD_TIPOLOCAL
        AND E.CD_LOCAL = IL.CD_LOCAL
        AND E.CD_ITEM = IL.CD_ITEM)
    WHERE IL.CD_ITEM = {cd_item}
    """
    return db.read_sql(query=_querie)


def buscar_marcas():
    _querie = """
    SELECT
        M.DS_MARCA
    FROM MARCA M
    ORDER BY M.DS_MARCA
    """
    return db.read_sql(query=_querie)

def buscar_ultima_compra(cd_empresa: int, cd_item: int):
    empresas = {
        40: (1, 10),
        50: (52, 0),
        60: (5, 0),
        7: (7, 0)
    }

    _querie = f"""
    SELECT
        FORMATA_DATA(MAX(N.DT_EMISSAO))
    FROM NOTA N
    INNER JOIN ITEMNOTA IT ON (IT.CD_EMPRESA = N.CD_EMPRESA
        AND IT.NR_LANCAMENTO = N.NR_LANCAMENTO
        AND IT.TP_NOTA = N.TP_NOTA
        AND IT.CD_SERIE = N.CD_SERIE)
    WHERE N.ST_NOTA = 'V'
        AND N.TP_NOTA =  'E'
        AND N.DT_EMISSAO BETWEEN DATEADD(YEAR, -2, CURRENT_DATE) AND CURRENT_DATE
        AND N.CD_EMPRESA IN {empresas[cd_empresa]}
        AND IT.CD_ITEM = {cd_item}

    """
    return db.read_sql(query=_querie)

def estoque_filial(cd_item):
    _querie = f"""
    WITH ITEM_PK
    AS (
        SELECT I.CD_SECAO
        FROM ITEM I
        WHERE I.CD_ITEM = {cd_item}
        
        UNION ALL

        SELECT I.CD_SECAO + IIF(CHAR_LENGTH(I.CD_SECAO) = 7, 3000000, 30000000) CD_SECAO
        FROM ITEM I
        WHERE I.CD_ITEM = {cd_item}
    )
    SELECT
        X.CD_ITEM, X.DS_MARCA,
        SUM(IIF(X.CD_EMPRESA = 1, CAST(COALESCE(X.QT_ESTOQUE, 0) AS NUMERIC(10,2)), 0)) QT_EMP1,
        SUM(IIF(X.CD_EMPRESA = 5, CAST(COALESCE(X.QT_ESTOQUE, 0) AS NUMERIC(10,2)), 0)) QT_EMP5,
        SUM(IIF(X.CD_EMPRESA = 7, CAST(COALESCE(X.QT_ESTOQUE, 0) AS NUMERIC(10,2)), 0)) QT_EMP7,
        SUM(IIF(X.CD_EMPRESA = 52,CAST(COALESCE(X.QT_ESTOQUE, 0) AS NUMERIC(10,2)), 0)) QT_EMP52
    FROM (
        SELECT DISTINCT
            CAST(SUBSTRING(I.CD_ITEM FROM CHAR_LENGTH(I.CD_SECAO)+1 FOR 2) AS INTEGER) CD_ITEM, 
            M.DS_MARCA,
            E.CD_EMPRESA, E.QT_ESTOQUE

        FROM 
            ITEM I
            INNER JOIN ITEM_PK IPK ON (IPK.CD_SECAO = I.CD_SECAO)
            INNER JOIN ESTOQUE E ON (E.CD_ITEM = I.CD_ITEM)
            INNER JOIN MARCA M ON (M.CD_MARCA = I.CD_MARCA)
        WHERE
            I.ST_ATIVO = 'S'
            AND E.CD_EMPRESA <> 4
    )X
    GROUP BY 1,2
    """

    return db.read_sql(query=_querie)


def pedidos_aberto(cd_empresa, cd_item):
    _querie = f"""
    SELECT
        P.NR_PEDIDO, FORMATA_DATA(P.DT_PEDIDO) DT_PEDIDO, COALESCE(IP.PS_PEDIDO, IP.QT_PEDIDA) QNTD
    FROM PEDIDO P
    INNER JOIN ITEMPEDIDO IP ON (IP.CD_EMPRESA = P.CD_EMPRESA
        AND IP.NR_PEDIDO = P.NR_PEDIDO
        AND IP.TP_PEDIDO = P.TP_PEDIDO)

    WHERE P.CD_EMPRESA = {cd_empresa}
        AND P.TP_PEDIDO = 'E'
        AND P.DT_PEDIDO BETWEEN DATEADD(YEAR, -1, CURRENT_DATE)
                            AND CURRENT_DATE
        AND P.ST_PEDIDO NOT IN ('A', 'C')
        AND IP.CD_MOVIMENTACAO IN (38,97,71,172,265,178,76,150,72,80,187,217,5,
                                    730,75,732,81,733,173,731,215,734)
        AND IP.CD_ITEM = {cd_item}
    """
    return db.read_sql(query=_querie) 


def exc_integrar_cotacao(cd_comprador, cd_empresa, nr_cotacao, cd_item, qt_item):
    try:
        _querie = F"""EXECUTE PROCEDURE EXTEND_COMPRASBY({cd_comprador}, {cd_empresa}, {nr_cotacao}, {cd_item}, {qt_item})"""
        erro = db.execute_UDI(query=_querie)
        return erro
    except Exception as e:
        return str(e)
    
def integrar_cotacao(cd_comprador, cd_empresa, nr_cotacao):
    _querie = f"""
    SELECT
        CP.ID
    FROM COTACAOPECA CP
    INNER JOIN PESSOA P ON (P.CD_PESSOA = CP.IDCOMPRADOR)
    WHERE CP.IDEMPRESA = {cd_empresa}
        AND CP.ID = {nr_cotacao}
        AND CP.IDCOMPRADOR = {cd_comprador}
        AND CP.STCOTACAO = 'A'
    """
    return db.read_sql(query=_querie)

@st.cache_data(show_spinner="Carregando Lead Time")
def buscar_leadtime():
    _querie = f"""
    SELECT
        IP.CD_ITEM, ABS(AVG(DATEDIFF(DAY,P.DT_PEDIDO, N.DT_EMISSAO))) LEAD_TIME
    FROM
        PEDIDO P
        INNER JOIN ITEMPEDIDO IP ON (IP.CD_EMPRESA = P.CD_EMPRESA
            AND IP.NR_PEDIDO = P.NR_PEDIDO
            AND IP.TP_PEDIDO = P.TP_PEDIDO
            AND IP.DT_REGISTRO BETWEEN DATEADD(MONTH, -6, CURRENT_DATE) AND CURRENT_DATE)
        INNER JOIN PEDIDONOTA PN ON (PN.CD_EMPRPED = IP.CD_EMPRESA
            AND PN.NR_PEDIDO = IP.NR_PEDIDO
            AND PN.TP_PEDIDO = IP.TP_PEDIDO
            AND PN.CD_ITEM = IP.CD_ITEM)
        INNER JOIN ITEMNOTA IT ON (IT.CD_EMPRESA = PN.CD_EMPRESA
            AND IT.NR_LANCAMENTO = PN.NR_LANCAMENTO
            AND IT.TP_NOTA = PN.TP_NOTA
            AND IT.CD_SERIE = PN.CD_SERIE
            AND IT.CD_ITEM = PN.CD_ITEM)
        INNER JOIN NOTA N ON (N.CD_EMPRESA = IT.CD_EMPRESA
            AND N.NR_LANCAMENTO = IT.NR_LANCAMENTO
            AND N.CD_SERIE = IT.CD_SERIE
            AND N.TP_NOTA = IT.TP_NOTA
            AND N.ST_NOTA = 'V')
    WHERE P.TP_PEDIDO = 'E'
        AND P.DT_PEDIDO BETWEEN DATEADD(MONTH, -6, CURRENT_DATE) AND CURRENT_DATE
        AND P.ST_PEDIDO IN ('A', 'P')
        AND IP.ST_ITEMPEDIDO IN ('A', 'P')
        AND DATEDIFF(DAY,P.DT_PEDIDO, N.DT_EMISSAO) <> 0
    GROUP BY 1
    """
    return db.read_sql(query=_querie)

@st.cache_data(show_spinner="Carregando Desvio Padrão...")
def buscar_desvio_padrao():
    empresas = {
        40: (1, 10),
        50: (52, 0),
        60: (5, 0),
        7: (7, 0)
    }
    
    _querie = f"""
    WITH TAB_1
    AS (
        SELECT
            X.DT_EMISSAO, X.CD_ITEM,
            POWER((MES_12 - SUM(MES_12) OVER (PARTITION BY X.CD_ITEM) / 12), 2) VARIACAO
        FROM (
            SELECT
                FORMATA_DATA(N.DT_EMISSAO, '%M/%Y') DT_EMISSAO, I.CD_ITEM, SUM(COALESCE(IT.PS_ITEMNOTA, IT.QT_ITEMNOTA)) MES_12
            FROM
                NOTA N
                INNER JOIN ITEMNOTA IT ON (IT.CD_EMPRESA = N.CD_EMPRESA
                    AND IT.NR_LANCAMENTO = N.NR_LANCAMENTO
                    AND IT.TP_NOTA = N.TP_NOTA
                    AND IT.CD_SERIE = N.CD_SERIE)
                INNER JOIN ITEM I ON (I.CD_ITEM = IT.CD_ITEM
                    AND I.ST_ATIVO = 'S')
                INNER JOIN SECAO S ON (I.CD_SECAO = S.CD_SECAO)
                INNER JOIN MOVIMENTACAO MO ON (MO.CD_MOVIMENTACAO = IT.CD_MOVIMENTACAO)
            WHERE
                N.ST_NOTA = 'V'
                AND N.TP_NOTA = 'S'
                AND N.CD_EMPRESA IN (52, 0)
                AND N.DT_EMISSAO BETWEEN PRIMEIRODIAMES(DATEADD(YEAR, -1, CURRENT_DATE)) AND CURRENT_DATE
                AND MO.ST_RECEITA = 'S'
            GROUP BY 1,2
        )X
    )
    SELECT
        T.CD_ITEM, POWER(SUM(VARIACAO), 0.5) / 11 DESVIO_PADRAO
    FROM TAB_1 T
    GROUP BY 1
    """
    return db.read_sql(query=_querie)