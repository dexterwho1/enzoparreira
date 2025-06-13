import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = "crm_data.db"

# --- Données fictives si la table clients est vide ---
with sqlite3.connect(DB_PATH) as conn:
    c = conn.cursor()
    nb_clients = c.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
    if nb_clients == 0:
        prospects = c.execute("SELECT * FROM prospects").fetchall()
        for p in prospects:
            place_id, name, website, phone, emails, main_category, categories, reviews, rating, address, horaires, link, featured_reviews, is_spending_on_ads, query, statut_appel, date_dernier_appel, meta_appel = p
            c.execute("""
                INSERT INTO clients (place_id, name, phone, address, date_conversion, last_contact)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                place_id,
                name + " (fictif)",
                phone,
                address,
                datetime.now().strftime("%Y-%m-%d"),
                datetime.now().strftime("%Y-%m-%d")
            ))
            client_id = c.lastrowid
            c.execute("""
                INSERT INTO commandes (client_id, prestation, prix, recurrence, date_debut, date_fin, argent_encaisse, statut)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                client_id,
                main_category or "Service fictif",
                100.0,
                "1 mois",
                datetime.now().strftime("%Y-%m-%d"),
                datetime.now().strftime("%Y-%m-%d"),
                0.0,
                "livré"
            ))
        conn.commit()

st.title("Liste des clients")

# --- Ajout manuel de client ---
st.header("Ajouter un client manuellement")
with st.form("ajout_client_form"):
    nom = st.text_input("Nom *", "")
    telephone = st.text_input("Téléphone *", "")
    adresse = st.text_input("Adresse *", "")
    recurrence = st.selectbox("Récurrence", ["Non", "2 semaines", "1 mois"])
    deliverabilite = st.selectbox("Délivrabilité", ["Délivrabilité", "Tout livré", "Non livré"])
    date_debut = st.date_input("Date de début du contrat *", value=datetime.now())
    date_delivrabilite = st.date_input("Date de délivrabilité *", value=datetime.now())
    prix = st.number_input("Prix *", min_value=0.0, step=10.0)
    encaisse = st.number_input("Argent encaissé (optionnel)", min_value=0.0, step=10.0, value=0.0)
    submitted = st.form_submit_button("Ajouter")
    if submitted:
        if not (nom and telephone and adresse and prix and date_debut and date_delivrabilite):
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
                    date_debut.strftime("%Y-%m-%d"),
                    date_debut.strftime("%Y-%m-%d")
                ))
                client_id = c.lastrowid
                c.execute("""
                    INSERT INTO commandes (client_id, prestation, prix, recurrence, date_debut, date_fin, argent_encaisse, statut)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    client_id,
                    "Service manuel",
                    prix,
                    recurrence if recurrence != "Non" else None,
                    date_debut.strftime("%Y-%m-%d"),
                    date_delivrabilite.strftime("%Y-%m-%d"),
                    encaisse,
                    deliverabilite if deliverabilite != "Délivrabilité" else None
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
    st.warning("Aucun client trouvé dans la base, même après insertion fictive. Ajoutez des prospects ou vérifiez la base.")
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
        # Ajout d'un bouton unique par client
        voir_key = f"voir_{client_id}"
        if st.button("Voir", key=voir_key):
            st.session_state['show_client_details'] = client_id
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
            "En savoir plus": st.session_state.get('show_client_details', None) == client_id
        })
    st.dataframe(pd.DataFrame([{k: v if k != 'En savoir plus' else 'Voir' for k, v in row.items()} for row in table]))

    # Affichage des détails dans la sidebar
    show_client_details = st.session_state.get('show_client_details', None)
    if show_client_details:
        client_row = df[df['client_id'] == show_client_details].iloc[0]
        st.sidebar.subheader(f"Détails pour {client_row['name']}")
        st.sidebar.markdown(f"**Téléphone :** {client_row['phone']}")
        st.sidebar.markdown(f"**Adresse :** {client_row['address']}")
        st.sidebar.markdown(f"**Dernier contact :** {client_row['last_contact'] if 'last_contact' in client_row else '-'}")
        st.sidebar.markdown(f"**Date conversion :** {client_row['date_conversion'] if 'date_conversion' in client_row else '-'}")
        # Si le client a un place_id, on va chercher les infos du prospect
        if 'place_id' in client_row and client_row['place_id']:
            with sqlite3.connect(DB_PATH) as conn:
                prospect = pd.read_sql_query("SELECT * FROM prospects WHERE place_id = ?", conn, params=(client_row['place_id'],))
                if not prospect.empty:
                    p = prospect.iloc[0]
                    st.sidebar.markdown(f"**Catégorie :** {p['main_category']}")
                    st.sidebar.markdown(f"**Site web :** {'[Site](' + p['website'] + ')' if p['website'] else 'Non dispo'}")
                    st.sidebar.markdown(f"**Email :** {'[Email](mailto:' + p['emails'] + ')' if p['emails'] else 'Non dispo'}")
                    st.sidebar.markdown(f"**Lien Google Maps :** {'[Maps](' + p['link'] + ')' if p['link'] else 'Non dispo'}")
                    st.sidebar.markdown(f"**Avis :** {p['reviews']} | **Note :** {p['rating']}")
        if st.sidebar.button("Fermer", key="close_client_details"):
            st.session_state['show_client_details'] = None
            st.rerun() 