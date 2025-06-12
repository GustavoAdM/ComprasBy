import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
from Src.Database.Queries import *
from math import ceil
from pandas import DataFrame, isna


def build_sidebar_filters():
    """Constrói os filtros na barra lateral e retorna os valores"""
    with st.sidebar:
        empresa = st.sidebar.selectbox(
            "Empresa", [7, 40, 50, 60], key="EMPRESACOMPRA")

    # Filtros numéricos

        g_col, s_col, i_col = st.columns(3)
        with g_col:
            group = st.number_input(
                "Grupo", value=None, min_value=1, max_value=99, key="GRUPO")
        with s_col:
            sub_group = st.number_input(
                "Sub", value=None, min_value=1, max_value=99, key="SUB")
        with i_col:
            piece = st.number_input(
                "Seção", value=None, min_value=1, max_value=999, key="SECAO")

        # Filtros de texto
        tipo_filtro = st.sidebar.toggle("[Começa com]", key="TIPO_FILTRO")
        desc_peca = st.sidebar.text_input(
            f'{"[Começa com]" if tipo_filtro else "[Contém na]"} - Desc. Peça',
            key="DESC_PECA"
        )
        application = st.sidebar.text_input(
            f'{"[Começa com]" if tipo_filtro else "[Contém na]"} - Aplicação',
            key="APPLICATION"
        )
        peca_fornecedor = st.sidebar.text_input(
            f'{"[Começa com]" if tipo_filtro else "[Contém na]"} - Código Peça Fabricante',
            key="PECA_FORNECEDOR"
        )

        # Filtros avançados
        brand_filter = st.sidebar.multiselect(
            "Selecione a(s) Marcas",
            options=buscar_marcas(),
            key="BRAND_FILTER"
        )

        arredondar_valor = st.sidebar.checkbox(
            "Arredondar valor", value=True, key="ARREDONDAR_VALOR")

        col_lead, col_stock = st.columns(2)
        with col_lead:
            lead_time = st.number_input(
                "LeadTime", value=1, min_value=1, key="LEADTIME")
        with col_stock:
            stock_duration = st.number_input(
                "Ciclo do Estoque",
                value=1,
                min_value=1,
                help="Determine o tempo ideal que os produtos devem permanecer em estoque (DIAS)",
                key="STOCKDURATION"
            )

        col_es, col_qtpers = st.columns(2)
        with col_es:
            fator_seguranca = st.number_input(
                "Fator Segurança",
                value=1.65,
                min_value=0.00,
                key="ESTOQUESEGURANCA"
            )

    return {
        "empresa": empresa,
        "group": group,
        "sub_group": sub_group,
        "piece": piece,
        "tipo_filtro": tipo_filtro,
        "desc_peca": desc_peca,
        "application": application,
        "peca_fornecedor": peca_fornecedor,
        "brand_filter": brand_filter,
        "arredondar_valor": arredondar_valor,
        "lead_time": lead_time,
        "stock_duration": stock_duration,
        "fator_seguranca": fator_seguranca
    }


def fetch_data(empresa, **filtros):

    filtros = filtros["filtros"]
    """Busca e prepara os dados do banco"""
    df_item = buscar_produtos(cd_empresa=empresa)
    df_lead_time = buscar_leadtime()

    df = df_item.merge(df_lead_time, on='CD_ITEM', how='left')
    df['LEAD_TIME'] = df['LEAD_TIME'].fillna(1)


    if "itens" in st.session_state:
        # Atualiza QNT_COMPRAR com base no estado da sessão
        for item in st.session_state.itens:
            cod = item['cod']
            df['QNT_COMPRAR'] = df['QNT_COMPRAR'].astype(float)
            # Pega a quantidade a comprar ou 0 se não existir
            quantity = item.get("comprar", 0.00)
            if st.session_state.get("ARREDONDAR_VALOR"):
                df.loc[df['CD_ITEM'] == cod,
                       'QNT_COMPRAR'] = ceil(quantity)
            else:
                df.loc[df['CD_ITEM'] == cod,
                       'QNT_COMPRAR'] = round(quantity, 2)

    # Aplicar filtros
    if filtros.get("group"):
        df = df[df["CD_GRUPO"] == filtros.get("group")]
    if filtros.get("sub_group"):
        df = df[df["CD_SUBGRUPO"] == str(filtros.get("sub_group")).zfill(2)]
    if filtros.get("piece"):
        df = df[df["CD_PECA"] == str(filtros.get("piece")).zfill(3)]
    if filtros.get("brand_filter"):
        df = df[df["FABRICANTE"].isin(filtros.get("brand_filter"))]
    if filtros.get("application"):
        df['DS_APLICACAO'] = df['DS_APLICACAO'].fillna('')
        if filtros.get("tipo_filtro"):
            df = df[df["DS_APLICACAO"].str.startswith(
                str(filtros.get("application")).upper())]
        else:
            df = df[df["DS_APLICACAO"].str.contains(
                filtros.get("application"), case=False)]
    if filtros.get("peca_fornecedor"):
        df['CD_FORNECEDOR1'] = df['CD_FORNECEDOR1'].fillna('')
        if filtros.get("tipo_filtro"):
            df = df[df["CD_FORNECEDOR1"].str.startswith(
                str(filtros.get("peca_fornecedor")).upper())]
        else:
            df = df[df["CD_FORNECEDOR1"].str.contains(
                filtros.get("peca_fornecedor"), case=False)]
    if filtros.get("desc_peca"):
        df['DS_ITEM'] = df['DS_ITEM'].fillna('')
        if filtros.get("tipo_filtro"):
            df = df[df["DS_ITEM"].str.startswith(
                str(filtros.get("desc_peca")).upper())]
        else:
            df = df[df["DS_ITEM"].str.contains(
                filtros.get("desc_peca"), case=False)]

    return df


def configure_grid(df):
    """Configura e exibe a AgGrid com as colunas personalizadas"""
    gb = GridOptionsBuilder.from_dataframe(df)

    # Mapeamento de colunas e configurações
    columns_config = {
        "CD_ITEM": {"header_name": "Código", "maxWidth": 100, "minWidth": 100},
        "DS_ITEM": {"header_name": "Descrição Peça", "maxWidth": 275, "minWidth": 275},
        "FABRICANTE": {"header_name": "Fabricante", "maxWidth": 200, "minWidth": 200},
        "CD_FORNECEDOR1": {"header_name": "Número", "maxWidth": 160, "minWidth": 160},
        "QNT_COMPRAR": {"header_name": "Qtde", "maxWidth": 100, "minWidth": 100}
    }

    for col, config in columns_config.items():
        gb.configure_column(col, **config)

    gb.configure_selection(selection_mode="single", use_checkbox=True)
    grid_options = gb.build()

    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.GRID_CHANGED,
        data_return_mode=DataReturnMode.AS_INPUT,
        allow_unsafe_jscode=True,
        height=800,
        fit_columns_on_grid_load=True,
        key="aggrid_compras",
        reload_data=True
    )

    return grid_response


def add_to_cache(cod, leadtime, duration, purchase):
    """Adiciona ou atualiza um item no cache da sessão."""
    if 'itens' not in st.session_state:
        st.session_state.itens = []

    # Verifica se o item já existe e atualiza
    for item in st.session_state.itens:
        if item['cod'] == cod:
            item.update(
                {'leadtime': leadtime, 'duracao': duration, 'comprar': purchase})
            return

    # Adiciona um novo item se não existir
    new_item = {'cod': cod, 'leadtime': leadtime,
                'duracao': duration, 'comprar': purchase}
    st.session_state.itens.append(new_item)


def produto_info(df: DataFrame, item_selecionado, cd_empresa):
    if not isinstance(item_selecionado, DataFrame):
        return
    cod_item = item_selecionado["CD_ITEM"].values[0]
    df = df[df["CD_ITEM"] == cod_item]
    if not df.empty:
        col1_1, col1_2, col1_3 = st.columns(3)
        with col1_1:
            df_session = st.session_state.df_table

            if 'itens' not in st.session_state:
                st.session_state.itens = []

            # Garante que o item existe no df_session
            if cod_item in df_session["CD_ITEM"].values:
                linha = df_session[df_session["CD_ITEM"] == cod_item].iloc[0]
                novo_valor = st.number_input(
                    "Alterar Qnt", value=int(linha["QNT_COMPRAR"]))

                # Atualiza diretamente no df original com a condição
                st.session_state.df_table.loc[
                    st.session_state.df_table["CD_ITEM"] == cod_item, "QNT_COMPRAR"
                ] = novo_valor

                atualiza = False

                for item in st.session_state.itens:
                    if item['cod'] == cod_item:
                        if novo_valor != item["comprar"]:
                            atualiza = True

                        item.update(
                            {'leadtime': item["leadtime"], 'duracao': item["duracao"], 'comprar': novo_valor})

                if atualiza:
                    st.rerun()

        with col1_2:
            ultima_compra = buscar_ultima_compra(
                cd_empresa=cd_empresa, cd_item=cod_item).values[0]
            ultima_comp = ultima_compra[0]
            if not ultima_comp:
                ultima_comp = "-"

            st.metric(label="Ultima Compra", value=ultima_comp, border=True)
        with col1_3:
            mv_12 = df[["MES_12"]].values[0]

            if mv_12 != 0:
                mv_12 = mv_12 / 12
            st.metric(label="M.V", value=f"{mv_12[0]:.2f}", border=True)

        df_estoque_filial = estoque_filial(cd_item=cod_item)
        st.dataframe(df_estoque_filial, hide_index=True, height=230,
                    column_config={
                        "CD_ITEM": st.column_config.NumberColumn("Similar"),
                        "DS_MARCA": st.column_config.TextColumn("Marca", width=60),
                        "QT_EMP1": st.column_config.NumberColumn("Emp 1", width=35),
                        "QT_EMP5": st.column_config.NumberColumn("Emp 5", width=35),
                        "QT_EMP7": st.column_config.NumberColumn("Emp 7", width=35),
                        "QT_EMP52": st.column_config.NumberColumn("Emp 52", width=35)
                    })

        df_pedidos = pedidos_aberto(cd_empresa=cd_empresa, cd_item=cod_item)
        st.dataframe(df_pedidos, hide_index=True, height=150,
                    column_config={
                        "NR_PEDIDO": st.column_config.NumberColumn("Nr Pedido"),
                        "DT_PEDIDO": st.column_config.TextColumn("Data Pedido"),
                        "QNTD": st.column_config.NumberColumn("Quant."),
                    })

        st.text_area("Aplicação", value=df["DS_APLICACAO"].values[0], height=250,
                    disabled=True)


@st.fragment()
@st.dialog(title="Integração")
def integracao_cotacao(df: DataFrame):
    col1, col2, col3 = st.columns(3)
    with col1:
        comprador = st.number_input(
            "Cod Comprador", min_value=0, key="COD_COMPRADOR")
    with col2:
        cotacao = st.number_input("Nr Cotação", min_value=0, key="NR_COTACAO")
    with col3:
        empresa = st.number_input(
            "Cod Empresa", min_value=0, value=st.session_state.EMPRESACOMPRA)

    if st.button("Verificar Cotação", use_container_width=True, key="VERIFICA_COTACAO"):
        df_integracao = integrar_cotacao(
            cd_comprador=comprador, nr_cotacao=cotacao, cd_empresa=empresa)
        if df_integracao.empty:
            st.error("Cotação não localizada, verifique")
        else:
            st.success("Cotação localizada.")

    if st.button("Iniciar integração", use_container_width=True, key="INTEGRACAO", disabled=st.session_state.STATUS_INTEGRADO):
        df = df[df['QNT_COMPRAR'].round(0) > 0]
        status = False
        mensagem = ""
        for linha_produto in df.itertuples(index=True, name='Pandas'):
            mensagem = exc_integrar_cotacao(cd_comprador=comprador, nr_cotacao=cotacao, cd_empresa=empresa,
                                            cd_item=linha_produto.CD_ITEM, qt_item=linha_produto.QNT_COMPRAR, tp_operacao="I")
        if mensagem:
            st.error(mensagem)
            st.stop()
        else:
            if st.session_state.get("itens"):
                del st.session_state["itens"]
            st.session_state.STATUS_INTEGRADO = True
            st.rerun(scope="fragment")
    if st.session_state.STATUS_INTEGRADO:
        st.success("Integração realizada com sucesso")


def compras_view():
    """View principal para a funcionalidade de compras"""
    filters = build_sidebar_filters()

    col1, col2 = st.columns([2, 1], border=True)

    with col1:
        df_data = fetch_data(filters["empresa"], filtros=filters)

        colunas_exibir = ["CD_ITEM", "DS_ITEM",
                          "FABRICANTE", "CD_FORNECEDOR1", "QNT_COMPRAR"]
        # Criamos uma cópia para trabalhar
        df_table = df_data[colunas_exibir]

        if "df_table" not in st.session_state:
            st.session_state.df_table = df_table
        st.session_state.df_table = df_table

        # Configuração do grid
        grid_response = configure_grid(st.session_state.df_table)

        selected = grid_response.get('selected_rows')
    with col2:
        produto_info(df=df_data, item_selecionado=selected,
                     cd_empresa=filters["empresa"])

    ##### Botão de calcular #####
    with st.sidebar:
        if st.button(label="Calcular", use_container_width=True):

            # Inicializa a lista de itens na session_state se não existir
            if 'itens' not in st.session_state:
                st.session_state.itens = []

            # Limpa os cálculos anteriores se necessário
            st.session_state.itens = []

            # Itera sobre cada linha do DataFrame principal
            for row in df_data.itertuples():
                df_estoque = buscar_estoque_item(cd_item=row.CD_ITEM, cd_empresa=filters["empresa"])

                # Cálculo do estoque atual com tratamento de valores vazios
                estoque_atual = 0 if df_estoque.empty or isna(
                    df_estoque["QT_ESTOQUE"].values[0]) else df_estoque["QT_ESTOQUE"].values[0]

                # Dados e cálculos
                vendas_360d = row.MES_12 / 360
                vendas_periodo_atual = row.MES_ATUAL
                dias_periodo_atual = row.DIAS_ATUAL
                lead_time_dias = filters["lead_time"]
                fator_seguranca = filters["fator_seguranca"]
                tempo_cobertura_dias = filters["stock_duration"]

                # Combinação ponderada (80% histórico, 20% recente)
                demanda_diaria = (vendas_360d * 0.8) + ((vendas_periodo_atual / dias_periodo_atual) * 0.2)

                # Estoque de segurança = demanda diária * dias de proteção (fator_seguranca * 30)
                estoque_seguranca = demanda_diaria * fator_seguranca

                # Quantidade a comprar = (Demanda Diária × (Lead Time + Cobertura)) - Estoque Atual + Segurança
                quantidade_comprar = max(
                    0,
                    (demanda_diaria *
                     (lead_time_dias + tempo_cobertura_dias))
                    - estoque_atual
                    + estoque_seguranca
                )

                # Arredondamento conforme configuração
                if filters["arredondar_valor"]:
                    quantidade_comprar = ceil(quantidade_comprar)
                else:
                    quantidade_comprar = round(quantidade_comprar, 2)

                # Atualiza o cache na session_state
                add_to_cache(
                    cod=row.CD_ITEM,
                    leadtime=lead_time_dias,
                    duration=tempo_cobertura_dias,
                    purchase=quantidade_comprar
                )

            # Atualiza o DataFrame com os valores calculados
            for item in st.session_state.itens:
                mask = df_table['CD_ITEM'] == item['cod']
                df_table.loc[mask, 'QNT_COMPRAR'] = item['comprar']
            # Força o rerun para atualizar a grid
            st.rerun()

        if st.button("Integrar", use_container_width=True):
            if "STATUS_INTEGRADO" not in st.session_state:
                st.session_state.STATUS_INTEGRADO = False
            st.session_state.STATUS_INTEGRADO = False

            integracao_cotacao(st.session_state.df_table)


if __name__ == "__main__":
    compras_view()
