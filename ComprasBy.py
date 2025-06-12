import streamlit as st
from PagesTemplate.Compras import compras_view
import warnings

warnings.simplefilter(action='ignore', category=UserWarning)

st.set_page_config(layout="wide")

st.markdown("""
<style>
    .stMainBlockContainer {
        padding: 3rem 1rem        
    }
    .stMetric {
        font-size: 15px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 15px    
    }
    div[data-testid="stSidebarHeader"] {
        padding: 0;
    }
    </style>
""", unsafe_allow_html=True)
menu = st.navigation([st.Page(compras_view, title="Compras")])
menu.run()
