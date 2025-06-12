from .Connection import db
import streamlit as st

@st.cache_data(show_spinner="Carregando dados para cache")
def fetch_purchase_orders(cd_empresa):
    empresas = {
        40: (1,10),
        50: (52,0),
        60: (5,0),
        7: (7,0)
    }

    query = f"""
    WITH MEDIA_VENDA AS (
        SELECT
            I.CD_ITEM, I.DS_ITEM, S.DS_APLICACAO, M.DS_MARCA AS FABRICANTE,
            I.CD_FORNECEDOR1, 0 AS QNT_COMPRAR, I.CD_SECAO, I.PS_LIQUIDO,
            COALESCE(SUM(CAST(COALESCE(IT.PS_ITEMNOTA, IT.QT_ITEMNOTA) AS DOM_NUMERIC15_3)) / 13, 0) AS MV_12M, 
            I.CD_GRUPO AS CD_GRUPO,
            SUBSTRING(I.CD_SUBGRUPO FROM CHAR_LENGTH(I.CD_GRUPO)+1 FOR 3) AS CD_SUBGRUPO,
            SUBSTRING(I.CD_SECAO FROM CHAR_LENGTH(I.CD_SUBGRUPO)+1 FOR 3) AS CD_PECA
        FROM
            NOTA N
            INNER JOIN ITEMNOTA IT ON (IT.CD_EMPRESA = N.CD_EMPRESA
                AND IT.NR_LANCAMENTO = N.NR_LANCAMENTO
                AND IT.TP_NOTA = N.TP_NOTA
                AND IT.CD_SERIE = N.CD_SERIE)
            INNER JOIN ITEM I ON (I.CD_ITEM = IT.CD_ITEM AND I.ST_ATIVO = 'S')
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
    ),
    ULTIMA_COMPRA
    AS (
        SELECT
           IT.CD_ITEM, MAX(N.DT_EMISSAO) ULTIMACOMPRA
        FROM NOTA N
        INNER JOIN ITEMNOTA IT ON (IT.CD_EMPRESA = N.CD_EMPRESA
               AND IT.NR_LANCAMENTO = N.NR_LANCAMENTO
               AND IT.TP_NOTA = N.TP_NOTA
               AND IT.CD_SERIE = N.CD_SERIE)
        WHERE N.ST_NOTA = 'V'
          AND N.TP_NOTA = 'E'
          AND N.DT_EMISSAO BETWEEN DATEADD(YEAR, -3, CURRENT_DATE) AND CURRENT_DATE
          AND N.CD_EMPRESA IN {empresas[cd_empresa]}
          AND IT.CD_MOVIMENTACAO IN (38,97,71,172,265,178,76,150,72,80,187,217,5,
                                     730,75,732,81,733,173,731,215,734)
        GROUP BY 1
    ),
    MOV_PEDIDO_COMPRA AS (
        SELECT DISTINCT
            IP.CD_ITEM
        FROM PEDIDO P
        INNER JOIN ITEMPEDIDO IP ON (IP.CD_EMPRESA = P.CD_EMPRESA
            AND IP.NR_PEDIDO = P.NR_PEDIDO
            AND IP.TP_PEDIDO = P.TP_PEDIDO)
        WHERE /*P.CD_EMPRESA= {cd_empresa}
            AND */P.TP_PEDIDO = 'E'
            AND (IP.QT_PEDIDA <> IP.QT_ATENDIDA OR IP.PS_PEDIDO <> IP.PS_ATENDIDO)
            AND P.ST_PEDIDO NOT IN ('A', 'C')
            AND P.DT_PEDIDO BETWEEN DATEADD(YEAR, -1, CURRENT_DATE)
                                AND CURRENT_DATE
            AND IP.CD_MOVIMENTACAO IN (38,97,71,172,265,178,76,150,72,80,187,217,5,
                                             730,75,732,81,733,173,731,215,734)
    ),
    AUXILIAR AS (
        SELECT
            ME.CD_ITEM, ME.DS_ITEM, ME.DS_APLICACAO, ME.FABRICANTE,
            ME.CD_FORNECEDOR1, MV_12M, ME.CD_SECAO, UC.ULTIMACOMPRA,
            SUM(IIF(E.CD_EMPRESA IN {empresas[cd_empresa]}, E.QT_ESTOQUE, 0)) AS QT_ESTOQUE,
            --SUM(IIF(E.CD_EMPRESA <> {cd_empresa}, E.QT_ESTOQUE, 0)) AS QT_OUTRS_LOJAS,
            (SUM(IIF(E.CD_EMPRESA IN {empresas[cd_empresa]}, E.QT_ESTOQUE, 0)) / NULLIF(MV_12M, 0)) AS TEMPO_MEDIO,
            ME.CD_GRUPO, ME.CD_SUBGRUPO, ME.CD_PECA, ME.PS_LIQUIDO,
            CASE
                WHEN LPC.CD_ITEM IS NOT NULL THEN 'VERDE'
                ELSE 'NENHUM'
            END MOV_PRODUTO
        FROM MEDIA_VENDA ME
        INNER JOIN ULTIMA_COMPRA UC ON (UC.CD_ITEM = ME.CD_ITEM)
        LEFT JOIN MOV_PEDIDO_COMPRA LPC ON (LPC.CD_ITEM = ME.CD_ITEM)
        INNER JOIN ESTOQUE E ON (E.cd_item = ME.CD_ITEM)
        GROUP BY ME.CD_ITEM, ME.DS_ITEM, ME.DS_APLICACAO, ME.FABRICANTE, ME.PS_LIQUIDO, UC.ULTIMACOMPRA,
            ME.CD_FORNECEDOR1, MV_12M, ME.CD_SECAO, ME.CD_GRUPO, ME.CD_SUBGRUPO, ME.CD_PECA, MOV_PRODUTO
    )
    SELECT 
        A.CD_ITEM, A.DS_ITEM, A.DS_APLICACAO, A.FABRICANTE, A.QT_ESTOQUE,
        A.CD_FORNECEDOR1, 0 QNT_COMPRAR, CAST(A.MV_12M AS dom_numeric15_2) AS MV_12M,
        COALESCE(FLOOR(A.TEMPO_MEDIO) || ' Mes(es) E ' ||
            CAST(CASE
                WHEN (A.TEMPO_MEDIO - FLOOR(A.TEMPO_MEDIO)) * 30 >= 0 
                THEN ROUND((A.TEMPO_MEDIO - FLOOR(A.TEMPO_MEDIO)) * 30, 0)
                ELSE 0
            END AS INTEGER) || ' Dias', 'SEM DADOS') AS TEMPO, 
        A.CD_SECAO, A.CD_GRUPO, A.CD_SUBGRUPO, A.CD_PECA, FLOOR(A.TEMPO_MEDIO) * 30 TEMPO_MEDIO,
        FLOOR(A.TEMPO_MEDIO) MES, COALESCE(A.PS_LIQUIDO, 0) QT_CONVERSAO, FORMATA_DATA(A.ULTIMACOMPRA, '%D/%M/%Y') ULTIMACOMPRA,
        A.MOV_PRODUTO
    FROM AUXILIAR A

    """
    return db.read_sql(query=query)


def get_brands_filter():
    """Obtém a lista de marcas com base na duração especificada."""
    _querie = """
    SELECT
        M.DS_MARCA
    FROM MARCA M
    """
    df = db.read_sql(query=_querie)
    return df["DS_MARCA"].unique().tolist()

def buscar_estoque_filiais(cd_item, cd_empresa):
    _querie = f"""
    SELECT
        X.CD_EMPRESA, X.DS_LOCAL, X.QT_ESTOQUE
    FROM (
        SELECT
            E.CD_EMPRESA, LE.DS_LOCAL, CAST(R.O_QT_SALDO AS NUMERIC(10,2)) QT_ESTOQUE
        FROM ESTOQUE E
        LEFT JOIN RETORNA_ESTOQUECOMPROMETIDO(E.CD_EMPRESA, E.CD_ITEM, NULL, NULL, CURRENT_DATE) R ON (1=1)
        INNER JOIN ITEMLOCAL IL ON (IL.CD_ITEM = E.CD_ITEM
            AND IL.CD_TIPOLOCAL = E.CD_TIPOLOCAL
            AND IL.CD_LOCAL = E.CD_LOCAL)
        INNER JOIN LOCALESTOQUE LE ON (LE.CD_TIPOLOCAL = IL.CD_TIPOLOCAL
            AND LE.CD_LOCAL = IL.CD_LOCAL)
        WHERE (E.CD_ITEM = {cd_item} OR E.CD_ITEM = ({cd_item} + 30000000))
            AND E.CD_EMPRESA <> 4
        
        UNION ALL
        
        SELECT
            0 CD_EMPRESA, '-- TOTAL -- ' DS_LOCAL, SUM(CAST(R.O_QT_SALDO AS NUMERIC(10,2))) QT_ESTOQUE
        FROM ESTOQUE E
        LEFT JOIN RETORNA_ESTOQUECOMPROMETIDO(E.CD_EMPRESA, E.CD_ITEM, NULL, NULL, CURRENT_DATE) R ON (1=1)
        WHERE (E.CD_ITEM = {cd_item} OR E.CD_ITEM = ({cd_item} + 30000000))
            AND E.CD_EMPRESA <> 4
        GROUP BY 1
    ) X
    ORDER BY IIF(X.CD_EMPRESA = 0, 9999, X.CD_EMPRESA)
        
    """

    return db.read_sql(query=_querie)

@st.cache_data(show_spinner="Carregando dados para cache")
def buscar_similar_estoque(cd_item):
    _querie = f"""
    WITH ITEM_PK
    AS (
        SELECT I.CD_SECAO
        FROM ITEM I
        WHERE I.CD_ITEM = 45360091
        
        UNION ALL

        SELECT I.CD_SECAO + IIF(CHAR_LENGTH(I.CD_SECAO) = 7, 3000000, 30000000) CD_SECAO
        FROM ITEM I
        WHERE I.CD_ITEM = 45360091
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
            (I.CD_ITEM <> 45360091)
            AND I.ST_ATIVO = 'S'
            AND E.CD_EMPRESA <> 4
    )X
    GROUP BY 1,2

    """
    return db.read_sql(query=_querie)

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

def exc_integrar_cotacao(cd_comprador, cd_empresa, nr_cotacao, cd_item, qt_item, tp_operacao):
    try:
        _querie = F"""EXECUTE PROCEDURE EXTEND_COMPRASBY({cd_comprador}, {cd_empresa}, {nr_cotacao}, {cd_item}, {qt_item}, '{tp_operacao}')"""
        erro = db.execute_UDI(query=_querie)
        return erro
    except Exception as e:
        return str(e)

def retorna_mov_mensal(cd_empresa, cd_item):
    empresas = {
        40: (1,10),
        50: (52,0),
        60: (5,0),
        7: (7,0)
    }

    _querie = f"""
    SELECT
        FORMATA_DATA(N.DT_EMISSAO, '01/%M/%Y') DATA_EMISSAO,
        SUM(CAST(COALESCE(IT.PS_ITEMNOTA, IT.QT_ITEMNOTA) AS DOM_NUMERIC15_2)) QUANTIDADE_VENDA

    FROM NOTA N
    INNER JOIN ITEMNOTA IT ON (IT.CD_EMPRESA = N.CD_EMPRESA AND
        IT.NR_LANCAMENTO = N.NR_LANCAMENTO AND
        IT.TP_NOTA = N.TP_NOTA AND
        IT.CD_SERIE = N.CD_SERIE)
    INNER JOIN ITEM I ON (I.CD_ITEM = IT.CD_ITEM AND
        I.ST_ATIVO = 'S')
    INNER JOIN SECAO S ON (I.CD_SECAO = S.CD_SECAO)
    INNER JOIN MARCA M ON (M.CD_MARCA = I.CD_MARCA)
    INNER JOIN MOVIMENTACAO MO ON (MO.CD_MOVIMENTACAO = IT.CD_MOVIMENTACAO)
    WHERE N.ST_NOTA = 'V' AND
        N.TP_NOTA = 'S' AND
        N.CD_EMPRESA IN {empresas[cd_empresa]} AND
        I.CD_ITEM = {cd_item} AND
        N.DT_EMISSAO BETWEEN PRIMEIRODIAMES(DATEADD(YEAR, -1, CURRENT_DATE)) AND CURRENT_DATE AND
        MO.ST_RECEITA = 'S'
    GROUP BY DATA_EMISSAO, EXTRACT(MONTH FROM N.DT_EMISSAO), EXTRACT(YEAR FROM N.DT_EMISSAO)
    ORDER BY EXTRACT(YEAR FROM N.DT_EMISSAO), EXTRACT(MONTH FROM N.DT_EMISSAO)

    """
    return db.read_sql(query=_querie)

def pedidos_aberto(cd_empresa, cd_item):
    _querie = f"""
    SELECT
        P.NR_PEDIDO, P.DT_PEDIDO, COALESCE(IP.PS_PEDIDO, IP.QT_PEDIDA) QNTD
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

