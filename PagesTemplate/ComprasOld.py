import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder
from Database.QueriesOld import (fetch_purchase_orders, get_brands_filter, pedidos_aberto,
                                  buscar_similar_estoque, integrar_cotacao, exc_integrar_cotacao, retorna_mov_mensal)
from pandas import DataFrame
from math import ceil


def fetch_filtered_purchase_orders(group_code, sub_code, piece_code, brand, application, empresa, peca_fornecedor,
                                   desc_peca, tipo_filtro):
    """Obtém o DataFrame de pedidos de compra e aplica os filtros."""
    df = fetch_purchase_orders(cd_empresa=empresa)

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
    if group_code:
        df = df[df["CD_GRUPO"] == group_code]
    if sub_code:
        df = df[df["CD_SUBGRUPO"] == str(sub_code).zfill(2)]
    if piece_code:
        df = df[df["CD_PECA"] == str(piece_code).zfill(3)]
    if brand:
        df = df[df["FABRICANTE"].isin(brand)]
    if application:
        df['DS_APLICACAO'] = df['DS_APLICACAO'].fillna('')
        if tipo_filtro:
            df = df[df["DS_APLICACAO"].str.startswith(
                str(application).upper())]
        else:
            df = df[df["DS_APLICACAO"].str.contains(application, case=False)]
    if peca_fornecedor:
        df['CD_FORNECEDOR1'] = df['CD_FORNECEDOR1'].fillna('')
        if tipo_filtro:
            df = df[df["CD_FORNECEDOR1"].str.startswith(
                str(peca_fornecedor).upper())]
        else:
            df = df[df["CD_FORNECEDOR1"].str.contains(
                peca_fornecedor, case=False)]
    if desc_peca:
        df['DS_ITEM'] = df['DS_ITEM'].fillna('')
        if tipo_filtro:
            df = df[df["DS_ITEM"].str.startswith(str(desc_peca).upper())]
        else:
            df = df[df["DS_ITEM"].str.contains(desc_peca, case=False)]
    return df


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
            cd_comprador=comprador, nr_cotacao=cotacao, cd_empresa=empresa, cd_item=0, qt_item=0, tp_operacao="V")
        if df_integracao is not None:
            if df_integracao['O_ERROR'].values[0] == 'S':
                st.warning(f"{df_integracao["O_DS_MENSAGEM"].values[0]}")

            if df_integracao['O_ERROR'].values[0] == 'N':
                st.text(f"Empresa: {df_integracao["O_CD_EMPRESA"].values[0]}")
                st.text(
                    f"Nr Cotação: {df_integracao["O_ID_COTACAO"].values[0]}")
                st.text(
                    f"Desc Cotação: {df_integracao["O_DS_COTACAO"].values[0]}")
                st.text(f"Comprador: {df_integracao["O_NM_PESSOA"].values[0]}")
        else:
            st.error("Não localizado")
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


def calculate_purchase(df: DataFrame, item_code, leadtime, stock_duration):
    """Calcula a quantidade a ser comprada com base nos dados do produto."""
    # Filtra a linha do produto
    df['QNT_COMPRAR'] = df['QNT_COMPRAR'].astype('float64')
    df_itens = df

    for product_row in df_itens.itertuples(index=True, name='Pandas'):
        stock_local = product_row.QT_ESTOQUE
        mv_12m = product_row.MV_12M

        # Cálculo da quantidade a ser comprada
        quantity_to_buy = (mv_12m / 30) * \
            (stock_duration + leadtime) - stock_local

        # Adiciona ou atualiza no cache
        add_to_cache(cod=product_row.CD_ITEM, leadtime=leadtime,
                     duration=stock_duration, purchase=quantity_to_buy)

        # Atualiza a coluna QNT_COMPRAR no DataFrame df
        linha = df.loc[df['CD_ITEM'] == product_row.CD_ITEM]

        # Verifica se a linha foi encontrada
        if not linha.empty:
            # Atribui o valor arredondado e convertido para inteiro à coluna 'QNT_COMPRAR'
            df.loc[df['CD_ITEM'] == product_row.CD_ITEM,
                   'QNT_COMPRAR'] = float(quantity_to_buy)
        else:
            print(f"Item com código {item_code} não encontrado no DataFrame.")


def configure_aggrid(df_compras):
    """Configura o AgGrid com colunas personalizadas."""
    gb = GridOptionsBuilder.from_dataframe(df_compras)
    gb.configure_column("QNT_COMPRAR")
    gb.configure_column("Qtde O", editable=True)

    # Nome das colunas
    column_names = {
        "CD_ITEM": "Código",
        "DS_ITEM": "Descrição Peça",
        "DS_APLICACAO": "Aplicação",
        "FABRICANTE": "Fabricante",
        "CD_FORNECEDOR1": "Número",
        "QNT_COMPRAR": "Qtde"
    }
    for old_name, new_name in column_names.items():
        gb.configure_column(old_name, header_name=new_name, maxWidth=350)

    gb.configure_selection(selection_mode='single')
    return gb.build()


def display_product_info(selected_rows, df):
    """Exibe as informações adicionais do produto selecionado."""
    if selected_rows is not None and len(selected_rows) > 0:
        cd_item = selected_rows.iloc[0]["CD_ITEM"]
        product_data = df[df['CD_ITEM'] == cd_item]

        if not product_data.empty:

            # Criação de colunas para exibir as métricas em pares
            col1, col2, col3 = st.columns([2, 1, 2], gap="small")
            with col1:
                tempo_medio = product_data["TEMPO"].values[0]
                st.metric(label="Duração do Estoque",
                          value=tempo_medio, border=True)
            with col2:
                st.metric(
                    label="M.V", value=product_data["MV_12M"].values[0], border=True)
            with col3:
                st.metric(label="Ultima Compra",
                          value=product_data["ULTIMACOMPRA"].values[0], border=True)

            # Buscar o estoque das empresas (Filliais)
            df_estoq_filial = buscar_similar_estoque(cd_item=cd_item)
            if df_estoq_filial is not None:
                df_estoq_filial = df_estoq_filial.rename(
                    columns={"CD_ITEM": "Similar",  "DS_MARCA": "Marca", "QT_EMP1": "Emp1", "QT_EMP5": "Emp5", "QT_EMP7": "Emp7", "QT_EMP52": "Emp52"})
            st.dataframe(df_estoq_filial, hide_index=True,
                         width=450, height=250,
                         column_config={
                             "Marca": st.column_config.TextColumn(
                                 width="small"  # Pode ser 'small', 'medium', 'large'
                             )
                         })
            
            df_pedidos = pedidos_aberto(cd_empresa=st.session_state.EMPRESACOMPRA, cd_item=cd_item)
            df_pedidos = df_pedidos.rename(columns={"NR_PEDIDO": "Nr Pedido", "DT_PEDIDO":"Data Pedido", "QNTD": "Qntd"})
            st.dataframe(df_pedidos,hide_index=True, height=150,width=300,
                         column_config={
                             "Nr Pedido": st.column_config.TextColumn(
                                 width="small"  # Pode ser 'small', 'medium', 'large'
                                )}
                             )
            
            st.text_area(
                "Aplicação", value=f"{product_data["DS_APLICACAO"].values[0]}", disabled=True, height=250)
            st.markdown("🟩 - Item com pedido de compra em aberto")
            st.markdown("🟥 - Item sem Movimentação de Venda")

        if st.sidebar.button(label="Calcular Compra", use_container_width=True):
            calculate_purchase(
                df, cd_item, st.session_state.LEADTIME, st.session_state.STOCKDURATION)
            st.rerun()

        if st.sidebar.button("Integrar", use_container_width=True):
            if "STATUS_INTEGRADO" not in st.session_state:
                st.session_state.STATUS_INTEGRADO = False
            st.session_state.STATUS_INTEGRADO = False
            integracao_cotacao(df)

    else:
        st.warning("Nenhuma linha selecionada.")


def compras_view():
    """Função principal para exibição da página de compras."""
    with st.sidebar:
        empresa = st.pills("Empresa ", [7, 40, 50, 60], key="EMPRESACOMPRA")
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

        tipo_filtro = st.toggle("[Começa com]")

        desc_peca = st.text_input(
            f"{"[Começa com]" if tipo_filtro else "[Contém na]"} - Desc. Peça")
        application = st.text_input(
            f"{"[Começa com]" if tipo_filtro else "[Contém na]"} - Aplicação")
        peca_fornecedor = st.text_input(
            f"{"[Começa com]" if tipo_filtro else "[Contém na]"} - Código Peça Fabricante")
        brand_filter = st.multiselect(
            "Selecione a(s) Marcas", options=get_brands_filter())
        # valor_cima_zero = st.checkbox("Filtrar somente valores superiores a 0")
        st.checkbox("Arrendodar valor", value=True, key="ARREDONDAR_VALOR")

        # Lead time e duração do estoque
        col_lead, col_stock = st.columns(2)
        with col_lead:
            lead_time = st.number_input(
                "LeadTime", value=1, min_value=1, key="LEADTIME")
        with col_stock:
            stock_duration = st.number_input(
                "Ciclo do Estoque",
                value=1,
                min_value=1,
                help="""Determine o tempo ideal que os produtos devem permanecer em estoque(**DIAS**)""",
                key="STOCKDURATION"
            )

    col1, col2 = st.columns([2.6, 1])

    if empresa:
        # Exibição da tabela de pedidos de compra
        with col1:
            with st.container(height=950, border=True, key="PEDIDOCOMPRA"):
                df = fetch_filtered_purchase_orders(group_code=group, sub_code=sub_group, piece_code=piece,
                                                    brand=brand_filter, application=application,
                                                    empresa=empresa, peca_fornecedor=peca_fornecedor,
                                                    desc_peca=desc_peca, tipo_filtro=tipo_filtro)

                df["Qtde O"] = None
                df["FLAGS"] = df["MOV_PRODUTO"].apply(
                    lambda x: "🟩" if x == "VERDE " else "")

                df_compras = df[["CD_ITEM", "DS_ITEM", "DS_APLICACAO",
                                 "FABRICANTE", "CD_FORNECEDOR1", "QNT_COMPRAR", "Qtde O", "FLAGS"]]
                
                st.data_editor(df_compras)
                #grid_options = configure_aggrid(df_compras)
                #response = AgGrid(df_compras, gridOptions=grid_options,
                #                  height=840, key="compras", enable_enterprise_modules=True, theme="streamlit")

                # Acessa as linhas selecionadas
                response = {"selected_rows" : None}
                selected_rows = response['selected_rows']

        # Exibição das informações adicionais no lado direito
        with col2:
            with st.container(border=True, key="INFOADICIONAIS", height=950):
                display_product_info(selected_rows, df)
        
        with st.container(border=True, key="MOV_MENSAL"):
            if selected_rows is not None and len(selected_rows) > 0:
                cd_item_mov = selected_rows.iloc[0]["CD_ITEM"]
                valor_mov = retorna_mov_mensal(
                    cd_empresa=st.session_state.EMPRESACOMPRA, cd_item=cd_item_mov)
                st.bar_chart(data=valor_mov, x="DATA_EMISSAO", y="QUANTIDADE_VENDA",
                            height=500, x_label="Data de EMissão", y_label="Quantidade")

    else:
        st.warning("Selecione uma empresa")
