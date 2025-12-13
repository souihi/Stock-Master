import streamlit as st
import pandas as pd
import io
import warnings
from datetime import datetime
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
def formater_sans_decimale(valeur):
    """Formatte EAN/Série : enlève .0 et la notation scientifique (E+)"""
    if pd.isna(valeur) or valeur == "": 
        return ""
    
    # Conversion en chaine
    txt = str(valeur).strip()
    
    # Cas de la notation scientifique (ex: 3,41E+12 ou 3.41E+12)
    if "E+" in txt.upper():
        try:
            # On remplace la virgule par un point pour que Python comprenne
            txt_clean = txt.replace(',', '.')
            return "{:.0f}".format(float(txt_clean))
        except:
            pass # Si erreur, on rend le texte tel quel
            
    # Cas du .0 à la fin
    if txt.endswith('.0'):
        return txt[:-2]
        
    return txt
def nettoyer_lot(valeur):
    """Normalise les noms de lots"""
    if pd.isna(valeur): return "SANS_LOT"
    val = str(valeur).strip().upper()
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
    worksheet.set_column('B:B', 70) 
    worksheet.set_column('C:C', 30) 
    worksheet.set_column('D:F', 20) 

def formatter_excel_maj(df, writer, sheet_name):
    df.to_excel(writer, sheet_name=sheet_name, index=False)
    worksheet = writer.sheets[sheet_name]
    worksheet.set_column('A:A', 15) 
    worksheet.set_column('B:B', 15) 
    worksheet.set_column('C:C', 15) 
    worksheet.set_column('D:D', 50) # Libellé large
    worksheet.set_column('E:Z', 15)

# --- APPLICATION ---
st.title("Stock Master")

col_up1, col_up2 = st.columns(2)
with col_up1:
    f_terrain = st.file_uploader("Inventaire TERRAIN", type=["xlsx", "xls", "csv", "ods", "xlsm"], key="t_up")
with col_up2:
    f_info = st.file_uploader("Inventaire INFORMATIQUE", type=["xlsx", "xls", "csv", "ods", "xlsm"], key="i_up")

if f_terrain and f_info:
    df_t_raw = charger_fichier(f_terrain)
    df_i_raw = charger_fichier(f_info)

    if df_t_raw is not None and df_i_raw is not None:
        # Identification Colonnes
        tc_code = trouver_colonne(df_t_raw, ['code', 'article', 'ref'])
        tc_lot = trouver_colonne(df_t_raw, ['lot', 'serie', 'batch'])
        tc_qte = trouver_colonne(df_t_raw, ['qte', 'quant', 'stock'])
        tc_lib = trouver_colonne(df_t_raw, ['lib', 'designation', 'nom'])
        
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

        # Standardisation des codes
        df_t[tc_code] = df_t[tc_code].apply(formater_sans_decimale)
        df_i[ic_code] = df_i[ic_code].apply(formater_sans_decimale)

        # Nettoyage des lots
        df_t['Lot_Clean'] = df_t[tc_lot].apply(nettoyer_lot)
        df_i['Lot_Clean'] = df_i[ic_lot].apply(nettoyer_lot)

        # --- 2. DICTIONNAIRE MAÎTRE DES LIBELLÉS ---
        lib_master = {}
        if tc_lib:
            temp_t = df_t[[tc_code, tc_lib]].dropna().drop_duplicates(subset=[tc_code])
            lib_master.update(dict(zip(temp_t[tc_code], temp_t[tc_lib])))
        if ic_lib:
            temp_i = df_i[[ic_code, ic_lib]].dropna().drop_duplicates(subset=[ic_code])
            lib_master.update(dict(zip(temp_i[ic_code], temp_i[ic_lib])))

        # --- 3. AGRÉGATION ---
        t_agg = df_t.groupby([tc_code, 'Lot_Clean'])[tc_qte].sum().reset_index()
        t_agg.columns = ['Code', 'Lot', 'Qte_Terrain']

        i_agg = df_i.groupby([ic_code, 'Lot_Clean'])[ic_qte].sum().reset_index()
        i_agg.columns = ['Code', 'Lot', 'Qte_Info']

        # --- 4. FUSION ---
        merged = pd.merge(i_agg, t_agg, on=['Code', 'Lot'], how='outer')
        merged['Qte_Info'] = merged['Qte_Info'].fillna(0)
        merged['Qte_Terrain'] = merged['Qte_Terrain'].fillna(0)

        # --- 5. APPLICATION LIBELLÉS ---
        merged['Libellé'] = merged['Code'].map(lib_master).fillna("LIBELLÉ INCONNU")

        merged['_Original_Info'] = merged['Qte_Info']
        merged['Ecart'] = merged['Qte_Info'] - merged['Qte_Terrain']

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
            buffer_rapport = io.BytesIO()
            with pd.ExcelWriter(buffer_rapport, engine='xlsxwriter') as writer:
                export_rpt = edited_df[['Code', 'Libellé', 'Lot', 'Qte_Terrain', 'Qte_Info', 'Ecart_Final']]
                formatter_excel(export_rpt, writer, "Rapport Ecarts")
                date_str = datetime.now().strftime("%d-%m-%Y_%Hh%M")
                nom_fichier_rapport = f"Rapport_Ecarts_{date_str}.xlsx"
            st.download_button("Télécharger Rapport", buffer_rapport, nom_fichier_rapport, mime="application/vnd.ms-excel", use_container_width=True)

    with c2:
            st.subheader("2. Fichier Final")
            st.caption("Génère l'inventaire complet au format du fichier informatique.")
            
            confirm_update = st.checkbox("Je confirme vouloir générer le fichier de mise à jour complet", key="confirm_global")
            
            if confirm_update:
                # 1. Mise à jour des quantités (Global)
                df_global = merged.copy()
                df_global.set_index(['Code', 'Lot'], inplace=True)
                df_corrections = edited_df.set_index(['Code', 'Lot'])
                df_global.update(df_corrections[['Qte_Info']])
                df_global.reset_index(inplace=True)
                
                # 2. On garde les lignes valides (!= 0)
                df_valid_full = df_global[df_global['Qte_Info'] != 0].copy()
                
                # 3. IDENTIFICATION DES COLONNES METADATA
                col_ean_i = trouver_colonne(df_i_raw, ['ean', 'code_barre', 'gencod'])
                col_ser_i = trouver_colonne(df_i_raw, ['serie', 'serial', 's/n'])
                col_emp_i = trouver_colonne(df_i_raw, ['emplacement', 'rack', 'allee', 'localisation'])
                col_site_i = trouver_colonne(df_i_raw, ['site', 'magasin', 'depot'])
                col_res_i = trouver_colonne(df_i_raw, ['reserve', 'réserv', 'alloue'])
                # --- AJOUT DES NOUVELLES COLONNES ---
                col_dispo_i = trouver_colonne(df_i_raw, ['dispo', 'utilisable']) 
                col_um_i = trouver_colonne(df_i_raw, ['um', 'unite', 'uom'])

                col_ean_t = trouver_colonne(df_t_raw, ['ean', 'code_barre', 'gencod'])
                col_ser_t = trouver_colonne(df_t_raw, ['serie', 'serial', 's/n'])
                col_emp_t = trouver_colonne(df_t_raw, ['emplacement', 'rack', 'allee', 'localisation'])
                col_site_t = trouver_colonne(df_t_raw, ['site', 'magasin', 'depot'])
                col_um_t = trouver_colonne(df_t_raw, ['um', 'unite', 'uom']) # On cherche l'UM terrain aussi

                # 4. PRÉPARATION DE LA BASE INFORMATIQUE
                df_base = df_i_raw.copy()
                df_base['Code_Join'] = df_base[ic_code].apply(formater_sans_decimale)
                df_base['Lot_Join'] = df_base[ic_lot].apply(nettoyer_lot)
                
                if col_ean_i: df_base[col_ean_i] = df_base[col_ean_i].apply(formater_sans_decimale)
                if col_ser_i: df_base[col_ser_i] = df_base[col_ser_i].apply(formater_sans_decimale)

                # Anti-doublon essentiel
                df_base = df_base.drop_duplicates(subset=['Code_Join', 'Lot_Join'])

                # 5. PRÉPARATION DE LA BASE TERRAIN (Secours)
                df_backup = df_t_raw.copy()
                df_backup['Code_Join'] = df_backup[tc_code].apply(formater_sans_decimale)
                df_backup['Lot_Join'] = df_backup[tc_lot].apply(nettoyer_lot)
                
                if col_ean_t: df_backup[col_ean_t] = df_backup[col_ean_t].apply(formater_sans_decimale)
                if col_ser_t: df_backup[col_ser_t] = df_backup[col_ser_t].apply(formater_sans_decimale)

                df_backup = df_backup.drop_duplicates(subset=['Code_Join', 'Lot_Join'])

                # 6. FUSION ROBUSTE
                df_step1 = pd.merge(
                    df_valid_full, 
                    df_base, 
                    left_on=['Code', 'Lot'], 
                    right_on=['Code_Join', 'Lot_Join'], 
                    how='left', 
                    suffixes=('', '_info')
                )
                
                df_final_rich = pd.merge(
                    df_step1, 
                    df_backup, 
                    left_on=['Code', 'Lot'], 
                    right_on=['Code_Join', 'Lot_Join'], 
                    how='left', 
                    suffixes=('', '_terr')
                )

                # 7. RECONSTRUCTION DU FICHIER FINAL
                df_export = pd.DataFrame()
                
                default_site = ""
                if col_site_i and not df_base[col_site_i].dropna().empty:
                    default_site = df_base[col_site_i].mode()[0]

                for col in df_i_raw.columns:
                    if col in ['Code_Join', 'Lot_Join', 'Lot_Clean']: continue
                    
                    # A. Clés principales
                    if col == ic_code:
                        df_export[col] = df_final_rich['Code']
                    elif col == ic_lot:
                        df_export[col] = df_final_rich['Lot']
                    elif col == ic_qte:
                        df_export[col] = df_final_rich['Qte_Info']
                    elif col == ic_lib:
                        df_export[col] = df_final_rich['Libellé']

                    # B. QUANTITÉ DISPONIBLE (NEW) -> Egale au stock
                    elif col_dispo_i and col == col_dispo_i:
                         # On applique simplement la quantité stock validée
                         df_export[col] = df_final_rich['Qte_Info']

                    # C. UNITÉ DE MESURE (NEW) -> Info sinon Terrain
                    elif col_um_i and col == col_um_i:
                        val_i = df_final_rich[col] if col in df_final_rich.columns else pd.NA
                        val_t = df_final_rich[col_um_t + '_terr'] if col_um_t and (col_um_t + '_terr') in df_final_rich.columns else pd.NA
                        # Si vide, on met 'pcs' par défaut ou vide
                        df_export[col] = val_i.fillna(val_t).fillna("")

                    # D. EAN & SERIE
                    elif col_ean_i and col == col_ean_i:
                        val_i = df_final_rich[col] if col in df_final_rich.columns else pd.NA
                        val_t = df_final_rich[col_ean_t + '_terr'] if col_ean_t and (col_ean_t + '_terr') in df_final_rich.columns else pd.NA
                        df_export[col] = val_i.fillna(val_t).fillna("")
                        
                    elif col_ser_i and col == col_ser_i:
                        val_i = df_final_rich[col] if col in df_final_rich.columns else pd.NA
                        val_t = df_final_rich[col_ser_t + '_terr'] if col_ser_t and (col_ser_t + '_terr') in df_final_rich.columns else pd.NA
                        df_export[col] = val_i.fillna(val_t).fillna("")

                    # E. EMPLACEMENT
                    elif col_emp_i and col == col_emp_i:
                        val_i = df_final_rich[col] if col in df_final_rich.columns else pd.NA
                        val_t = df_final_rich[col_emp_t + '_terr'] if col_emp_t and (col_emp_t + '_terr') in df_final_rich.columns else pd.NA
                        df_export[col] = val_i.fillna(val_t).fillna("")

                    # F. SITE
                    elif col_site_i and col == col_site_i:
                        val_i = df_final_rich[col] if col in df_final_rich.columns else pd.NA
                        val_t = df_final_rich[col_site_t + '_terr'] if col_site_t and (col_site_t + '_terr') in df_final_rich.columns else pd.NA
                        df_export[col] = val_i.fillna(val_t).fillna(default_site)

                    # G. QUANTITE RESERVEE
                    elif col_res_i and col == col_res_i:
                        if col in df_final_rich.columns:
                            df_export[col] = df_final_rich[col].fillna(0)
                        elif f"{col}_info" in df_final_rich.columns:
                             df_export[col] = df_final_rich[f"{col}_info"].fillna(0)
                        else:
                            df_export[col] = 0

                    # H. LE RESTE
                    else:
                        if col in df_final_rich.columns:
                            df_export[col] = df_final_rich[col]
                        elif f"{col}_info" in df_final_rich.columns:
                             df_export[col] = df_final_rich[f"{col}_info"]
                        else:
                            df_export[col] = ""

                buffer_maj = io.BytesIO()
                with pd.ExcelWriter(buffer_maj, engine='xlsxwriter') as writer:
                    formatter_excel_maj(df_export, writer, "Inventaire_Complet")
                
                date_str = datetime.now().strftime("%d-%m-%Y_%Hh%M")
                nom_fichier_final = f"Inventaire_Base_{date_str}.xlsx"
                
                st.download_button(
                    "Mise à jour de l'inventaire terrain", 
                    buffer_maj, 
                    nom_fichier_final, 
                    mime="application/vnd.ms-excel", 
                    type="primary", 
                    use_container_width=True
                )
            else:
                st.warning("Veuillez cocher la case pour générer le fichier.")
else:
     st.info("En attente des fichiers...")