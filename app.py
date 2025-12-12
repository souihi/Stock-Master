import streamlit as st
import pandas as pd
import io
import warnings

# --- CONFIGURATION ---
st.set_page_config(page_title="Comparateur Stock", layout="wide")
warnings.filterwarnings("ignore")

# --- CSS ---
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

# --- FONCTIONS ---
def nettoyer_lot(valeur):
    """Normalise les noms de lots"""
    if pd.isna(valeur): return "SANS_LOT"
    val = str(valeur).strip().upper()
    # Regroupement des variantes de recyclage sous 'STOCK'
    if val in ['STOCK+RECYCL0', 'RECYCL0', 'STOCK RECYCL0', 'STOCK+RECYCLO']:
        return 'STOCK'
    if val == '' or val == 'NAN': return "SANS_LOT"
    return val

def charger_fichier(file):
    try:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file, header=None, nrows=20)
        else:
            df = pd.read_excel(file, header=None, nrows=20)
        
        header_idx = 0
        for i, row in df.iterrows():
            row_str = row.astype(str).str.lower().str.cat(sep=' ')
            if 'code' in row_str and ('lot' in row_str or 'article' in row_str):
                header_idx = i
                break
        
        if file.name.endswith('.csv'):
            file.seek(0)
            df = pd.read_csv(file, header=header_idx)
        else:
            df = pd.read_excel(file, header=header_idx)
            
        df.columns = df.columns.astype(str).str.strip().str.lower()
        return df
    except:
        return None

def trouver_colonne(df, keywords):
    for col in df.columns:
        for k in keywords:
            if k in col: return col
    return None

def formatter_excel(df, writer, sheet_name):
    df.to_excel(writer, sheet_name=sheet_name, index=False)
    worksheet = writer.sheets[sheet_name]
    worksheet.set_column('A:A', 30) 
    worksheet.set_column('B:B', 70) # Libellé large
    worksheet.set_column('C:C', 30) 
    worksheet.set_column('D:F', 20) 

def formatter_excel_maj(df, writer, sheet_name):
    df.to_excel(writer, sheet_name=sheet_name, index=False)
    worksheet = writer.sheets[sheet_name]
    worksheet.set_column('A:A', 6) 
    worksheet.set_column('B:B', 8) 
    worksheet.set_column('C:C', 15) 
    worksheet.set_column('D:D', 15) 
    worksheet.set_column('E:E', 45)
    worksheet.set_column('F:F', 15)
    worksheet.set_column('G:G', 15)
    worksheet.set_column('H:H', 15)
    worksheet.set_column('I:I', 15)
    worksheet.set_column('J:J', 15)
    worksheet.set_column('K:K', 15)
# --- APPLICATION ---
st.title("Stock Master")

col_up1, col_up2 = st.columns(2)
with col_up1:
    f_terrain = st.file_uploader("Inventaire TERRAIN", type=["xlsx", "xls", "csv", "ods"], key="t_up")
with col_up2:
    f_info = st.file_uploader("Inventaire INFORMATIQUE", type=["xlsx", "xls", "csv", "ods"], key="i_up")

if f_terrain and f_info:
    df_t_raw = charger_fichier(f_terrain)
    df_i_raw = charger_fichier(f_info)

    if df_t_raw is not None and df_i_raw is not None:
        # Identification Colonnes
        tc_code = trouver_colonne(df_t_raw, ['code', 'article', 'ref'])
        tc_lot = trouver_colonne(df_t_raw, ['lot', 'serie', 'batch'])
        tc_qte = trouver_colonne(df_t_raw, ['qte', 'quant', 'stock'])
        tc_lib = trouver_colonne(df_t_raw, ['lib', 'designation', 'nom']) # On cherche aussi le libellé terrain au cas où
        
        ic_code = trouver_colonne(df_i_raw, ['code', 'article', 'ref'])
        ic_lot = trouver_colonne(df_i_raw, ['lot', 'serie', 'batch'])
        ic_qte = trouver_colonne(df_i_raw, ['qte', 'quant', 'stock'])
        ic_lib = trouver_colonne(df_i_raw, ['lib', 'designation', 'nom'])

        if not all([tc_code, tc_lot, tc_qte, ic_code, ic_lot, ic_qte]):
            st.error("Colonnes introuvables. Vérifiez les fichiers.")
            st.stop()

        # --- 1. NETTOYAGE & PRÉPARATION ---
        df_t = df_t_raw.copy()
        df_i = df_i_raw.copy()

        # Standardisation des codes (string + strip)
        df_t[tc_code] = df_t[tc_code].astype(str).str.strip()
        df_i[ic_code] = df_i[ic_code].astype(str).str.strip()

        # Nettoyage des lots
        df_t['Lot_Clean'] = df_t[tc_lot].apply(nettoyer_lot)
        df_i['Lot_Clean'] = df_i[ic_lot].apply(nettoyer_lot)

        # --- 2. CRÉATION DU DICTIONNAIRE MAÎTRE DES LIBELLÉS ---
        # C'est cette étape qui assure que le libellé est toujours trouvé
        lib_master = {}
        
        # A. On récupère d'abord ceux du terrain (backup)
        if tc_lib:
            temp_t = df_t[[tc_code, tc_lib]].dropna().drop_duplicates(subset=[tc_code])
            lib_master.update(dict(zip(temp_t[tc_code], temp_t[tc_lib])))
            
        # B. On écrase avec ceux de l'informatique (prioritaire)
        if ic_lib:
            temp_i = df_i[[ic_code, ic_lib]].dropna().drop_duplicates(subset=[ic_code])
            lib_master.update(dict(zip(temp_i[ic_code], temp_i[ic_lib])))

        # --- 3. AGRÉGATION DES QUANTITÉS ---
        t_agg = df_t.groupby([tc_code, 'Lot_Clean'])[tc_qte].sum().reset_index()
        t_agg.columns = ['Code', 'Lot', 'Qte_Terrain']

        i_agg = df_i.groupby([ic_code, 'Lot_Clean'])[ic_qte].sum().reset_index()
        i_agg.columns = ['Code', 'Lot', 'Qte_Info']

        # --- 4. FUSION ---
        merged = pd.merge(i_agg, t_agg, on=['Code', 'Lot'], how='outer')
        
        # Remplissage des 0 pour les quantités
        merged['Qte_Info'] = merged['Qte_Info'].fillna(0)
        merged['Qte_Terrain'] = merged['Qte_Terrain'].fillna(0)

        # --- 5. APPLICATION DES LIBELLÉS (LE FIX EST ICI) ---
        # On applique le nom en fonction du Code, peu importe d'où vient la ligne
        merged['Libellé'] = merged['Code'].map(lib_master).fillna("LIBELLÉ INCONNU")

        # Calcul Ecart
        merged['_Original_Info'] = merged['Qte_Info']
        merged['Ecart'] = merged['Qte_Info'] - merged['Qte_Terrain']

        # --- INTERFACE ---
        nb_ecarts = len(merged[merged['Ecart'] != 0])
        st.markdown(f'<div class="metric-box">⚠️ Nombre d\'articles avec écarts : {nb_ecarts}</div>', unsafe_allow_html=True)
        st.write("")

        st.info("Corrigez la colonne **'Qte Info (Logiciel)'** ci-dessous.")
        
        # Filtre d'affichage (seulement les écarts)
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

        # RECALCULS APRÈS MODIFICATION
        edited_df['Ecart_Final'] = edited_df['Qte_Info'] - edited_df['Qte_Terrain']
        changes = edited_df[edited_df['Qte_Info'] != edited_df['_Original_Info']]
        
        if not changes.empty:
            st.write("### Actions requises")
            for idx, row in changes.iterrows():
                st.markdown(f"""
                <div class="alert-box">
                    <b>{row['Code']} ({row['Libellé']})</b> :Veuillez mettre à jour votre stock informatique à <b>{int(row['Qte_Info'])}</b>.
                </div>
                """, unsafe_allow_html=True)
        
        st.divider()

        # --- EXPORTS ---
        c1, c2 = st.columns(2)

        with c1:
            st.subheader("1. Rapport d'Écarts")
            buffer_rapport = io.BytesIO()
            with pd.ExcelWriter(buffer_rapport, engine='xlsxwriter') as writer:
                # On exporte ce qui est affiché (donc les écarts)
                export_rpt = edited_df[['Code', 'Libellé', 'Lot', 'Qte_Terrain', 'Qte_Info', 'Ecart_Final']]
                formatter_excel(export_rpt, writer, "Rapport Ecarts")
            
            st.download_button("Télécharger Rapport", buffer_rapport, "Rapport_Ecarts.xlsx", mime="application/vnd.ms-excel", use_container_width=True)

        with c2:
            st.subheader("2. Fichier Final")
            st.caption("Génère l'inventaire complet au format du fichier informatique.")
            
            # CASE À COCHER DE CONFIRMATION
            confirm_update = st.checkbox("Je confirme vouloir générer le fichier de mise à jour complet", key="confirm_global")
            
            if confirm_update:
                # 1. ON RÉCUPÈRE TOUT LE MONDE (MERGE)
                # On part du dataframe complet 'merged'
                df_global = merged.copy()
                
                # On indexe pour faire la mise à jour facile
                df_global.set_index(['Code', 'Lot'], inplace=True)
                
                # On récupère les corrections faites dans l'éditeur (edited_df)
                df_corrections = edited_df.set_index(['Code', 'Lot'])
                
                # On met à jour les quantités dans le global avec celles de l'éditeur
                # (Cela ne touche que les lignes qui ont été modifiées/affichées)
                df_global.update(df_corrections[['Qte_Info']])
                
                df_global.reset_index(inplace=True)
                
                # 2. ON FILTRE LES 0 (On supprime les lignes à 0 comme demandé)
                df_valid_full = df_global[df_global['Qte_Info'] != 0].copy()
                
                # 3. ON REMET AU FORMAT FICHIER INFORMATIQUE D'ORIGINE
                # Préparation pour le mapping
                df_base = df_i_raw.copy()
                df_base['Code_Join'] = df_base[ic_code].astype(str).str.strip()
                df_base['Lot_Join'] = df_base[ic_lot].apply(nettoyer_lot)
                
                # Fusion pour récupérer les infos annexes (EAN, Emplacement...)
                df_final_rich = pd.merge(
                    df_valid_full, 
                    df_base, 
                    left_on=['Code', 'Lot'], 
                    right_on=['Code_Join', 'Lot_Join'], 
                    how='left', 
                    suffixes=('', '_base')
                )
                
                # Reconstruction des colonnes exactes
                df_export = pd.DataFrame()
                
                for col in df_i_raw.columns:
                    if col in ['Code_Join', 'Lot_Join', 'Lot_Clean']: continue
                    
                    # Si c'est la quantité -> On met la quantité validée (Info corrigée)
                    if col == ic_qte:
                        df_export[col] = df_final_rich['Qte_Info']
                    # Si c'est Code/Lot -> On met les versions nettoyées
                    elif col == ic_code:
                        df_export[col] = df_final_rich['Code']
                    elif col == ic_lot:
                        df_export[col] = df_final_rich['Lot']
                    # Sinon -> On remet la donnée d'origine
                    elif col in df_final_rich.columns:
                        df_export[col] = df_final_rich[col]
                    elif f"{col}_base" in df_final_rich.columns:
                         df_export[col] = df_final_rich[f"{col}_base"]
                    else:
                        df_export[col] = ""

                buffer_maj = io.BytesIO()
                with pd.ExcelWriter(buffer_maj, engine='xlsxwriter') as writer:
                    formatter_excel_maj(df_export, writer, "Inventaire_Complet")
                st.download_button(
                    "Mise à jour de l'inventaire terrain", 
                    buffer_maj, 
                    "Inventaire_terrain.xlsx", 
                    mime="application/vnd.ms-excel", 
                    type="primary", 
                    use_container_width=True
                )
            else:
                st.warning("Veuillez cocher la case pour générer le fichier.")

else:
    st.info("En attente des fichiers...")