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
                INSERT INTO commandes (client_id, nom_service, prestation, prix, recurrence, date_debut, date_fin, argent_encaisse, statut)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                client_id,
                main_category or "Service fictif",
                "Description du service fictif",
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
                    INSERT INTO commandes (client_id, nom_service, prestation, prix, recurrence, date_debut, date_fin, argent_encaisse, statut)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    client_id,
                    "Service manuel",
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
    # En-têtes du tableau
    headers = [
        "Nom", "Téléphone", "Adresse", "Dernier contact", "Récurrence", "À encaisser", "Facturé", "Coût par heure", "Commandes", "En savoir plus"
    ]
    col_widths = [2,1.2,2,1.2,1,1,1,1,2,1]
    header_cols = st.columns(col_widths)
    for i, h in enumerate(headers):
        header_cols[i].markdown(f"**{h}**")
    # Affichage des lignes
    for _, row in df.iterrows():
        client_id = row['client_id']
        prestations = ', '.join(commandes[commandes['client_id'] == client_id]['nom_service'].tolist())
        dernier_contact = row['last_contact'] if 'last_contact' in row else "-"
        cout_heure = "-"
        a_encaisser = "0"
        facture = "0"
        rec = ', '.join(set(commandes[commandes['client_id'] == client_id]['recurrence'].dropna().astype(str).tolist()))
        line_cols = st.columns(col_widths)
        line_cols[0].write(row['name'])
        line_cols[1].write(row['phone'])
        line_cols[2].write(row['address'])
        line_cols[3].write(dernier_contact)
        line_cols[4].write(rec)
        line_cols[5].write(a_encaisser)
        line_cols[6].write(facture)
        line_cols[7].write(cout_heure)
        line_cols[8].write(prestations)
        voir_key = f"voir_{client_id}"
        if line_cols[9].button("Voir", key=voir_key):
            st.session_state['show_client_details'] = client_id
    # Affichage des détails dans la sidebar
    show_client_details = st.session_state.get('show_client_details', None)
    if show_client_details:
        client_row = df[df['client_id'] == show_client_details].iloc[0]
        st.sidebar.subheader(f"Détails pour {client_row.get('name', 'Non renseigné')}")
        st.sidebar.markdown(f"**Téléphone :** {client_row.get('phone', 'Non renseigné')}")
        st.sidebar.markdown(f"**Adresse :** {client_row.get('address', 'Non renseigné')}")
        st.sidebar.markdown(f"**Dernier contact :** {client_row.get('last_contact', 'Non renseigné')}")
        st.sidebar.markdown(f"**Date conversion :** {client_row.get('date_conversion', 'Non renseigné')}")
        
        # Commandes du client
        client_commandes = commandes[commandes['client_id'] == show_client_details]
        if not client_commandes.empty:
            st.sidebar.markdown("**Commandes :**")
            for _, cmd in client_commandes.iterrows():
                statut = cmd.get('statut', 'En cours')
                statut_color = 'green' if statut == 'livré' else 'orange'
                st.sidebar.markdown(f"• **{cmd.get('nom_service', 'Sans nom')}** - {cmd.get('prix', 0)}€ - <span style='color:{statut_color}'>{statut}</span>", unsafe_allow_html=True)
                if cmd.get('prestation'):
                    st.sidebar.markdown(f"  *{cmd.get('prestation')}*")
                st.sidebar.markdown(f"  Du {cmd.get('date_debut')} au {cmd.get('date_fin')}")
        else:
            st.sidebar.markdown("**Aucune commande**")
        
        # Informations prospect (si applicable)
        if client_row.get('place_id'):
            cat = client_row.get('main_category', None)
            site = client_row.get('website', None)
            email = client_row.get('emails', None)
            link = client_row.get('link', None)
            avis = client_row.get('reviews', None)
            note = client_row.get('rating', None)
            st.sidebar.markdown("---")
            st.sidebar.markdown("**Informations prospect :**")
            st.sidebar.markdown(f"**Catégorie :** {cat if cat else 'Non renseigné'}")
            st.sidebar.markdown(f"**Site web :** {'[Site](' + site + ')' if site else 'Non renseigné'}")
            st.sidebar.markdown(f"**Email :** {'[Email](mailto:' + email + ')' if email else 'Non renseigné'}")
            st.sidebar.markdown(f"**Lien Google Maps :** {'[Maps](' + link + ')' if link else 'Non renseigné'}")
            st.sidebar.markdown(f"**Avis :** {avis if avis else 'Non renseigné'} | **Note :** {note if note else 'Non renseigné'}")
        
        if st.sidebar.button("Fermer", key="close_client_details"):
            st.session_state['show_client_details'] = None
            st.rerun() 