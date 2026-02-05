import streamlit as st
from sqlalchemy import text

# Titre
st.title("🚧 Zone de Test BDD")

try:
    # On essaie de se connecter
    conn = st.connection("postgresql", type="sql")
    
    # Petite requête simple pour voir si la table Entreprise existe (créée via ton SQL)
    df = conn.query('SELECT * FROM "Entreprise"', ttl=0)
    
    st.success("✅ Connexion réussie à la Base de Données !")
    st.write("Contenu de la table Entreprise :")
    st.dataframe(df)

except Exception as e:
    st.error(f"❌ Erreur de connexion : {e}")
