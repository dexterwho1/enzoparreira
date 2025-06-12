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

    st.write("")
    st.subheader("Tableau des prospects")
    if df.empty:
        st.info("Aucun prospect trouvé.")
    else:
        # Gestion de la sélection multiple
        selection = st.session_state.get('selection', set())
        if not isinstance(selection, set):
            selection = set()
        all_ids = df['place_id'].tolist()
        # Affichage de la case 'Tout sélectionner' au-dessus du tableau
        select_all = st.checkbox("Tout sélectionner", value=len(selection)==len(all_ids) and len(all_ids)>0, key="select_all_checkbox")
        # Mise à jour de la sélection si on coche/décoche 'Tout sélectionner'
        if select_all and len(selection) != len(all_ids):
            selection = set(all_ids)
        elif not select_all and len(selection) == len(all_ids):
            selection = set()
        # Affichage du tableau
        col_nom, col_cat, col_adr, col_tel, col_details = st.columns([3,2,3,2,2])
        with col_nom:
            st.markdown("**Nom**")
        with col_cat:
            st.markdown("**Catégorie**")
        with col_adr:
            st.markdown("**Adresse**")
        with col_tel:
            st.markdown("**Téléphone**")
        with col_details:
            st.markdown("**Détails**")
        for i, row in df.iterrows():
            cols = st.columns([1,3,2,3,2,2])
            with cols[0]:
                checked = st.checkbox("", value=row['place_id'] in selection, key=f"sel_{row['place_id']}")
                if checked:
                    selection.add(row['place_id'])
                else:
                    selection.discard(row['place_id'])
            with cols[1]:
                st.write(row['name'])
            with cols[2]:
                st.write(row['main_category'])
            with cols[3]:
                st.write(row['address'])
            with cols[4]:
                st.write(row['phone'])
            with cols[5]:
                if st.button("Détails", key=f"details_{row['place_id']}"):
                    st.session_state['show_details'] = row['place_id']
        st.session_state['selection'] = selection

        # --- Panneau d'action à droite ---
        if selection:
            st.sidebar.subheader("Actions sur la sélection")
            if st.sidebar.button("Supprimer la sélection", type="primary"):
                with sqlite3.connect(DB_PATH) as conn:
                    c = conn.cursor()
                    c.executemany("DELETE FROM prospects WHERE place_id=?", [(pid,) for pid in selection])
                    conn.commit()
                st.success(f"{len(selection)} prospect(s) supprimé(s).")
                st.session_state['selection'] = set()
                st.experimental_rerun()
            st.sidebar.markdown("**Changer le statut d'appel :**")
            for statut in STATUTS:
                if st.sidebar.button(statut, key=f"statut_bulk_{statut}"):
                    with sqlite3.connect(DB_PATH) as conn:
                        c = conn.cursor()
                        now = datetime.now().strftime("%Y-%m-%d %H:%M")
                        for pid in selection:
                            c.execute("UPDATE prospects SET statut_appel=?, date_dernier_appel=? WHERE place_id=?", (statut, now, pid))
                        conn.commit()
                    st.success(f"Statut '{statut}' appliqué à la sélection.")
                    st.experimental_rerun()

        # --- Affichage des détails dans un panneau latéral ---
        show_details = st.session_state.get('show_details', None)
        if show_details:
            detail_row = df[df['place_id'] == show_details].iloc[0]
            st.sidebar.subheader(f"Détails pour {detail_row['name']}")
            st.sidebar.markdown(f"**Catégorie :** {detail_row['main_category']}")
            st.sidebar.markdown(f"**Adresse :** {detail_row['address']}")
            st.sidebar.markdown(f"**Téléphone :** {detail_row['phone']}")
            st.sidebar.markdown(f"**Site web :** {'[Site](' + detail_row['website'] + ')' if detail_row['website'] else 'Non dispo'}")
            st.sidebar.markdown(f"**Email :** {'[Email](mailto:' + detail_row['emails'] + ')' if detail_row['emails'] else 'Non dispo'}")
            st.sidebar.markdown(f"**Lien Google Maps :** {'[Maps](' + detail_row['link'] + ')' if detail_row['link'] else 'Non dispo'}")
            st.sidebar.markdown(f"**Avis :** {detail_row['reviews']} | **Note :** {detail_row['rating']}")
            st.sidebar.markdown(f"**Statut appel :** {detail_row['statut_appel'] if detail_row['statut_appel'] else 'Non renseigné'}")
            if st.sidebar.button("Fermer", key="close_details"):
                st.session_state['show_details'] = None

# ... le reste du code (autres pages) ...
