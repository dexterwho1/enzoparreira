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
    
    # Affichage du tableau
    if df.empty:
        st.info("Aucun prospect trouvé.")
    else:
        def lien_maps(row):
            if row['link']:
                return f"[Maps]({row['link']})"
            return "Non dispo"
        def lien_site(row):
            if row['website']:
                return f"[Site]({row['website']})"
            return "Non dispo"
        def mailto(row):
            if row['emails']:
                return f"[Email](mailto:{row['emails']})"
            return "Non dispo"
        # Construction du tableau affiché
        display_df = pd.DataFrame({
            'Nom': df['name'],
            'Téléphone': df['phone'],
            'Adresse': df['address'],
            'Catégorie': df['main_category'],
            'Site web': df.apply(lien_site, axis=1),
            'Email': df.apply(mailto, axis=1),
            'Lien Google Maps': df.apply(lien_maps, axis=1),
            'Avis': df['reviews'],
            'Note': df['rating'],
            'Statut appel': df['statut_appel'].fillna("")
        })
        st.dataframe(display_df, use_container_width=True)
        st.caption("Cliquez sur un prospect pour voir les détails ou changer le statut d'appel.")

# ... le reste du code (autres pages) ...
