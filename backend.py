from abc import ABC, abstractmethod
import pandas as pd
import io
from utils import (formater_sans_decimale, nettoyer_lot, trouver_colonne, 
                   charger_fichier_pandas, formatter_excel_simple, formatter_excel_maj)

# --- CLASSE ABSTRAITE ---
class AbstractStockProcessor(ABC):
    
    @abstractmethod
    def load_data(self, file_terrain, file_info):
        pass

    @abstractmethod
    def process_comparison(self):
        pass

    @abstractmethod
    def generate_diff_report(self, edited_df):
        pass

    @abstractmethod
    def generate_final_update(self, edited_df, original_merged_df):
        pass

# --- IMPLEMENTATION---
class StockProcessor(AbstractStockProcessor):
    def __init__(self):
        self.df_t_raw = None
        self.df_i_raw = None
        self.col_map_t = {}
        self.col_map_i = {}

    def load_data(self, file_terrain, file_info):
        """Charge les fichiers et identifie les colonnes"""
        self.df_t_raw = charger_fichier_pandas(file_terrain)
        self.df_i_raw = charger_fichier_pandas(file_info)

        if self.df_t_raw is not None and self.df_i_raw is not None:
            # Identification Colonnes Terrain
            self.col_map_t = {
                'code': trouver_colonne(self.df_t_raw, ['code', 'article', 'ref']),
                'lot': trouver_colonne(self.df_t_raw, ['lot', 'serie', 'batch']),
                'qte': trouver_colonne(self.df_t_raw, ['qte', 'quant', 'stock']),
                'lib': trouver_colonne(self.df_t_raw, ['lib', 'designation', 'nom'])
            }
            # Identification Colonnes Info
            self.col_map_i = {
                'code': trouver_colonne(self.df_i_raw, ['code', 'article', 'ref']),
                'lot': trouver_colonne(self.df_i_raw, ['lot', 'serie', 'batch']),
                'qte': trouver_colonne(self.df_i_raw, ['qte', 'quant', 'stock']),
                'lib': trouver_colonne(self.df_i_raw, ['lib', 'designation', 'nom'])
            }

            # Vérification minimale
            required = [self.col_map_t['code'], self.col_map_t['lot'], self.col_map_t['qte'],
                        self.col_map_i['code'], self.col_map_i['lot'], self.col_map_i['qte']]
            
            return all(required)
        return False

    def process_comparison(self):
        """Exécute la logique de nettoyage et de fusion"""
        df_t = self.df_t_raw.copy()
        df_i = self.df_i_raw.copy()
        
        tc_code, ic_code = self.col_map_t['code'], self.col_map_i['code']
        tc_lot, ic_lot = self.col_map_t['lot'], self.col_map_i['lot']
        tc_qte, ic_qte = self.col_map_t['qte'], self.col_map_i['qte']
        tc_lib, ic_lib = self.col_map_t['lib'], self.col_map_i['lib']

        # Standardisation
        df_t[tc_code] = df_t[tc_code].apply(formater_sans_decimale)
        df_i[ic_code] = df_i[ic_code].apply(formater_sans_decimale)
        df_t['Lot_Clean'] = df_t[tc_lot].apply(nettoyer_lot)
        df_i['Lot_Clean'] = df_i[ic_lot].apply(nettoyer_lot)

        # Dictionnaire Libellés
        lib_master = {}
        if tc_lib:
            temp = df_t[[tc_code, tc_lib]].dropna().drop_duplicates(subset=[tc_code])
            lib_master.update(dict(zip(temp[tc_code], temp[tc_lib])))
        if ic_lib:
            temp = df_i[[ic_code, ic_lib]].dropna().drop_duplicates(subset=[ic_code])
            lib_master.update(dict(zip(temp[ic_code], temp[ic_lib])))

        # Agrégation
        t_agg = df_t.groupby([tc_code, 'Lot_Clean'])[tc_qte].sum().reset_index()
        t_agg.columns = ['Code', 'Lot', 'Qte_Terrain']
        i_agg = df_i.groupby([ic_code, 'Lot_Clean'])[ic_qte].sum().reset_index()
        i_agg.columns = ['Code', 'Lot', 'Qte_Info']

        # Fusion
        merged = pd.merge(i_agg, t_agg, on=['Code', 'Lot'], how='outer')
        merged[['Qte_Info', 'Qte_Terrain']] = merged[['Qte_Info', 'Qte_Terrain']].fillna(0)
        
        merged['Libellé'] = merged['Code'].map(lib_master).fillna("LIBELLÉ INCONNU")
        merged['_Original_Info'] = merged['Qte_Info']
        merged['Ecart'] = merged['Qte_Info'] - merged['Qte_Terrain']
        
        return merged

    def generate_diff_report(self, edited_df):
        """Génère le fichier Excel simple des écarts"""
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            export_rpt = edited_df[['Code', 'Libellé', 'Lot', 'Qte_Terrain', 'Qte_Info', 'Ecart_Final']]
            formatter_excel_simple(export_rpt, writer, "Rapport Ecarts")
        return buffer

    def generate_final_update(self, edited_df, original_merged_df):
        """Logique complexe de reconstruction du fichier final"""
        # 1. Mise à jour globale
        df_global = original_merged_df.copy()
        df_global.set_index(['Code', 'Lot'], inplace=True)
        df_corrections = edited_df.set_index(['Code', 'Lot'])
        df_global.update(df_corrections[['Qte_Info']])
        df_global.reset_index(inplace=True)
        
        df_valid_full = df_global[df_global['Qte_Info'] != 0].copy()

        # 2. Identification Metadata
        def find_i(keys): return trouver_colonne(self.df_i_raw, keys)
        def find_t(keys): return trouver_colonne(self.df_t_raw, keys)

        # Mapping des colonnes avancées
        cols_meta = {
            'ean': (find_i(['ean', 'code_barre']), find_t(['ean', 'code_barre'])),
            'ser': (find_i(['serie', 'serial', 's/n']), find_t(['serie', 'serial'])),
            'emp': (find_i(['emplacement', 'rack']), find_t(['emplacement', 'rack'])),
            'site': (find_i(['site', 'magasin']), find_t(['site', 'magasin'])),
            'um': (find_i(['um', 'unite']), find_t(['um', 'unite'])),
            'res': find_i(['reserve', 'réserv']),
            'dispo': find_i(['dispo', 'utilisable'])
        }

        # 3. Préparation Bases (Info & Terrain)
        df_base = self.df_i_raw.copy()
        df_base['Code_Join'] = df_base[self.col_map_i['code']].apply(formater_sans_decimale)
        df_base['Lot_Join'] = df_base[self.col_map_i['lot']].apply(nettoyer_lot)
        
        # Nettoyage EAN/Series dans la base
        if cols_meta['ean'][0]: df_base[cols_meta['ean'][0]] = df_base[cols_meta['ean'][0]].apply(formater_sans_decimale)
        if cols_meta['ser'][0]: df_base[cols_meta['ser'][0]] = df_base[cols_meta['ser'][0]].apply(formater_sans_decimale)
        
        df_base = df_base.drop_duplicates(subset=['Code_Join', 'Lot_Join'])

        df_backup = self.df_t_raw.copy()
        df_backup['Code_Join'] = df_backup[self.col_map_t['code']].apply(formater_sans_decimale)
        df_backup['Lot_Join'] = df_backup[self.col_map_t['lot']].apply(nettoyer_lot)
        
        if cols_meta['ean'][1]: df_backup[cols_meta['ean'][1]] = df_backup[cols_meta['ean'][1]].apply(formater_sans_decimale)
        if cols_meta['ser'][1]: df_backup[cols_meta['ser'][1]] = df_backup[cols_meta['ser'][1]].apply(formater_sans_decimale)
        
        df_backup = df_backup.drop_duplicates(subset=['Code_Join', 'Lot_Join'])

        # 4. Fusion Riche
        df_step1 = pd.merge(df_valid_full, df_base, left_on=['Code', 'Lot'], right_on=['Code_Join', 'Lot_Join'], how='left', suffixes=('', '_info'))
        df_final_rich = pd.merge(df_step1, df_backup, left_on=['Code', 'Lot'], right_on=['Code_Join', 'Lot_Join'], how='left', suffixes=('', '_terr'))

        # 5. Reconstruction colonne par colonne
        df_export = pd.DataFrame()
        default_site = ""
        if cols_meta['site'][0] and not df_base[cols_meta['site'][0]].dropna().empty:
            default_site = df_base[cols_meta['site'][0]].mode()[0]

        for col in self.df_i_raw.columns:
            if col in ['Code_Join', 'Lot_Join', 'Lot_Clean']: continue
            
            # Mapping direct des valeurs calculées
            if col == self.col_map_i['code']: df_export[col] = df_final_rich['Code']
            elif col == self.col_map_i['lot']: df_export[col] = df_final_rich['Lot']
            elif col == self.col_map_i['qte']: df_export[col] = df_final_rich['Qte_Info']
            elif col == self.col_map_i['lib']: df_export[col] = df_final_rich['Libellé']
            elif cols_meta['dispo'] and col == cols_meta['dispo']: df_export[col] = df_final_rich['Qte_Info']
            
            # Logique de fallback (Info -> Terrain -> Vide)
            elif cols_meta['ean'][0] and col == cols_meta['ean'][0]:
                df_export[col] = df_final_rich[col].fillna(df_final_rich.get(f"{cols_meta['ean'][1]}_terr")).fillna("")
            
            elif cols_meta['site'][0] and col == cols_meta['site'][0]:
                df_export[col] = df_final_rich[col].fillna(df_final_rich.get(f"{cols_meta['site'][1]}_terr")).fillna(default_site)
            
            # Gestion générique des autres colonnes
            else:
                if col in df_final_rich.columns:
                    df_export[col] = df_final_rich[col]
                elif f"{col}_info" in df_final_rich.columns:
                    df_export[col] = df_final_rich[f"{col}_info"]
                else:
                    df_export[col] = ""

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            formatter_excel_maj(df_export, writer, "Inventaire_Complet")
        
        return buffer

    def search_item(self, df_source, query):
        """
        Cherche un article par Code, EAN ou Série.
        Retourne la ligne correspondante (Series) ou None.
        """
        if df_source is None or not query:
            return None
            
        q = str(query).strip().upper()
        
        # On définit les colonnes où chercher
        cols_to_search = []
        
        # On récupère les noms de colonnes identifiés lors du chargement
        keys_to_check = ['code', 'ean', 'serie'] # clés internes mapping
        
        
        for col in df_source.columns:
            col_str = str(col).upper()
            pass

        mask = pd.Series(False, index=df_source.index)
        
        for col in df_source.columns:
            try:
                col_normalized = df_source[col].astype(str).str.strip().str.upper()
                mask = mask | (col_normalized == q)
            except:
                pass
        
        results = df_source[mask]
        
        if not results.empty:
            return results.iloc[0]
        return None