import pandas as pd
import warnings

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
    """Cherche une colonne contenant un des mots clés"""
    for col in df.columns:
        for k in keywords:
            if k in col: return col
    return None

def charger_fichier_pandas(file):
    """Charge un fichier CSV ou Excel en détectant l'en-tête"""
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
    except Exception as e:
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