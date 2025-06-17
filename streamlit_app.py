import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime
import hashlib
import re
from glob import glob
import requests

# Configuration de la page
st.set_page_config(page_title="CRM Agence", layout="wide")

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
        nom_service TEXT,
        prestation TEXT,
        prix REAL,
        recurrence TEXT,
        date_debut TEXT,
        date_fin TEXT,
        argent_encaisse REAL,
        statut TEXT,
        temps_passe TEXT,
        FOREIGN KEY(client_id) REFERENCES clients(client_id)
    )''')
    # Table historique des statuts
    c.execute('''CREATE TABLE IF NOT EXISTS historique_statuts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        place_id TEXT,
        statut TEXT,
        date_changement TEXT,
        FOREIGN KEY (place_id) REFERENCES prospects (place_id)
    )''')
    
    # Ajouter la colonne nom_service si elle n'existe pas
    try:
        c.execute("ALTER TABLE commandes ADD COLUMN nom_service TEXT")
    except:
        pass  # La colonne existe déjà
    
    # Correctif ponctuel : donner un nom de service par défaut aux commandes qui n'en ont pas
    c.execute("""
        UPDATE commandes
        SET nom_service = 'Service par défaut'
        WHERE nom_service IS NULL OR nom_service = ''
    """)
    
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
    
    def is_french_mobile(phone):
        """Vérifie si le numéro est un mobile français valide"""
        if not isinstance(phone, str) or not phone.strip():
            return False
        # Nettoie le numéro (supprime espaces, tirets, points)
        phone_clean = re.sub(r'[\s\-\.]', '', phone.strip())
        # Regex pour mobile français: 06/07 ou +336/+337 suivi de 8 chiffres
        return bool(re.match(r'^(0|\+33)[67]\d{8}$', phone_clean))
    
    for idx, row in df.iterrows():
        nom = str(row.get("name", "")).strip()
        tel = str(row.get("phone", "")).strip()
        adresse = str(row.get("address", "")).strip()
        
        # Filtre numéro mobile FR uniquement
        if not is_french_mobile(tel):
            erreurs.append(f"Ligne {idx+2} ignorée : numéro non mobile FR (06, 07, +336, +337). Numéro: {tel}")
            continue
            
        if not (nom and tel and adresse):
            erreurs.append(f"Ligne {idx+2} ignorée : nom/téléphone/adresse manquant.")
            continue
            
        # Normalise le numéro pour stockage (format 0X XX XX XX XX)
        tel_clean = re.sub(r'[\s\-\.]', '', tel)
        if tel_clean.startswith('+33'):
            tel_clean = '0' + tel_clean[3:]
        
        # Gestion du doublon : on met à jour si le téléphone existe déjà
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM prospects WHERE phone=?", (tel_clean,))
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
                    tel_clean
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
                    tel_clean,
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
PAGES = [
    "Dashboard",
    "CRM Clients",
    "Commandes",
    "Planning",
    "Prospection",
    "KPI Prospection",
    "Checklists",
    "Automatisation",
    "Générateur de site"
]
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
    # Première ligne de filtres
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        filtre_nom = st.text_input("Rechercher par nom...")
    with col2:
        filtre_tel = st.text_input("Rechercher par téléphone...")
    with col3:
        filtre_cat = st.text_input("Rechercher par catégorie...")
    with col4:
        filtre_adr = st.text_input("Rechercher par adresse...")
    
    # Deuxième ligne de filtres
    st.write("")
    st.markdown("**Filtrer par statut d'appel :**")
    filtre_appel = st.radio("", ["Tous", "Non appelé", "Appelé"], horizontal=True, label_visibility="collapsed")
    
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

    # Application du filtre 'Appelé / Non appelé'
    if 'filtre_appel' in locals() and filtre_appel != "Tous":
        if filtre_appel == "Appelé":
            df = df[df['statut_appel'].fillna('') != '']
        elif filtre_appel == "Non appelé":
            df = df[df['statut_appel'].fillna('') == '']

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
                    # Ajout historique
                    c.execute("INSERT INTO historique_statuts (place_id, statut, date_changement) VALUES (?, ?, ?)", (show_statut_popup, statut_choisi, now))
                    conn.commit()
                st.session_state['show_statut_popup'] = None
                st.session_state['selected_individual'] = None
                st.session_state['planning_popup'] = {
                    'place_id': show_statut_popup,
                    'statut': statut_choisi
                }
                st.rerun()
            if st.sidebar.button("❌ Annuler", key="cancel_statut_popup"):
                st.session_state['show_statut_popup'] = None
                st.session_state['selected_individual'] = None
                st.rerun()

        # --- En dehors de la popup, si planning_popup est défini, afficher le mini-formulaire
        planning_popup = st.session_state.get('planning_popup', None)
        if planning_popup and planning_popup['statut'] in ['r1', 'à rappeller']:
            prospect = df[df['place_id'] == planning_popup['place_id']].iloc[0]
            st.sidebar.subheader(f"Ajouter un rappel au planning pour {prospect['name']}")
            default_comment = f"{prospect['phone']}" if prospect.get('phone') else ""
            with st.sidebar.form(f"form_planning_{prospect['place_id']}"):
                titre = st.text_input("Titre du rappel", f"Rappel {planning_popup['statut']} - {prospect['name']}")
                date = st.date_input("Date", value=datetime.now().date())
                heure = st.time_input("Heure", value=datetime.now().time().replace(second=0, microsecond=0))
                commentaire = st.text_area("Commentaire (optionnel)", value=default_comment)
                submit_planning = st.form_submit_button("Ajouter au planning")
                if submit_planning:
                    with sqlite3.connect(DB_PATH) as conn:
                        c = conn.cursor()
                        date_debut = datetime.combine(date, heure)
                        c.execute("""
                            INSERT INTO taches (client_id, commande_id, type_tache, titre, description, date_debut, est_process, service)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            None,  # client_id (optionnel, à lier si besoin)
                            None,  # commande_id
                            planning_popup['statut'],
                            titre,
                            commentaire,
                            date_debut,
                            1,  # est_process = True (pas lié à un client)
                            prospect['place_id']  # <-- place_id stocké dans 'service'
                        ))
                        conn.commit()
                    st.success("Rappel ajouté au planning !")
                    st.session_state['planning_popup'] = None
                    st.rerun()
            if st.sidebar.button("Fermer", key=f"close_planning_popup_{prospect['place_id']}"):
                st.session_state['planning_popup'] = None
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
                            # Ajout historique
                            c.execute("INSERT INTO historique_statuts (place_id, statut, date_changement) VALUES (?, ?, ?)", (pid, statut, now))
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
                nom_service = st.text_input("Nom du service *", "")
                date_debut = st.date_input("Date de début *")
                date_fin = st.date_input("Date de fin *")
                prix = st.number_input("Prix *", min_value=0.0, step=10.0)
                encaisse = st.number_input("Encaissé (optionnel)", min_value=0.0, step=10.0, value=0.0)
                recurrence = st.selectbox("Récurrent (optionnel)", ["Non", "2 semaines", "1 mois"])
                submit_transfer = st.form_submit_button("Transférer en client")
                
                if submit_transfer:
                    if not (nom_service and date_debut and date_fin and prix):
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
                                INSERT INTO commandes (client_id, nom_service, prix, recurrence, date_debut, date_fin, argent_encaisse, statut)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                client_id,
                                nom_service,
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
                        # Ajout historique
                        c.execute("INSERT INTO historique_statuts (place_id, statut, date_changement) VALUES (?, ?, ?)", (detail_row['place_id'], statut, now))
                        conn.commit()
                    st.success(f"Statut '{statut}' appliqué à {detail_row['name']}.")
                    st.session_state['show_details'] = None
                    st.rerun()
            if st.sidebar.button("Fermer", key="close_details"):
                st.session_state['show_details'] = None
                st.rerun()

elif page == "KPI Prospection":
    with open("kpi_prospection.py", encoding="utf-8") as f:
        exec(f.read(), globals())

elif page == "Planning":
    with open("planning.py", encoding="utf-8") as f:
        exec(f.read(), globals())

# Autres pages (Dashboard, CRM Clients, etc.) - à implémenter selon vos besoins
elif page == "Dashboard":
    st.title("Dashboard")
    st.subheader("Productivité du jour")
    # --- Récupération des données ---
    today = datetime.now().date()
    yesterday = today - pd.Timedelta(days=1)
    last_week = today - pd.Timedelta(days=7)
    with sqlite3.connect(DB_PATH) as conn:
        # Appels aujourd'hui, hier, S-1
        appels_today = pd.read_sql_query("SELECT COUNT(*) as n FROM taches WHERE date(date_debut)=? AND type_tache='tache'", conn, params=(today,)).iloc[0]['n']
        appels_yesterday = pd.read_sql_query("SELECT COUNT(*) as n FROM taches WHERE date(date_debut)=? AND type_tache='tache'", conn, params=(yesterday,)).iloc[0]['n']
        appels_lastweek = pd.read_sql_query("SELECT COUNT(*) as n FROM taches WHERE date(date_debut)=? AND type_tache='tache'", conn, params=(last_week,)).iloc[0]['n']
        # RDV
        rdv_today = pd.read_sql_query("SELECT COUNT(*) as n FROM taches WHERE date(date_debut)=? AND type_tache='r1'", conn, params=(today,)).iloc[0]['n']
        rdv_yesterday = pd.read_sql_query("SELECT COUNT(*) as n FROM taches WHERE date(date_debut)=? AND type_tache='r1'", conn, params=(yesterday,)).iloc[0]['n']
        rdv_lastweek = pd.read_sql_query("SELECT COUNT(*) as n FROM taches WHERE date(date_debut)=? AND type_tache='r1'", conn, params=(last_week,)).iloc[0]['n']
        # Missions finies
        missions_today = pd.read_sql_query("SELECT COUNT(*) as n FROM taches WHERE date(date_debut)=? AND statut='terminé'", conn, params=(today,)).iloc[0]['n']
        missions_yesterday = pd.read_sql_query("SELECT COUNT(*) as n FROM taches WHERE date(date_debut)=? AND statut='terminé'", conn, params=(yesterday,)).iloc[0]['n']
        missions_lastweek = pd.read_sql_query("SELECT COUNT(*) as n FROM taches WHERE date(date_debut)=? AND statut='terminé'", conn, params=(last_week,)).iloc[0]['n']
        # Heures travaillées
        heures_today = pd.read_sql_query("SELECT SUM(temps_passe) as h FROM taches WHERE date(date_debut)=?", conn, params=(today,)).iloc[0]['h'] or 0
        heures_yesterday = pd.read_sql_query("SELECT SUM(temps_passe) as h FROM taches WHERE date(date_debut)=?", conn, params=(yesterday,)).iloc[0]['h'] or 0
        heures_lastweek = pd.read_sql_query("SELECT SUM(temps_passe) as h FROM taches WHERE date(date_debut)=?", conn, params=(last_week,)).iloc[0]['h'] or 0
    # --- Tableau productivité ---
    prod = pd.DataFrame({
        "": ["Appels", "RDV", "Missions finies", "Heures travaillées"],
        "Aujourd'hui": [appels_today, rdv_today, missions_today, heures_today],
        "Hier": [appels_yesterday, rdv_yesterday, missions_yesterday, heures_yesterday],
        "Même jour S-1": [appels_lastweek, rdv_lastweek, missions_lastweek, heures_lastweek],
    })
    st.table(prod)
    # --- Indicateurs clés semaine ---
    semaine = today.isocalendar()[1]
    annee = today.year
    lundi = today - pd.Timedelta(days=today.weekday())
    dimanche = lundi + pd.Timedelta(days=6)
    with sqlite3.connect(DB_PATH) as conn:
        facture = pd.read_sql_query("SELECT SUM(prix) as s FROM commandes WHERE date(date_debut)>=? AND date(date_debut)<=?", conn, params=(lundi, dimanche)).iloc[0]['s'] or 0
        encaisse = pd.read_sql_query("SELECT SUM(argent_encaisse) as s FROM commandes WHERE date(date_debut)>=? AND date(date_debut)<=?", conn, params=(lundi, dimanche)).iloc[0]['s'] or 0
        appels = pd.read_sql_query("SELECT COUNT(*) as n FROM taches WHERE date(date_debut)>=? AND date(date_debut)<=? AND type_tache='tache'", conn, params=(lundi, dimanche)).iloc[0]['n']
        rdv = pd.read_sql_query("SELECT COUNT(*) as n FROM taches WHERE date(date_debut)>=? AND date(date_debut)<=? AND type_tache='r1'", conn, params=(lundi, dimanche)).iloc[0]['n']
        nouveaux_clients = pd.read_sql_query("SELECT COUNT(*) as n FROM clients WHERE date(date_conversion)>=? AND date(date_conversion)<=?", conn, params=(lundi, dimanche)).iloc[0]['n']
        missions = pd.read_sql_query("SELECT COUNT(*) as n FROM taches WHERE date(date_debut)>=? AND date(date_debut)<=? AND statut='terminé'", conn, params=(lundi, dimanche)).iloc[0]['n']
        projets_retard = pd.read_sql_query("SELECT COUNT(*) as n FROM commandes WHERE date(date_fin)<? AND statut!='livré'", conn, params=(today,)).iloc[0]['n']
        # Taux horaire moyen
        heures = pd.read_sql_query("SELECT SUM(temps_passe) as h FROM taches WHERE date(date_debut)>=? AND date(date_debut)<=?", conn, params=(lundi, dimanche)).iloc[0]['h'] or 0
        taux_horaire = round(facture / heures, 2) if heures else 0
    col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
    col1.metric("Facturé cette semaine", f"{facture:,.0f} €")
    col2.metric("Encaissé cette semaine", f"{encaisse:,.0f} €")
    col3.metric("Appels passés", appels)
    col4.metric("RDV générés", rdv)
    col5.metric("Nouveaux clients", nouveaux_clients)
    col6.metric("{}/h".format(taux_horaire if taux_horaire else 0), "Taux horaire moyen")
    col7.metric("Missions terminées", missions)
    col8.metric("Projets en retard", projets_retard)
    # --- Comparatif semaine/semaine ---
    st.subheader("Comparatif Semaine/Semaine")
    lundi_prec = lundi - pd.Timedelta(days=7)
    dimanche_prec = lundi_prec + pd.Timedelta(days=6)
    with sqlite3.connect(DB_PATH) as conn:
        facture_prec = pd.read_sql_query("SELECT SUM(prix) as s FROM commandes WHERE date(date_debut)>=? AND date(date_debut)<=?", conn, params=(lundi_prec, dimanche_prec)).iloc[0]['s'] or 0
        encaisse_prec = pd.read_sql_query("SELECT SUM(argent_encaisse) as s FROM commandes WHERE date(date_debut)>=? AND date(date_debut)<=?", conn, params=(lundi_prec, dimanche_prec)).iloc[0]['s'] or 0
        appels_prec = pd.read_sql_query("SELECT COUNT(*) as n FROM taches WHERE date(date_debut)>=? AND date(date_debut)<=? AND type_tache='tache'", conn, params=(lundi_prec, dimanche_prec)).iloc[0]['n']
        rdv_prec = pd.read_sql_query("SELECT COUNT(*) as n FROM taches WHERE date(date_debut)>=? AND date(date_debut)<=? AND type_tache='r1'", conn, params=(lundi_prec, dimanche_prec)).iloc[0]['n']
        nouveaux_clients_prec = pd.read_sql_query("SELECT COUNT(*) as n FROM clients WHERE date(date_conversion)>=? AND date(date_conversion)<=?", conn, params=(lundi_prec, dimanche_prec)).iloc[0]['n']
        missions_prec = pd.read_sql_query("SELECT COUNT(*) as n FROM taches WHERE date(date_debut)>=? AND date(date_debut)<=? AND statut='terminé'", conn, params=(lundi_prec, dimanche_prec)).iloc[0]['n']
        heures_prec = pd.read_sql_query("SELECT SUM(temps_passe) as h FROM taches WHERE date(date_debut)>=? AND date(date_debut)<=?", conn, params=(lundi_prec, dimanche_prec)).iloc[0]['h'] or 0
        taux_horaire_prec = round(facture_prec / heures_prec, 2) if heures_prec else 0
    def evol(val, prec):
        if prec == 0:
            return "+100%" if val > 0 else "0%"
        return f"{((val-prec)/prec)*100:+.1f}%"
    comp = pd.DataFrame({
        "Indicateur": ["Facturé", "Encaissé", "Appels", "RDV", "Nouveaux clients", "Taux horaire", "Missions terminées"],
        "Cette semaine": [
            f"{facture:,.0f} €",
            f"{encaisse:,.0f} €",
            str(appels),
            str(rdv),
            str(nouveaux_clients),
            f"{taux_horaire} €/h",
            str(missions)
        ],
        "Semaine dernière": [
            f"{facture_prec:,.0f} €",
            f"{encaisse_prec:,.0f} €",
            str(appels_prec),
            str(rdv_prec),
            str(nouveaux_clients_prec),
            f"{taux_horaire_prec} €/h",
            str(missions_prec)
        ],
        "Évolution": [evol(facture, facture_prec), evol(encaisse, encaisse_prec), evol(appels, appels_prec), evol(rdv, rdv_prec), evol(nouveaux_clients, nouveaux_clients_prec), evol(taux_horaire, taux_horaire_prec), evol(missions, missions_prec)]
    })
    st.table(comp)

elif page == "CRM Clients":
    with open("crm_clients.py", encoding="utf-8") as f:
        exec(f.read(), globals())
    
elif page == "Commandes":
    with open("commandes.py", encoding="utf-8") as f:
        exec(f.read(), globals())

elif page == "Checklists":
    with open("checklists.py", encoding="utf-8") as f:
        exec(f.read(), globals())

elif page == "Automatisation":
    st.title("Automatisation")
    sous_page = st.radio("Choisissez une section :", ["Facture", "Site internet"])
    if sous_page == "Facture":
        st.header("Automatisation - Facture")
        st.info("Ici, vous pourrez automatiser la gestion des factures.")
    elif sous_page == "Site internet":
        st.header("Automatisation - Site internet")
        st.info("Ici, vous pourrez automatiser la gestion des sites internet.")

elif page == "Générateur de site":
    st.title("Générateur de site internet")
    # Liste des templates disponibles
    template_files = glob('templates_sites/*.html')
    st.write(f"Templates trouvés : {template_files}")
    template_names = [os.path.basename(f) for f in template_files]
    template_choice = st.selectbox("Choisir un template", template_names)
    # Champs à remplir manuellement
    with st.form("infos_site_form"):
        nom = st.text_input("Nom de l'entreprise")
        variableadressecomplete = st.text_input("Adresse complète")
        variabletelephone = st.text_input("Téléphone")
        variablemail = st.text_input("Email")
        ville = st.text_input("Ville")
        datedecreation = st.text_input("Date de création")
        region = st.text_input("Région")
        enzo_parreira = st.text_input("Copyright / Nom de l'auteur")
        logo_url = st.text_input("URL du logo")
        submitted = st.form_submit_button("Prévisualiser")
    if submitted and template_choice:
        file_path = f'templates_sites/{template_choice}'
        st.write(f"Chemin du fichier tenté : {file_path}")
        if not os.path.exists(file_path):
            st.error(f"Le fichier {file_path} n'existe pas !")
            html = ""
        else:
            with st.spinner('Génération de la prévisualisation...'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    html = f.read()
                # Remplacement des balises (à adapter selon le template)
                # Remplacement par balises si elles existent, sinon par valeurs fixes
                html = html.replace('{{nom}}', nom)
                html = html.replace('{{adresse}}', variableadressecomplete)
                html = html.replace('{{telephone}}', variabletelephone)
                html = html.replace('{{email}}', variablemail)
                html = html.replace('{{ville}}', ville)
                html = html.replace('{{datedecreation}}', datedecreation)
                html = html.replace('{{region}}', region)
                html = html.replace('{{enzo_parreira}}', enzo_parreira)
                html = html.replace('{{logo_url}}', logo_url)
                # Remplacement des valeurs fixes si les balises ne sont pas présentes
                html = html.replace('25 Chem. des Prés, 91480 Quincy-sous-Sénart', variableadressecomplete)
                html = html.replace('Td.couverture.idf@gmail.com', variablemail)
                html = html.replace('0664684699', variabletelephone)
                html = html.replace('Quincy-Sous-Sénart', ville)
                html = html.replace('2016', datedecreation)
                html = html.replace("l'Essonne", region)
                html = html.replace('Copyright © 2024 GMB CORP', enzo_parreira)
                html = html.replace('https://demestre-couverture-quincy.fr/wp-content/uploads/2025/04/ChatGPT_Image_12_avr._2025_a_00_31_46-removebg-preview.png', logo_url)
                html = html.replace('https://cdn.prod.website-files.com/683bad57cdebe0a37a9c74a1/683bad57cdebe0a37a9c7556_Logo.svg', logo_url)
            st.subheader("HTML généré (debug) :")
            st.text_area("Code HTML généré", html, height=200)
            if not html.strip():
                st.error("Le HTML généré est vide !")
            else:
                st.subheader("Test d'affichage minimal :")
                st.components.v1.html(f"<h1>{nom}</h1>", height=100)
                st.subheader("Prévisualisation du site généré :")
                st.components.v1.html(html, height=800, scrolling=True)

def download_image(url, save_path):
    """Télécharge une image depuis une URL et la sauve dans le chemin spécifié"""
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return True
        else:
            st.error(f"Erreur lors du téléchargement de l'image: {response.status_code}")
            return False
    except Exception as e:
        st.error(f"Erreur lors du téléchargement de l'image: {str(e)}")
        return False

def page_generateur_site():
    st.title("Générateur de Site")
    
    # Upload d'image
    st.subheader("Ajouter une image")
    uploaded_file = st.file_uploader("Choisir une image", type=['png', 'jpg', 'jpeg'])
    if uploaded_file is not None:
        # Afficher l'image
        st.image(uploaded_file, caption=uploaded_file.name)
        
        # Bouton pour utiliser l'image
        if st.button("Utiliser cette image"):
            # Ici on peut traiter l'image temporairement sans la sauvegarder
            # Par exemple, l'afficher dans le template ou la convertir en base64
            st.success(f"Image {uploaded_file.name} prête à être utilisée dans le site")
    
    # Reste du code existant pour la génération de site
    # ... existing code ...