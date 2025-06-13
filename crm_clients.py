import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = "crm_data.db"

st.title("Liste des clients")

# --- Ajout manuel de client ---
st.header("Ajouter un client manuellement")
with st.form("ajout_client_form"):
    nom = st.text_input("Nom *", "")
    telephone = st.text_input("Téléphone *", "")
    adresse = st.text_input("Adresse *", "")
    recurrence = st.selectbox("Récurrence", ["Non", "2 semaines", "1 mois"])
    deliverabilite = st.selectbox("Délivrabilité", ["Délivrabilité", "Tout livré", "Non livré"])
    submitted = st.form_submit_button("Ajouter")
    if submitted:
        if not (nom and telephone and adresse):
            st.error("Merci de remplir tous les champs obligatoires.")
        else:
            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO clients (name, phone, address, date_conversion, last_contact)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    nom,
                    telephone,
                    adresse,
                    datetime.now().strftime("%Y-%m-%d"),
                    datetime.now().strftime("%Y-%m-%d")
                ))
                conn.commit()
            st.success("Client ajouté avec succès !")
            st.rerun()

# --- Filtres ---
st.header("Liste des clients")
col1, col2, col3, col4, col5 = st.columns([2,2,2,1,1])
with col1:
    filtre_nom = st.text_input("Recherche nom...")
with col2:
    filtre_tel = st.text_input("Recherche téléphone...")
with col3:
    filtre_adr = st.text_input("Recherche adresse...")
with col4:
    filtre_rec = st.selectbox("Récurrence", ["", "Non", "2 semaines", "1 mois"])
with col5:
    filtre_deliv = st.selectbox("Délivrabilité", ["", "Tout livré", "Non livré"])

# --- Récupération des clients ---
with sqlite3.connect(DB_PATH) as conn:
    df = pd.read_sql_query("SELECT * FROM clients", conn)
    commandes = pd.read_sql_query("SELECT * FROM commandes", conn)

# --- Application des filtres ---
if filtre_nom:
    df = df[df['name'].str.contains(filtre_nom, case=False, na=False)]
if filtre_tel:
    df = df[df['phone'].str.contains(filtre_tel, case=False, na=False)]
if filtre_adr:
    df = df[df['address'].str.contains(filtre_adr, case=False, na=False)]
if filtre_rec:
    # On suppose que la récurrence est stockée dans la table commandes
    rec_clients = commandes[commandes['recurrence'] == filtre_rec]['client_id'].unique()
    df = df[df['client_id'].isin(rec_clients)]
if filtre_deliv:
    # On suppose que la délivrabilité est stockée dans la table commandes (statut)
    if filtre_deliv == "Tout livré":
        deliv_clients = commandes[commandes['statut'] == 'livré']['client_id'].unique()
        df = df[df['client_id'].isin(deliv_clients)]
    elif filtre_deliv == "Non livré":
        deliv_clients = commandes[commandes['statut'] != 'livré']['client_id'].unique()
        df = df[df['client_id'].isin(deliv_clients)]

# --- Affichage du tableau ---
if df.empty:
    st.info("Aucun client trouvé.")
else:
    st.write("")
    st.subheader("")
    table = []
    for _, row in df.iterrows():
        client_id = row['client_id']
        # Commandes du client
        prestations = commandes[commandes['client_id'] == client_id]['prestation'].tolist()
        # À encaisser et facturé (placeholders)
        a_encaisser = 0
        facture = 0
        # Dernier contact (placeholder)
        dernier_contact = row['last_contact'] if 'last_contact' in row else "-"
        # Coût par heure (placeholder)
        cout_heure = "-"
        table.append({
            "Nom": row['name'],
            "Téléphone": row['phone'],
            "Adresse": row['address'],
            "Dernier contact": dernier_contact,
            "Récurrence": ', '.join(set(commandes[commandes['client_id'] == client_id]['recurrence'].dropna().astype(str).tolist())),
            "À encaisser": a_encaisser,
            "Facturé": facture,
            "Coût par heure": cout_heure,
            "Commandes": ', '.join(prestations),
            "En savoir plus": "Voir"
        })
    st.dataframe(pd.DataFrame(table)) 