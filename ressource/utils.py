import pandas as pd
import warnings
import streamlit as st

warnings.filterwarnings("ignore")

def formater_sans_decimale(valeur):
    """Formatte EAN/Série : enlève .0 et la notation scientifique (E+)"""
    if pd.isna(valeur) or valeur == "": 
        return ""
    
    txt = str(valeur).strip()
    
    # Cas de la notation scientifique
    if "E+" in txt.upper():
        try:
            txt_clean = txt.replace(',', '.')
            return "{:.0f}".format(float(txt_clean))
        except:
            pass 
            
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

def trouver_colonne(df, keywords):
    """Cherche une colonne contenant un des mots clés (insensible à la casse)"""
    # Nettoyage des noms de colonnes du DF pour la comparaison
    cols_normalized = {c: str(c).strip().lower() for c in df.columns}
    
    for col_original, col_lower in cols_normalized.items():
        for k in keywords:
            if k in col_lower: 
                return col_original
    return None

def charger_fichier_pandas(file):
    """Charge un fichier CSV ou Excel en détectant intelligemment l'en-tête"""
    try:
        # 1. On lit les 20 premières lignes pour "sniffer" l'en-tête
        if file.name.endswith('.csv'):
            df_preview = pd.read_csv(file, header=None, nrows=20)
        else:
            df_preview = pd.read_excel(file, header=None, nrows=20)
        
        header_idx = 0
        found = False
        
        # 2. On cherche la ligne qui contient "code" ET ("lot" ou "article" ou "désignation")
        for i, row in df_preview.iterrows():
            row_str = row.astype(str).str.lower().str.cat(sep=' ')
            # On assouplit la condition : juste "code" et "qte" ou "code" et "lot"
            if ('code' in row_str or 'article' in row_str) and ('qte' in row_str or 'quant' in row_str or 'stock' in row_str or 'lot' in row_str):
                header_idx = i
                found = True
                break
        
        # 3. On recharge le fichier avec le bon header
        file.seek(0) # IMPORTANT: Rembobiner le fichier
        
        if file.name.endswith('.csv'):
            df = pd.read_csv(file, header=header_idx)
        else:
            df = pd.read_excel(file, header=header_idx)
            
        # 4. On normalise les noms de colonnes (strip espaces)
        df.columns = df.columns.astype(str).str.strip()
        
        return df

    except Exception as e:
        st.error(f"Erreur lecture fichier : {e}")
        return None

def formatter_excel_simple(df, writer, sheet_name):
    df.to_excel(writer, sheet_name=sheet_name, index=False)
    worksheet = writer.sheets[sheet_name]
    worksheet.set_column('A:A', 30) 
    worksheet.set_column('B:B', 70) 
    worksheet.set_column('C:F', 20) 

def formatter_excel_maj(df, writer, sheet_name):
    df.to_excel(writer, sheet_name=sheet_name, index=False)
    worksheet = writer.sheets[sheet_name]
    worksheet.set_column('A:C', 15) 
    worksheet.set_column('D:D', 50)
    worksheet.set_column('E:Z', 15)