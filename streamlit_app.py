import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime
import hashlib

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
        # Filtre numéro FR mobile
        tel_clean = tel.replace(" ", "").replace("-", "")
        if not (nom and tel and adresse):
            erreurs.append(f"Ligne {idx+2} ignorée : nom/téléphone/adresse manquant.")
            continue
        if not (tel_clean.startswith("06") or tel_clean.startswith("07") or tel_clean.startswith("+336") or tel_clean.startswith("+337")):
            erreurs.append(f"Ligne {idx+2} ignorée : numéro non mobile FR (06, 07, +336, +337).")
            continue
        # Gestion du doublon : on met à jour si le téléphone existe déjà
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM prospects WHERE phone=?", (tel,))
            exists = c.fetchone()
            if exists:
                # Mise à jour
                c.execute("""
                    UPDATE prospects SET
                        place_id=?, name=?, website=?, emails=?, main_category=?, categories=?, reviews=?, rating=?, address=?, horaires=?, link=?, featured_reviews=?, is_spending_on_ads=?, query=?
                    WHERE phone=?
                """, (
                    str(row.get("place_id", "")).strip(),
                    nom,
                    row.get("website", ""),
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
                    tel
                ))
            else:
                # Insertion
                c.execute("""
                    INSERT INTO prospects (place_id, name, website, phone, emails, main_category, categories, reviews, rating, address, horaires, link, featured_reviews, is_spending_on_ads, query)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(row.get("place_id", "")).strip(),
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
PAGES = ["Dashboard", "CRM Clients", "Commandes", "Planning", "Prospection", "KPI Prospection"]
page = st.sidebar.radio("Navigation", PAGES, index=4)

if page == "Prospection":
    st.title("Prospection")
    st.markdown("""
    <style>
    .css-1aumxhk, .css-1v0mbdj, .css-1d391kg {background-color: #222 !important; color: #fff !important;}
    </style>
    """, unsafe_allow_html=True)

    # --- Formulaire d'ajout manuel de prospect ---
    st.header("Ajouter un prospect manuellement")
    with st.form("ajout_prospect_form"):
        lien = st.text_input("Lien Google Maps de la fiche *", "")
        nom = st.text_input("Nom *", "")
        categorie = st.text_input("Catégorie *", "")
        telephone = st.text_input("Téléphone *", "")
        submitted = st.form_submit_button("Ajouter")
        if submitted:
            if not (lien and nom and categorie and telephone):
                st.error("Merci de remplir tous les champs obligatoires.")
            else:
                import hashlib
                place_id = hashlib.md5(lien.encode()).hexdigest()
                with sqlite3.connect(DB_PATH) as conn:
                    c = conn.cursor()
                    c.execute("SELECT * FROM prospects WHERE phone=?", (telephone,))
                    exists = c.fetchone()
                    if exists:
                        st.error("Ce prospect existe déjà (même téléphone).")
                    else:
                        c.execute("""
                            INSERT INTO prospects (place_id, name, main_category, phone, link)
                            VALUES (?, ?, ?, ?, ?)
                        """, (place_id, nom, categorie, telephone, lien))
                        conn.commit()
                        st.success("Prospect ajouté avec succès !")
                        st.rerun()

    st.header("Liste des prospects")
    # Filtres principaux (hors statut d'appel)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        filtre_nom = st.text_input("Rechercher par nom...")
    with col2:
        filtre_tel = st.text_input("Rechercher par téléphone...")
    with col3:
        filtre_cat = st.text_input("Rechercher par catégorie...")
    with col4:
        filtre_adr = st.text_input("Rechercher par adresse...")
    
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

    st.write("")
    st.subheader("Tableau des prospects")
    if df.empty:
        st.info("Aucun prospect trouvé.")
    else:
        # --- Sélection bulk ---
        selection = st.session_state.get('selection', set())
        if not isinstance(selection, set):
            selection = set()
        all_ids = df['place_id'].tolist()
        
        # Initialiser la sélection individuelle si elle n'existe pas
        if 'selected_individual' not in st.session_state:
            st.session_state['selected_individual'] = None
        if 'show_statut_popup' not in st.session_state:
            st.session_state['show_statut_popup'] = None
            
        # Affichage de la case 'Tout sélectionner' au-dessus du tableau
        select_all = st.checkbox("Tout sélectionner pour bulk", value=len(selection)==len(all_ids) and len(all_ids)>0, key="select_all_checkbox")
        if select_all and len(selection) != len(all_ids):
            selection = set(all_ids)
        elif not select_all and len(selection) == len(all_ids):
            selection = set()
            
        # --- Filtre d'appel rapide (menu à droite) ---
        st.write("")
        st.markdown("**Filtrer par statut d'appel (rapide) :**")
        filtre_rapide = st.selectbox("Statut d'appel", ["Tous"] + STATUTS, key="filtre_rapide")
        df_affiche = df.copy()
        if filtre_rapide != "Tous":
            df_affiche = df_affiche[df_affiche['statut_appel'] == filtre_rapide]
            
        # Affichage du tableau avec colonnes dédiées
        col_sel, col_nom, col_cat, col_adr, col_tel, col_date, col_details, col_statut = st.columns([1,3,2,3,2,2,2,2])
        with col_sel:
            st.markdown("<div style='text-align:center;white-space:nowrap'><b>Sélectionner</b></div>", unsafe_allow_html=True)
        with col_nom:
            st.markdown("<div style='text-align:center;white-space:nowrap'><b>Nom</b></div>", unsafe_allow_html=True)
        with col_cat:
            st.markdown("<div style='text-align:center;white-space:nowrap'><b>Catégorie</b></div>", unsafe_allow_html=True)
        with col_adr:
            st.markdown("<div style='text-align:center;white-space:nowrap'><b>Adresse</b></div>", unsafe_allow_html=True)
        with col_tel:
            st.markdown("<div style='text-align:center;white-space:nowrap'><b>Téléphone</b></div>", unsafe_allow_html=True)
        with col_date:
            st.markdown("<div style='text-align:center;white-space:nowrap'><b>Date action</b></div>", unsafe_allow_html=True)
        with col_details:
            st.markdown("<div style='text-align:center;white-space:nowrap'><b>Détails</b></div>", unsafe_allow_html=True)
        with col_statut:
            st.markdown("<div style='text-align:center;white-space:nowrap'><b>Statut d'appel</b></div>", unsafe_allow_html=True)
            
        for i, row in df_affiche.iterrows():
            cols = st.columns([1,3,2,3,2,2,2,2])
            with cols[0]:
                checked = st.checkbox(" ", value=row['place_id'] in selection, key=f"sel_{row['place_id']}", label_visibility="collapsed")
                if checked:
                    selection.add(row['place_id'])
                else:
                    selection.discard(row['place_id'])
            with cols[1]:
                if st.button(row['name'], key=f"nom_{row['place_id']}"):
                    st.session_state['show_transfer'] = row['place_id']
            with cols[2]:
                st.write(row['main_category'])
            with cols[3]:
                st.write(row['address'])
            with cols[4]:
                st.write(row['phone'])
            with cols[5]:
                st.write(row['date_dernier_appel'] if row['date_dernier_appel'] else "-")
            with cols[6]:
                if st.button("Détails", key=f"details_{row['place_id']}"):
                    st.session_state['show_details'] = row['place_id']
            with cols[7]:
                # Sélection individuelle exclusive avec logique de toggle
                current_selected = st.session_state.get('selected_individual', None)
                is_selected = current_selected == row['place_id']
                
                if st.button("Changer statut", key=f"statut_btn_{row['place_id']}"):
                    if is_selected:
                        # Si déjà sélectionné, on désélectionne
                        st.session_state['selected_individual'] = None
                    else:
                        # Sinon on sélectionne ce prospect
                        st.session_state['selected_individual'] = row['place_id']
                        st.session_state['show_statut_popup'] = row['place_id']
                    st.rerun()
                    
                # Afficher le statut actuel
                if row['statut_appel']:
                    st.write(f"📞 {row['statut_appel']}")
                else:
                    st.write("❌ Non défini")

        st.session_state['selection'] = selection

        # --- Popup pour changer le statut d'appel individuellement ---
        show_statut_popup = st.session_state.get('show_statut_popup', None)
        if show_statut_popup:
            prospect_popup = df[df['place_id'] == show_statut_popup].iloc[0]
            st.sidebar.subheader(f"Changer le statut d'appel pour {prospect_popup['name']}")
            st.sidebar.markdown(f"**Statut actuel :** {prospect_popup['statut_appel'] if prospect_popup['statut_appel'] else 'Non défini'}")
            statut_choisi = None
            for statut in STATUTS:
                if st.sidebar.button(f"✅ {statut}", key=f"popup_statut_{statut}_{show_statut_popup}"):
                    statut_choisi = statut
            if statut_choisi:
                with sqlite3.connect(DB_PATH) as conn:
                    c = conn.cursor()
                    now = datetime.now().strftime("%Y-%m-%d %H:%M")
                    c.execute("UPDATE prospects SET statut_appel=?, date_dernier_appel=? WHERE place_id=?", 
                            (statut_choisi, now, show_statut_popup))
                    conn.commit()
                st.session_state['show_statut_popup'] = None
                st.session_state['selected_individual'] = None
                st.rerun()
            if st.sidebar.button("❌ Annuler", key="cancel_statut_popup"):
                st.session_state['show_statut_popup'] = None
                st.session_state['selected_individual'] = None
                st.rerun()

        # --- Panneau d'action à droite pour bulk ---
        if selection:
            st.sidebar.subheader("Actions sur la sélection (bulk)")
            if st.sidebar.button("Supprimer la sélection", type="primary"):
                with sqlite3.connect(DB_PATH) as conn:
                    c = conn.cursor()
                    c.executemany("DELETE FROM prospects WHERE place_id=?", [(pid,) for pid in selection])
                    conn.commit()
                st.success(f"{len(selection)} prospect(s) supprimé(s).")
                st.session_state['selection'] = set()
                st.rerun()
            st.sidebar.markdown("**Changer le statut d'appel (bulk) :**")
            for statut in STATUTS:
                if st.sidebar.button(statut, key=f"statut_bulk_{statut}"):
                    with sqlite3.connect(DB_PATH) as conn:
                        c = conn.cursor()
                        now = datetime.now().strftime("%Y-%m-%d %H:%M")
                        for pid in selection:
                            c.execute("UPDATE prospects SET statut_appel=?, date_dernier_appel=? WHERE place_id=?", (statut, now, pid))
                        conn.commit()
                    st.success(f"Statut '{statut}' appliqué à la sélection.")
                    st.session_state['selection'] = set()
                    st.rerun()

        # --- Popup de transfert en client ---
        show_transfer = st.session_state.get('show_transfer', None)
        if show_transfer:
            prospect = df[df['place_id'] == show_transfer].iloc[0]
            st.sidebar.subheader(f"Transférer {prospect['name']} en client")
            with st.sidebar.form(f"form_transfer_{show_transfer}"):
                date_debut = st.date_input("Date de début *")
                date_fin = st.date_input("Date de fin *")
                prix = st.number_input("Prix *", min_value=0.0, step=10.0)
                encaisse = st.number_input("Encaissé (optionnel)", min_value=0.0, step=10.0, value=0.0)
                recurrence = st.selectbox("Récurrent (optionnel)", ["Non", "2 semaines", "1 mois"])
                submit_transfer = st.form_submit_button("Transférer en client")
                
                if submit_transfer:
                    if not (date_debut and date_fin and prix):
                        st.error("Merci de remplir tous les champs obligatoires.")
                    else:
                        with sqlite3.connect(DB_PATH) as conn:
                            c = conn.cursor()
                            # Création du client
                            c.execute("""
                                INSERT INTO clients (place_id, name, phone, address, date_conversion, last_contact)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (
                                prospect['place_id'],
                                prospect['name'],
                                prospect['phone'],
                                prospect['address'],
                                date_debut.strftime("%Y-%m-%d"),
                                date_debut.strftime("%Y-%m-%d")
                            ))
                            client_id = c.lastrowid
                            # Création de la commande
                            c.execute("""
                                INSERT INTO commandes (client_id, prestation, prix, recurrence, date_debut, date_fin, argent_encaisse, statut)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                client_id,
                                prospect['main_category'],
                                prix,
                                recurrence if recurrence != "Non" else None,
                                date_debut.strftime("%Y-%m-%d"),
                                date_fin.strftime("%Y-%m-%d"),
                                encaisse,
                                "active"
                            ))
                            # Suppression du prospect
                            c.execute("DELETE FROM prospects WHERE place_id=?", (prospect['place_id'],))
                            conn.commit()
                        st.success("Prospect transféré en client avec succès !")
                        st.session_state['show_transfer'] = None
                        st.rerun()
                        
            if st.sidebar.button("Fermer", key="close_transfer"):
                st.session_state['show_transfer'] = None
                st.rerun()

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
            st.sidebar.markdown("**Changer le statut d'appel individuellement :**")
            for statut in STATUTS:
                if st.sidebar.button(statut, key=f"statut_indiv_{statut}_{detail_row['place_id']}"):
                    with sqlite3.connect(DB_PATH) as conn:
                        c = conn.cursor()
                        now = datetime.now().strftime("%Y-%m-%d %H:%M")
                        c.execute("UPDATE prospects SET statut_appel=?, date_dernier_appel=? WHERE place_id=?", (statut, now, detail_row['place_id']))
                        conn.commit()
                    st.success(f"Statut '{statut}' appliqué à {detail_row['name']}.")
                    st.session_state['show_details'] = None
                    st.rerun()
            if st.sidebar.button("Fermer", key="close_details"):
                st.session_state['show_details'] = None
                st.rerun()

elif page == "KPI Prospection":
    import kpi_prospection

# Autres pages (Dashboard, CRM Clients, etc.) - à implémenter selon vos besoins
elif page == "Dashboard":
    st.title("Dashboard")
    st.info("Page Dashboard à implémenter")
    
elif page == "CRM Clients":
    import crm_clients
    
elif page == "Commandes":
    st.title("Commandes")
    st.info("Page Commandes à implémenter")
    
elif page == "Planning":
    st.title("Planning")
    st.info("Page Planning à implémenter")