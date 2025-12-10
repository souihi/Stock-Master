import streamlit as st
import pandas as pd
import io
import time
import warnings

# --- 1. NETTOYAGE DES LOGS ---
warnings.filterwarnings("ignore", category=UserWarning, module="xlrd")

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Stock Master",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS PERSONNALISÉ ---
st.markdown("""
    <style>
    .big-font { font-size:20px !important; font-weight: bold; }
    .stMetric { background-color: #0a3057; padding: 10px; border-radius: 10px; }
    .alert-box { 
        padding: 15px; 
        background-color: #fff3cd; 
        color: #856404;
        border-left: 6px solid #ffeeba;
        margin-bottom: 10px;
        border-radius: 4px;
    }
    </style>
""", unsafe_allow_html=True)

# --- INITIALISATION SESSION STATE (Mémoire) ---
# On stocke les dataframes originaux pour qu'ils soient dispos partout
if 'df_i_raw' not in st.session_state: st.session_state.df_i_raw = None
if 'cols_i' not in st.session_state: st.session_state.cols_i = {}
if 'audit_data' not in st.session_state: st.session_state.audit_data = None

# --- SIDEBAR ---
with st.sidebar:
    st.title("Mode d'emploi")
    st.info("""
    **Étape 1 :** Chargez vos deux fichiers.
    **Étape 2 :** Lancez l'audit.
    **Étape 3 :** Corrigez les écarts en direct.
    **Étape 4 :** Générez le fichier final.
    """)
    st.divider()
    st.caption("Version 6.1 - Stable & Mémoire")

# --- FONCTIONS ROBUSTES ---
def charger_et_trouver_header(uploaded_file, nom_fichier):
    try:
        uploaded_file.seek(0)
        if uploaded_file.name.endswith('.csv'):
            preview = pd.read_csv(uploaded_file, header=None, nrows=20)
        else:
            preview = pd.read_excel(uploaded_file, header=None, nrows=20)
        
        header_row_idx = 0
        for i, row in preview.iterrows():
            row_text = row.astype(str).str.lower().str.cat(sep=' ')
            if 'code' in row_text and ('lot' in row_text or 'article' in row_text or 'ref' in row_text):
                header_row_idx = i
                break
        
        uploaded_file.seek(0)
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, header=header_row_idx)
        else:
            df = pd.read_excel(uploaded_file, header=header_row_idx)
            
        df.columns = df.columns.astype(str).str.strip().str.lower()
        return df
    except Exception as e:
        return None

def get_col(df, mots_cles):
    for col in df.columns:
        for mot in mots_cles:
            if mot in col:
                return col
    return None

# --- TITRE ---
st.title("Stock Master : Comparateur Intelligent")
st.markdown("Comparez votre **Inventaire Physique** avec votre **Stock Informatique**.")
st.divider()

# --- CHARGEMENT ---
col1, col2 = st.columns(2)
with col1:
    st.subheader("Fichier Terrain")
    f_terrain = st.file_uploader("Glissez le fichier ici", type=["xlsx", "xls", "csv"], key="t")

with col2:
    st.subheader("Fichier Informatique")
    f_info = st.file_uploader("Glissez le fichier ici", type=["xlsx", "xls", "csv"], key="i")

if f_terrain and f_info:
    # Lecture silencieuse pour préparer les données
    df_t_raw = charger_et_trouver_header(f_terrain, "Terrain")
    df_i_raw = charger_et_trouver_header(f_info, "Informatique")

    if df_t_raw is not None and df_i_raw is not None:
        # Identification colonnes
        t_code = get_col(df_t_raw, ['code', 'article', 'ref'])
        t_lot = get_col(df_t_raw, ['lot', 'serie', 'batch'])
        t_qte = get_col(df_t_raw, ['quantit', 'qte', 'stock'])
        t_lib = get_col(df_t_raw, ['libel', 'designation'])

        i_code = get_col(df_i_raw, ['code', 'article', 'ref'])
        i_lot = get_col(df_i_raw, ['lot', 'serie', 'batch'])
        i_qte = get_col(df_i_raw, ['quantit', 'qte', 'stock'])
        i_lib = get_col(df_i_raw, ['libel', 'designation'])

        # SAUVEGARDE EN MEMOIRE (POUR L'ONGLET 2)
        st.session_state.df_i_raw = df_i_raw
        st.session_state.cols_i = {'code': i_code, 'lot': i_lot, 'qte': i_qte, 'lib': i_lib}

        if not all([t_code, t_lot, t_qte, i_code, i_lot, i_qte]):
            st.error("Colonnes manquantes.")
            st.stop()

        # --- ACTIONS ---
        st.write("") 
        tab_audit, tab_reset = st.tabs(["AUDIT & CORRECTION", "RESET (Fichier Final)"])

        # --- ONGLET 1 : AUDIT INTERACTIF ---
        with tab_audit:
            # Bouton de lancement
            if st.button("Lancer (ou Relancer) l'Audit", type="primary", use_container_width=True):
                # Standardisation
                df_t = df_t_raw.copy()
                df_i = df_i_raw.copy()

                df_t[t_code] = df_t[t_code].astype(str).str.strip()
                df_t[t_lot] = df_t[t_lot].astype(str).str.strip().str.upper().replace(['NAN', 'NAN', ''], 'SANS_LOT')
                df_t[t_lot] = df_t[t_lot].replace(['STOCK+RECYCL0', 'RECYCL0'], 'STOCK')
                
                df_i[i_code] = df_i[i_code].astype(str).str.strip()
                df_i[i_lot] = df_i[i_lot].astype(str).str.strip().str.upper().replace(['NAN', 'NAN', ''], 'SANS_LOT')
                df_i[i_lot] = df_i[i_lot].replace(['STOCK+RECYCL0', 'RECYCL0'], 'STOCK')

                # Calculs
                t_agg = df_t.groupby([t_code, t_lot])[t_qte].sum().reset_index()
                i_agg = df_i.groupby([i_code, i_lot])[i_qte].sum().reset_index()

                t_agg = t_agg.rename(columns={t_qte: 'Qte_Terrain', t_code: 'Code', t_lot: 'Lot'})
                i_agg = i_agg.rename(columns={i_qte: 'Qte_Info', i_code: 'Code', i_lot: 'Lot'})

                merged = pd.merge(i_agg, t_agg, on=['Code', 'Lot'], how='outer')
                merged['Qte_Info'] = merged['Qte_Info'].fillna(0)
                merged['Qte_Terrain'] = merged['Qte_Terrain'].fillna(0)
                
                # Libellés
                dict_lib = {}
                if t_lib:
                    try: dict_lib.update(df_t.drop_duplicates(subset=[t_code]).set_index(t_code)[t_lib].to_dict())
                    except: pass
                if i_lib:
                    try: dict_lib.update(df_i.drop_duplicates(subset=[i_code]).set_index(i_code)[i_lib].to_dict())
                    except: pass
                merged['Libellé'] = merged['Code'].map(dict_lib).fillna("-")

                # IMPORTANT : On garde une copie de la valeur originale pour détecter les changements
                merged['_Original_Info'] = merged['Qte_Info']

                # On stocke dans la mémoire et on ne garde que ce qui a un écart par défaut
                st.session_state.audit_data = merged[merged['Qte_Info'] - merged['Qte_Terrain'] != 0].copy()

            # Affichage de l'éditeur SI les données existent
            if st.session_state.audit_data is not None:
                
                st.divider()
                st.info("Vous pouvez modifier la colonne **'Qte_Info'** ci-dessous pour corriger votre stock informatique.")

                # Configuration de l'éditeur
                edited_df = st.data_editor(
                    st.session_state.audit_data,
                    disabled=["Code", "Libellé", "Lot", "Qte_Terrain", "_Original_Info"], # On bloque tout sauf Qte_Info
                    column_config={
                        "Qte_Info": st.column_config.NumberColumn(
                            "Qté Info (MODIFIABLE)",
                            help="Cliquez pour modifier la valeur informatique",
                            step=1,
                            required=True
                        ),
                        "_Original_Info": None # On cache la colonne technique
                    },
                    use_container_width=True,
                    key="data_editor",
                    num_rows="fixed"
                )
      
                # --- LOGIQUE D'ALERTE ---
                changes = edited_df[edited_df['Qte_Info'] != edited_df['_Original_Info']]

                if not changes.empty:
                    st.markdown("###ACTIONS REQUISES (Mise à jour PC)")
                    for index, row in changes.iterrows():
                        code = row['Code']
                        lib = row['Libellé']
                        old_val = int(row['_Original_Info'])
                        new_val = int(row['Qte_Info'])
                        
                        st.markdown(f"""
                        <div class="alert-box">
                            <b>Article {code} ({lib})</b> : <br>
                            Veuillez mettre à jour le stock informatique à <b>{new_val}</b> (au lieu de {old_val}).
                        </div>
                        """, unsafe_allow_html=True)

                # Recalcul de l'écart dynamique pour l'affichage
                edited_df['Ecart_Final'] = edited_df['Qte_Info'] - edited_df['Qte_Terrain']
                
                # Export du rapport (avec les corrections prises en compte)
                st.markdown("---")
                cols_export = ['Code', 'Libellé', 'Lot', 'Qte_Terrain', 'Qte_Info', 'Ecart_Final']
                
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                    edited_df[cols_export].to_excel(writer, index=False)
                
                st.download_button(
                    "Télécharger le Rapport d'Écarts (Corrigé)", 
                    buf, 
                    "Rapport_Ecarts_Corrigé.xlsx", 
                    use_container_width=True
                )

        # --- ONGLET 2 : RESET (CORRIGÉ) ---
        with tab_reset:
            if st.button("Générer Fichier Reset", use_container_width=True):
                # On récupère les données de la session
                df_raw = st.session_state.df_i_raw
                cols = st.session_state.cols_i
                
                if df_raw is not None:
                    with st.spinner("Génération..."):
                        time.sleep(0.5)
                        
                        # On utilise les colonnes sauvegardées
                        ic = cols['code']
                        il = cols['lot']
                        iq = cols['qte']
                        ilb = cols['lib']

                        # Standardisation (Même traitement que l'audit)
                        df_raw[ic] = df_raw[ic].astype(str).str.strip()
                        df_raw[il] = df_raw[il].astype(str).str.strip().str.upper().replace(['NAN', 'NAN', ''], 'SANS_LOT')
                        df_raw[il] = df_raw[il].replace(['STOCK+RECYCL0', 'RECYCL0'], 'STOCK')

                        df_reset = df_raw.copy()
                        agg_rules = {iq: 'sum'}
                        if ilb: agg_rules[ilb] = 'first'
                        
                        df_reset = df_reset.groupby([ic, il]).agg(agg_rules).reset_index()

                        rename_map = {ic: 'code_article', il: 'lot', iq: 'quantite_stock'}
                        if ilb: rename_map[ilb] = 'libelle_article'
                        
                        df_final = df_reset.rename(columns=rename_map)
                        
                        cols_final = ['code_article', 'lot', 'quantite_stock']
                        if ilb: cols_final.insert(1, 'libelle_article')
                        
                        # Sécurité pour ne garder que les colonnes qui existent vraiment
                        existing_cols = [c for c in cols_final if c in df_final.columns]
                        df_final = df_final[existing_cols]
                        
                        st.success("Fichier généré !")
                        
                        buf_res = io.BytesIO()
                        with pd.ExcelWriter(buf_res, engine='xlsxwriter') as writer:
                            df_final.to_excel(writer, index=False)
                        
                        st.download_button("Télécharger Fichier Terrain", buf_res, "Nouveau_Inventaire.xlsx", use_container_width=True)
                else:
                    st.error("Erreur : Veuillez recharger les fichiers (F5).")

else:
    st.info("Chargez vos fichiers pour commencer.")