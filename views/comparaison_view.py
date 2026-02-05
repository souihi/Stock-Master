import streamlit as st
from datetime import datetime
from components.atoms import display_metric_box

def render_comparaison_view(processor):   
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