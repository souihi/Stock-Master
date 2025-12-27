import streamlit as st
import time
import streamlit.components.v1 as components
import pandas as pd
import io
from datetime import datetime
from backend import StockProcessor

# --- CONFIGURATION ---
st.set_page_config(page_title="Comparateur Stock", layout="wide")

# --- CSS---
st.markdown("""
    <style>
    .metric-box {
        background-color: #08101e;
        border-left: 5px solid #ff4b4b;
        padding: 15px;
        border-radius: 5px;
        font-weight: bold;
    }
    .alert-box {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 10px;
        margin-bottom: 5px;
        color: #856404;
    }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'history' not in st.session_state:
    st.session_state.history = []
if 'current_search' not in st.session_state:
    st.session_state.current_search = None
if 'scan_input' not in st.session_state:
    st.session_state.scan_input = ""

processor = StockProcessor()

# --- APPLICATION ---
st.title("STOCKITO")

# Création des onglets
tab_global, tab_tournant = st.tabs(["MAGASIN VS POUS", "INVENTAIRE TOURNANT"])


with tab_global:
    col_up1, col_up2 = st.columns(2)
    with col_up1:
        f_terrain = st.file_uploader("STOCK MAGASIN", type=["xlsx", "xls", "csv", "ods", "xlsm"], key="t_up")
    with col_up2:
        f_info = st.file_uploader("STOCK POUS", type=["xlsx", "xls", "csv", "ods", "xlsm"], key="i_up")

    if f_terrain and f_info:
        # Utilisation du backend
        if processor.load_data(f_terrain, f_info):
            
            # --- TRAITEMENT via Backend ---
            merged = processor.process_comparison()

            # --- INTERFACE ---
            nb_ecarts = len(merged[merged['Ecart'] != 0])
            st.markdown(f'<div class="metric-box">⚠️ Nombre d\'articles avec écarts : {nb_ecarts}</div>', unsafe_allow_html=True)
            st.write("")

            st.info("Corrigez la colonne **'Qte Info (Logiciel)'** ci-dessous.")
            
            df_display = merged[merged['Ecart'] != 0].copy()

            edited_df = st.data_editor(
                df_display,
                column_order=['Code', 'Libellé', 'Lot', 'Qte_Terrain', 'Qte_Info', 'Ecart'],
                disabled=['Code', 'Libellé', 'Lot', 'Qte_Terrain', 'Ecart'],
                column_config={
                    "Qte_Info": st.column_config.NumberColumn("Qte Info (Logiciel)", step=1, required=True),
                    "Qte_Terrain": st.column_config.NumberColumn("Qte Terrain", format="%d"),
                    "Ecart": st.column_config.NumberColumn("Ecart", format="%d"),
                },
                use_container_width=True,
                num_rows="fixed",
                key="editor"
            )

            # ALERTES
            edited_df['Ecart_Final'] = edited_df['Qte_Info'] - edited_df['Qte_Terrain']
            changes = edited_df[edited_df['Qte_Info'] != edited_df['_Original_Info']]
            
            if not changes.empty:
                st.write("### Actions requises")
                for idx, row in changes.iterrows():
                    st.markdown(f"""
                    <div class="alert-box">
                        <b>{row['Code']} ({row['Libellé']})</b> : Mettre à jour stock informatique à <b>{int(row['Qte_Info'])}</b>.
                    </div>
                    """, unsafe_allow_html=True)
            
            st.divider()

            # --- EXPORTS ---
            c1, c2 = st.columns(2)

            with c1:
                st.subheader("1. Rapport d'Écarts")
                # Appel Backend pour génération Excel
                buffer_rapport = processor.generate_diff_report(edited_df)
                date_str = datetime.now().strftime("%d-%m-%Y_%Hh%M")
                nom_fichier_rapport = f"Rapport_Ecarts_{date_str}.xlsx"
                st.download_button("Télécharger Rapport", buffer_rapport, nom_fichier_rapport, mime="application/vnd.ms-excel", use_container_width=True)

            with c2:
                st.subheader("2. Fichier Final")
                st.caption("Génère l'inventaire complet au format du fichier informatique.")
                
                confirm_update = st.checkbox("Je confirme vouloir générer le fichier de mise à jour complet", key="confirm_global")
                
                if confirm_update:
                    # Appel Backend pour la logique complexe de reconstruction
                    buffer_maj = processor.generate_final_update(edited_df, merged)
                    
                    date_str = datetime.now().strftime("%d-%m-%Y %Hh%M")
                    nom_fichier_final = f"STOCK MAGASIN {date_str}.xlsx"
                    
                    st.download_button(
                        "Mise à jour du stock magasin", 
                        buffer_maj, 
                        nom_fichier_final, 
                        mime="application/vnd.ms-excel", 
                        type="primary", 
                        use_container_width=True
                    )
                else:
                    st.warning("Veuillez cocher la case pour générer le fichier.")
        else:
             st.error("Colonnes introuvables. Vérifiez les fichiers.")
    else:
        st.info("En attente des fichiers...")

# ==============================================================================
# ONGLET 2 : NOUVELLE FONCTIONNALITÉ (INVENTAIRE TOURNANT)
# ==============================================================================
with tab_tournant:
    st.caption("Scan article par article pour vérification rapide.")
    
    # 1. Chargement du fichier de référence (POUS)
    file_ref = st.file_uploader("Charger le fichier STOCK POUS (Référence)", type=["xlsx", "xls", "csv", "ods", "xlsm"], key="ref_up")
    
    if file_ref:
        # Chargement du fichier en mémoire
        if 'df_ref' not in st.session_state or st.session_state.get('file_ref_name') != file_ref.name:
            from utils import charger_fichier_pandas, trouver_colonne
            df = charger_fichier_pandas(file_ref)
            st.session_state.df_ref = df
            st.session_state.file_ref_name = file_ref.name
            # Identification basique des colonnes pour cet onglet
            st.session_state.col_code = trouver_colonne(df, ['code', 'article', 'ref'])
            st.session_state.col_qte = trouver_colonne(df, ['qte', 'quant', 'stock'])
            st.session_state.col_lib = trouver_colonne(df, ['lib', 'designation'])
            st.session_state.col_lot = trouver_colonne(df, ['lot', 'serie'])
            st.success(f"Fichier chargé : {len(df)} lignes.")

        df = st.session_state.df_ref
        
        # 2. Zone de Scan
        st.divider()
        col_scan, col_result = st.columns([1, 2])
        
        with col_scan:
            def run_search():
                query = st.session_state.scan_input
                if query:
                    # --- Logique de recherche ---
                    mask = pd.Series(False, index=df.index)
                    for col in df.columns:
                        try:
                            mask = mask | (df[col].astype(str).str.strip().str.upper() == str(query).strip().upper())
                        except: pass
                    res = df[mask]
                    if not res.empty:
                        st.session_state.current_search = res.iloc[0].to_dict()
                        st.session_state.search_status = "found"
                    else:
                        st.session_state.current_search = None
                        st.session_state.search_status = "not_found"
                    
                    st.session_state.scan_input = ""

            label_scan = "SCANNER ICI"
            
            # 1. L'INPUT
            st.text_input(label_scan, key="scan_input", on_change=run_search)

            # 2. LE SCRIPT
            timestamp = int(time.time() * 1000)
            
            components.html(f"""
                <script>
                    var input = window.parent.document.querySelector('input[aria-label="{label_scan}"]');
                    if (input) {{
                        input.focus();
                        input.select();
                    }}
                    // Force re-load timestamp: {timestamp}
                </script>
            """, height=0, width=0)

            st.caption("Le curseur est verrouillé sur cette case.")

        # 3. Affichage Résultat
        with col_result:
            if st.session_state.get('current_search'):
                item = st.session_state.current_search
                c_code = st.session_state.col_code
                c_lib = st.session_state.col_lib
                c_qte = st.session_state.col_qte
                c_lot = st.session_state.col_lot
                
                # Carte d'info
                st.info(f"Article trouvé : {item.get(c_code)}")
                st.markdown(f"## {item.get(c_lib)}")
                if c_lot:
                    st.write(f"**Lot/Série :** {item.get(c_lot)}")
                
                # Gestion Quantité
                qte_info = item.get(c_qte, 0)
                st.metric("Quantité Informatique", qte_info)
                
                # Actions
                st.write("---")
                col_btn1, col_btn2 = st.columns(2)
                
                # Bouton OK
                if col_btn1.button("STOCK OK", use_container_width=True, type="primary"):
                    st.session_state.history.insert(0, {
                        "Heure": datetime.now().strftime("%H:%M:%S"),
                        "Code": item.get(c_code),
                        "Libellé": item.get(c_lib),
                        "Ancien Stock": qte_info,
                        "Nouveau Stock": qte_info,
                        "Statut": "OK"
                    })
                    st.toast("Stock confirmé !")
                    st.session_state.current_search = None # Reset
                    st.rerun()

                # Bouton Correction
                with col_btn2:
                    # step=1 empêche les décimales à la saisie
                    new_qte = st.text_input("Nouvelle Quantité Réelle", value=float(qte_info))
                    
                    if st.button("CORRIGER STOCK"):
                        # On force la conversion en int() ici pour nettoyer les zéros
                        valeur_propre = int(new_qte) 
                        ancien_propre = int(qte_info) if pd.notna(qte_info) else 0

                        st.session_state.history.insert(0, {
                            "Heure": datetime.now().strftime("%H:%M:%S"),
                            "Code": item.get(c_code),
                            "Libellé": item.get(c_lib),
                            "Ancien Stock": ancien_propre,  # Nettoyé
                            "Nouveau Stock": valeur_propre, # Nettoyé (300 au lieu de 300.000)
                            "Statut": "CORRECTION"
                        })
                        st.toast("Correction enregistrée !")
                        st.session_state.current_search = None # Reset
                        st.rerun()

    # 4. Historique de la session
    st.divider()
    st.subheader("Historique de la session")
    if st.session_state.history:
        df_hist = pd.DataFrame(st.session_state.history)
        
        # Coloration conditionnelle simple
        def color_status(val):
            color = "#7ae994" if val == 'OK' else "#fd0015" # Vert vs Rouge pastel
            return f'background-color: {color}'

        st.dataframe(df_hist.style.applymap(color_status, subset=['Statut']), use_container_width=True)
        
        # Export Session
        buffer_hist = io.BytesIO()
        with pd.ExcelWriter(buffer_hist, engine='xlsxwriter') as writer:
            df_hist.to_excel(writer, index=False)
            date_str = datetime.now().strftime("%d-%m-%Y %Hh%M")
            nom_fichier_final = f"Inventaire_Tournant {date_str}.xlsx"
        st.download_button("Télécharger l'historique de session", buffer_hist, nom_fichier_final)
    else:
        st.caption("Scannez des articles pour voir l'historique.")