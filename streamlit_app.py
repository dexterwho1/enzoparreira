import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime

# --- Initialisation de la base de données ---
DB_PATH = "crm_data.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Table des prospects
    c.execute('''CREATE TABLE IF NOT EXISTS prospects (
        place_id TEXT PRIMARY KEY,
        name TEXT,
        website TEXT,
        phone TEXT,
        emails TEXT,
        main_category TEXT,
        categories TEXT,
        reviews INTEGER,
        rating REAL,
        address TEXT,
        horaires TEXT,
        link TEXT,
        featured_reviews TEXT,
        is_spending_on_ads TEXT,
        query TEXT,
        statut_appel TEXT DEFAULT '',
        date_dernier_appel TEXT DEFAULT '',
        meta_appel TEXT DEFAULT ''
    )''')
    # Table des clients
    c.execute('''CREATE TABLE IF NOT EXISTS clients (
        client_id INTEGER PRIMARY KEY AUTOINCREMENT,
        place_id TEXT,
        name TEXT,
        phone TEXT,
        address TEXT,
        date_conversion TEXT,
        last_contact TEXT,
        FOREIGN KEY(place_id) REFERENCES prospects(place_id)
    )''')
    # Table des prestations/commandes
    c.execute('''CREATE TABLE IF NOT EXISTS commandes (
        commande_id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        prestation TEXT,
        prix REAL,
        recurrence TEXT,
        date_debut TEXT,
        date_fin TEXT,
        argent_encaisse REAL,
        statut TEXT,
        FOREIGN KEY(client_id) REFERENCES clients(client_id)
    )''')
    conn.commit()
    conn.close()

init_db()

st.title("CRM Agence - Prospection & Clients")

# --- Import CSV Prospects ---
st.header("Importer des prospects (CSV)")
file = st.file_uploader("Choisir un fichier CSV", type=["csv"])

if file:
    df = pd.read_csv(file)
    # Vérification des champs obligatoires
    erreurs = []
    lignes_valides = []
    for idx, row in df.iterrows():
        nom = str(row.get("name", "")).strip()
        tel = str(row.get("phone", "")).strip()
        adresse = str(row.get("address", "")).strip()
        if not (nom and tel and adresse):
            erreurs.append(f"Ligne {idx+2} ignorée : nom/téléphone/adresse manquant.")
            continue
        # Normalisation du téléphone (optionnel)
        # tel = tel.replace(" ", "").replace("-", "")
        # Gestion du doublon : on met à jour si place_id existe déjà
        place_id = str(row.get("place_id", "")).strip()
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM prospects WHERE place_id=?", (place_id,))
            exists = c.fetchone()
            if exists:
                # Mise à jour
                c.execute("""
                    UPDATE prospects SET
                        name=?, website=?, phone=?, emails=?, main_category=?, categories=?, reviews=?, rating=?, address=?, horaires=?, link=?, featured_reviews=?, is_spending_on_ads=?, query=?
                    WHERE place_id=?
                """, (
                    nom,
                    row.get("website", ""),
                    tel,
                    row.get("emails", ""),
                    row.get("main_category", ""),
                    str(row.get("categories", "")),
                    row.get("reviews", 0),
                    row.get("rating", 0),
                    adresse,
                    row.get("horaires", ""),
                    row.get("link", ""),
                    str(row.get("featured_reviews", "")),
                    str(row.get("is_spending_on_ads", "")),
                    row.get("query", ""),
                    place_id
                ))
            else:
                # Insertion
                c.execute("""
                    INSERT INTO prospects (place_id, name, website, phone, emails, main_category, categories, reviews, rating, address, horaires, link, featured_reviews, is_spending_on_ads, query)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    place_id,
                    nom,
                    row.get("website", ""),
                    tel,
                    row.get("emails", ""),
                    row.get("main_category", ""),
                    str(row.get("categories", "")),
                    row.get("reviews", 0),
                    row.get("rating", 0),
                    adresse,
                    row.get("horaires", ""),
                    row.get("link", ""),
                    str(row.get("featured_reviews", "")),
                    str(row.get("is_spending_on_ads", "")),
                    row.get("query", "")
                ))
            conn.commit()
        lignes_valides.append(nom)
    st.success(f"{len(lignes_valides)} prospects importés/mis à jour.")
    if erreurs:
        st.warning("\n".join(erreurs))

# --- Statuts d'appel (fixes) ---
STATUTS = ["n'a pas répondu", "à rappeller", "r1", "pas intérréssé", "signé"]

# --- Navigation ---
PAGES = ["Dashboard", "CRM Clients", "Commandes", "Planning", "Prospection"]
page = st.sidebar.radio("Navigation", PAGES, index=4)

if page == "Prospection":
    st.title("Prospection")
    st.markdown("""
    <style>
    .css-1aumxhk, .css-1v0mbdj, .css-1d391kg {background-color: #222 !important; color: #fff !important;}
    </style>
    """, unsafe_allow_html=True)
    
    st.header("Liste des prospects")
    # Filtres
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        filtre_nom = st.text_input("Rechercher par nom...")
    with col2:
        filtre_tel = st.text_input("Rechercher par téléphone...")
    with col3:
        filtre_cat = st.text_input("Rechercher par catégorie...")
    with col4:
        filtre_adr = st.text_input("Rechercher par adresse...")
    with col5:
        filtre_statut = st.selectbox("Filtrer par statut d'appel", ["Tous"] + STATUTS)
    
    # Boutons appelés/non appelés
    colA, colB = st.columns(2)
    with colA:
        voir_appeles = st.button("Voir appelés")
    with colB:
        voir_non_appeles = st.button("Voir non appelés")
    
    # Récupération des prospects
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query("SELECT * FROM prospects", conn)
    # Application des filtres
    if filtre_nom:
        df = df[df['name'].str.contains(filtre_nom, case=False, na=False)]
    if filtre_tel:
        df = df[df['phone'].str.contains(filtre_tel, case=False, na=False)]
    if filtre_cat:
        df = df[df['main_category'].str.contains(filtre_cat, case=False, na=False)]
    if filtre_adr:
        df = df[df['address'].str.contains(filtre_adr, case=False, na=False)]
    if filtre_statut != "Tous":
        df = df[df['statut_appel'] == filtre_statut]
    if voir_appeles:
        df = df[df['statut_appel'].isin([s for s in STATUTS if s != ""])]
    if voir_non_appeles:
        df = df[df['statut_appel'].isnull() | (df['statut_appel'] == "")]
    
    # Suppression multiple
    st.write("")
    st.subheader("Sélection et suppression")
    if not df.empty:
        selection = st.multiselect(
            "Sélectionner les prospects à supprimer :",
            options=df['place_id'],
            format_func=lambda x: df[df['place_id'] == x]['name'].values[0]
        )
        if selection:
            if st.button("Supprimer la sélection", type="primary"):
                with sqlite3.connect(DB_PATH) as conn:
                    c = conn.cursor()
                    c.executemany("DELETE FROM prospects WHERE place_id=?", [(pid,) for pid in selection])
                    conn.commit()
                st.success(f"{len(selection)} prospect(s) supprimé(s).")
                st.experimental_rerun()
    
    # Affichage du tableau avec clic pour modifier le statut
    if df.empty:
        st.info("Aucun prospect trouvé.")
    else:
        st.write("")
        st.subheader("Tableau des prospects")
        for idx, row in df.iterrows():
            with st.expander(f"{row['name']} | {row['phone']} | {row['address']}"):
                st.markdown(f"**Catégorie :** {row['main_category']}")
                st.markdown(f"**Site web :** {'[Site](' + row['website'] + ')' if row['website'] else 'Non dispo'}")
                st.markdown(f"**Email :** {'[Email](mailto:' + row['emails'] + ')' if row['emails'] else 'Non dispo'}")
                st.markdown(f"**Lien Google Maps :** {'[Maps](' + row['link'] + ')' if row['link'] else 'Non dispo'}")
                st.markdown(f"**Avis :** {row['reviews']} | **Note :** {row['rating']}")
                st.markdown(f"**Statut appel actuel :** {row['statut_appel'] if row['statut_appel'] else 'Non renseigné'}")
                new_statut = st.selectbox(
                    "Changer le statut d'appel :",
                    [row['statut_appel']] + [s for s in STATUTS if s != row['statut_appel']],
                    key=f"statut_{row['place_id']}"
                )
                if new_statut != row['statut_appel'] and st.button("Enregistrer le nouveau statut", key=f"save_{row['place_id']}"):
                    with sqlite3.connect(DB_PATH) as conn:
                        c = conn.cursor()
                        c.execute("UPDATE prospects SET statut_appel=?, date_dernier_appel=? WHERE place_id=?", (new_statut, datetime.now().strftime("%Y-%m-%d %H:%M"), row['place_id']))
                        conn.commit()
                    st.success("Statut mis à jour !")
                    st.experimental_rerun()

# ... le reste du code (autres pages) ...
