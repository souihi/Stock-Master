import streamlit as st
import pandas as pd
from datetime import datetime
from components.atoms import display_article_card, inject_focus_script
from ressource.utils import charger_fichier_pandas, trouver_colonne

def render_inventory_view(processor):
    """Affiche l'onglet Inventaire Tournant"""
    
    # 1. Chargement
    with st.expander("Charger fichier POUS", expanded=True if 'df_ref' not in st.session_state else False):
        file_ref = st.file_uploader("Fichier POUS", type=["xlsx", "xls", "csv", "ods", "xlsm"], key="ref_up")
    
    if file_ref:
        _handle_file_load(file_ref) # Fonction privée en bas pour alléger
        
        # 2. Barre de Scan
        label_scan = "SCANNER ICI"
        st.text_input(label_scan, key="scan_input", on_change=_run_search, placeholder="Cliquez ici...")
        inject_focus_script(label_scan)
        
        st.divider()

        # 3. Résultat
        if st.session_state.get('current_search'):
            _render_result_card()
        elif st.session_state.get('search_status') == "not_found":
            st.error("❌ Article inconnu")
            
        # 4. Historique
        st.write("")
        with st.expander(f"📝 Historique ({len(st.session_state.history)})"):
            if st.session_state.history:
                st.dataframe(pd.DataFrame(st.session_state.history), use_container_width=True)

# --- Helpers internes à la vue ---
def _handle_file_load(file_ref):
    if 'df_ref' not in st.session_state or st.session_state.get('file_ref_name') != file_ref.name:
        df = charger_fichier_pandas(file_ref)
        st.session_state.df_ref = df
        st.session_state.file_ref_name = file_ref.name
        # Initialisation des colonnes dans session_state
        st.session_state.col_code = trouver_colonne(df, ['code', 'article', 'ref'])
        st.session_state.col_qte = trouver_colonne(df, ['qte', 'quant', 'stock'])
        st.session_state.col_lib = trouver_colonne(df, ['lib', 'designation'])
        st.session_state.col_lot = trouver_colonne(df, ['lot', 'serie'])
        st.toast(f"Chargé : {len(df)} lignes")

def _run_search():
    """
    Logique de recherche déclenchée par le scan.
    Cherche l'article, agrège les quantités si multi-lots, et met à jour l'état.
    """
    # 1. Récupération de la saisie
    query = st.session_state.scan_input
    
    # Si vide ou si le fichier n'est pas chargé, on arrête
    if not query or 'df_ref' not in st.session_state:
        return

    # 2. Récupération du contexte (Dataframe + Noms des colonnes stockés en session)
    df = st.session_state.df_ref
    c_code = st.session_state.col_code
    c_qte = st.session_state.col_qte
    c_lot = st.session_state.col_lot  # Peut être None

    # 3. Recherche "Large" (Match sur n'importe quelle colonne)
    # On crée un masque vide (False partout)
    mask = pd.Series(False, index=df.index)
    
    for col in df.columns:
        try:
            # On convertit tout en string majuscule pour comparer
            mask = mask | (df[col].astype(str).str.strip().str.upper() == str(query).strip().upper())
        except: 
            pass
    
    res_prelim = df[mask]
    
    # 4. Traitement du résultat
    if not res_prelim.empty:
        # A. On identifie le Code Article unique de l'objet trouvé (via la 1ère ligne trouvée)
        found_article_code = res_prelim.iloc[0][c_code]
        
        # B. On va chercher TOUTES les lignes du fichier qui ont ce code article
        # (Pour gérer les doublons : Stock principal + Lots isolés + Recyclo)
        all_rows = df[df[c_code] == found_article_code]
        
        # C. On calcule la SOMME des quantités
        # pd.to_numeric sécurise le calcul (évite que "5" + "5" fasse "55")
        total_qty = pd.to_numeric(all_rows[c_qte], errors='coerce').fillna(0).sum()
        
        # D. On construit l'objet résultat
        # On prend les métadonnées (Libellé, etc.) de la première ligne
        final_item = all_rows.iloc[0].to_dict()
        
        # On ÉCRASE la quantité unitaire par la QUANTITÉ TOTALE calculée
        final_item[c_qte] = total_qty
        
        # E. Petit bonus : flag visuel si c'est un cumul
        if len(all_rows) > 1 and c_lot:
            final_item[c_lot] = "MULTI-LOTS (CUMUL)"

        # F. Mise à jour du State (Succès)
        st.session_state.current_search = final_item
        st.session_state.search_status = "found"
    
    else:
        # G. Mise à jour du State (Echec)
        st.session_state.current_search = None
        st.session_state.search_status = "not_found"
    
    # 5. Reset du champ de saisie (pour permettre le scan suivant)
    st.session_state.scan_input = ""

def _render_result_card():
    # --- 1. RÉCUPÉRATION DES VARIABLES (C'est ce qui te manquait !) ---
    # On récupère l'objet trouvé et les noms de colonnes depuis la session
    item = st.session_state.current_search
    c_code = st.session_state.col_code
    c_lib = st.session_state.col_lib
    c_qte = st.session_state.col_qte
    c_lot = st.session_state.col_lot # Optionnel

    # On définit qte_info MAINTENANT pour qu'il soit connu partout dans la fonction
    qte_info = item.get(c_qte, 0)

    # --- 2. AFFICHAGE DE LA CARTE ---
    with st.container(border=True):
        # On utilise les variables définies juste au-dessus
        display_article_card(item.get(c_code), item.get(c_lib), 0)
        
        col_metric, col_actions = st.columns([1, 1])
        with col_metric:
            st.metric("STOCK POUS", int(qte_info) if pd.notna(qte_info) else 0)
        
        with col_actions:
            st.write("")
            if st.button("STOCK OK", use_container_width=True):
                _add_history(item, int(qte_info), int(qte_info), "OK")
                st.session_state.current_search = None
                st.toast("Stock validé !")
                st.rerun()

    # --- 3. ZONE DE CORRECTION ---
    with st.expander("⚠️ Faire une correction de stock", expanded=True):
        c_saisie, c_valide = st.columns([2, 1])
        
        with c_saisie:
            new_qte = st.number_input(
                "Quantité Réelle", 
                value=None, 
                step=1, 
                placeholder="Tapez le stock...", 
                label_visibility="collapsed"
            )
            
        with c_valide:
            # Le bouton utilise maintenant les variables définies en haut (1.)
            if st.button("CORRIGER", type="primary", use_container_width=True):
                if new_qte is not None:
                    valeur_propre = int(new_qte)
                    # Ici, qte_info est maintenant bien défini !
                    ancien_propre = int(qte_info) if pd.notna(qte_info) else 0
                    
                    _add_history(item, ancien_propre, valeur_propre, "CORRECTION")
                    
                    st.session_state.current_search = None
                    st.toast("Correction sauvegardée", icon="💾")
                    st.rerun()
                else:
                    st.warning("Saisissez une quantité.")

def _add_history(item, old, new, status):
    """Ajoute une ligne complète à l'historique de session"""
    
    # On récupère les noms de colonnes
    c_code = st.session_state.col_code
    c_lib = st.session_state.col_lib
    
    st.session_state.history.insert(0, {
        "Heure": datetime.now().strftime("%H:%M"),
        "Code": item.get(c_code),
        "Libellé": item.get(c_lib, "N/A"), # "N/A" si pas de colonne libellé
        "Ancien": old,
        "Nouveau": new,
        "Statut": status
    })