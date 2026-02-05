import streamlit as st
from ressource.backend import StockProcessor
from views.comparaison_view import render_comparaison_view
from views.inventaire_tournant_view import render_inventory_view

# 1. CONFIGURATION GLOBALE
st.set_page_config(page_title="Comparateur Stock", layout="wide")

# 2. CHARGEMENT ASSETS (CSS)
with open("assets/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# 3. INITIALISATION SESSION (STATE)
if 'history' not in st.session_state: st.session_state.history = []
if 'current_search' not in st.session_state: st.session_state.current_search = None
if 'scan_input' not in st.session_state: st.session_state.scan_input = ""

# 4. INSTANCIATION DES SERVICES (BACKEND)
processor = StockProcessor()

# 5. ROUTAGE (LAYOUT PRINCIPAL)
st.title("STOCKITO")

tab_global, tab_tournant = st.tabs(["MAGASIN VS POUS", "INVENTAIRE TOURNANT"])

with tab_global:
    # On délègue tout l'affichage à la Vue dédiée
    render_comparaison_view(processor)

with tab_tournant:
    # On délègue tout l'affichage à la Vue dédiée
    render_inventory_view(processor)