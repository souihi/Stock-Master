import streamlit as st
import streamlit.components.v1 as components

def display_metric_box(label, value, is_alert=False):
    """Affiche une boite de métrique custom"""
    color_class = "metric-box" if not is_alert else "alert-box"
    st.markdown(f'<div class="{color_class}">{label} : {value}</div>', unsafe_allow_html=True)

def display_article_card(code, libelle, qte_info):
    """Affiche la grosse carte article pour l'inventaire tournant"""
    st.markdown(f"<div class='big-code'>CODE : {code}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='article-lib'>{libelle}</div>", unsafe_allow_html=True)

def inject_focus_script(label_target):
    """Injecte le JS pour le focus"""
    import time
    timestamp = int(time.time() * 1000)
    components.html(f"""
        <script>
            var input = window.parent.document.querySelector('input[aria-label="{label_target}"]');
            if (input) {{
                input.focus();
                input.select();
            }}
        </script>
    """, height=0, width=0)