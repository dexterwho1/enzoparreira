import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = "crm_data.db"

# --- Création des tables si besoin ---
def init_checklist_tables():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS checklist_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT,
            description TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS checklist_template_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id INTEGER,
            texte TEXT,
            ordre INTEGER,
            FOREIGN KEY(template_id) REFERENCES checklist_templates(id)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS checklists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT,
            description TEXT,
            commande_id INTEGER,
            process_id INTEGER,
            template_id INTEGER,
            date_creation TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS checklist_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            checklist_id INTEGER,
            texte TEXT,
            fait INTEGER,
            ordre INTEGER,
            FOREIGN KEY(checklist_id) REFERENCES checklists(id)
        )''')
        conn.commit()

init_checklist_tables()

st.title("Checklists")

# --- Filtres avancés ---
tab1, tab2 = st.tabs(["Mes checklists", "Modèles de checklist"])

with tab1:
    # Filtres principaux
    filtre_type = st.radio("Associer avec :", ["Toutes", "Commande", "Process", "Market", "Aucune"], horizontal=True)
    commande_id = process_id = market_id = None
    commandes_options, commandes_df = get_commandes_options()
    # Dummy pour process/market (à adapter selon ta structure réelle)
    process_options = ["Aucun"] + [f"Process {i}" for i in range(1, 4)]
    market_options = ["Aucun"] + [f"Market {i}" for i in range(1, 3)]
    if filtre_type == "Commande":
        commande_label = st.selectbox("Choisir une commande", ["Aucune"] + commandes_options)
        if commande_label != "Aucune":
            commande_id = int(commande_label.split("ID:")[-1].replace(")", ""))
    elif filtre_type == "Process":
        process_label = st.selectbox("Choisir un process", process_options)
        if process_label != "Aucun":
            process_id = int(process_label.split(" ")[-1])
    elif filtre_type == "Market":
        market_label = st.selectbox("Choisir un market", market_options)
        if market_label != "Aucun":
            market_id = int(market_label.split(" ")[-1])

    # --- Récupération des checklists filtrées ---
    query = "SELECT * FROM checklists"
    params = []
    where = []
    if filtre_type == "Commande" and commande_id:
        where.append("commande_id=?")
        params.append(commande_id)
    elif filtre_type == "Process" and process_id:
        where.append("process_id=?")
        params.append(process_id)
    elif filtre_type == "Market" and market_id:
        where.append("template_id=?")
        params.append(market_id)
    elif filtre_type == "Aucune":
        where.append("commande_id IS NULL AND process_id IS NULL AND template_id IS NULL")
    if where:
        query += " WHERE " + " AND ".join(where)
    query += " ORDER BY date_creation DESC"
    with sqlite3.connect(DB_PATH) as conn:
        checklists = pd.read_sql_query(query, conn, params=params)

    # --- Couleurs par type d'association ---
    def get_bulle_color(cl):
        if cl['commande_id']:
            return "#e3f2fd", "Commande"
        elif cl['process_id']:
            return "#e8f5e9", "Process"
        elif cl['template_id']:
            return "#fff3e0", "Market"
        else:
            return "#ececec", "Aucune"

    if st.button("Créer une checklist"):
        st.session_state['show_new_checklist'] = True
    if st.session_state.get('show_new_checklist'):
        with st.form("form_new_checklist"):
            nom = st.text_input("Nom de la checklist")
            description = st.text_area("Description")
            commande_label = st.selectbox("Associer à une commande (optionnel)", ["Aucune"] + commandes_options)
            commande_id = None
            if commande_label != "Aucune":
                commande_id = int(commande_label.split("ID:")[-1].replace(")", ""))
            templates_options, templates_df = get_templates_options()
            template_label = st.selectbox("Modèle (optionnel)", templates_options)
            submitted = st.form_submit_button("Créer")
            if submitted and nom:
                with sqlite3.connect(DB_PATH) as conn:
                    c = conn.cursor()
                    tpl_id = None
                    if template_label != "Aucun":
                        tpl_id = templates_df[templates_df['nom'] == template_label]['id'].iloc[0]
                    c.execute("INSERT INTO checklists (nom, description, commande_id, process_id, template_id, date_creation) VALUES (?, ?, ?, ?, ?, ?)", (nom, description, commande_id, None, tpl_id, datetime.now().isoformat()))
                    checklist_id = c.lastrowid
                    # Si modèle choisi, pré-remplir les items
                    if tpl_id:
                        items = pd.read_sql_query("SELECT * FROM checklist_template_items WHERE template_id=? ORDER BY ordre", conn, params=(tpl_id,))
                        for i, item in items.iterrows():
                            c.execute("INSERT INTO checklist_items (checklist_id, texte, fait, ordre) VALUES (?, ?, 0, ?)", (checklist_id, item['texte'], item['ordre']))
                    conn.commit()
                st.success("Checklist créée !")
                st.session_state['show_new_checklist'] = False
                st.rerun()
            if st.form_submit_button("Annuler"):
                st.session_state['show_new_checklist'] = False
                st.rerun()

    if not checklists.empty:
        for _, cl in checklists.iterrows():
            color, type_label = get_bulle_color(cl)
            st.markdown(f"""
            <div style='background:{color};border-radius:15px;padding:20px;margin-bottom:20px;'>
                <h4 style='margin-bottom:5px;'>{cl['nom']} <span style='font-size:0.8em;background:#bbb;border-radius:8px;padding:2px 8px;margin-left:10px;'>{type_label}</span></h4>
                <p style='margin-top:0;color:#555;'>{cl['description']}</p>
            """, unsafe_allow_html=True)
            with sqlite3.connect(DB_PATH) as conn:
                items = pd.read_sql_query("SELECT * FROM checklist_items WHERE checklist_id=? ORDER BY ordre", conn, params=(cl['id'],))
            for idx, item in items.iterrows():
                checked = st.checkbox(item['texte'], value=bool(item['fait']), key=f"cl_item_{item['id']}")
                if checked != bool(item['fait']):
                    with sqlite3.connect(DB_PATH) as conn:
                        c = conn.cursor()
                        c.execute("UPDATE checklist_items SET fait=? WHERE id=?", (int(checked), item['id']))
                        conn.commit()
            if st.button(f"Ajouter un item", key=f"add_item_cl_{cl['id']}"):
                st.session_state[f"show_add_item_cl_{cl['id']}"] = True
            if st.session_state.get(f"show_add_item_cl_{cl['id']}"):
                with st.form(f"form_add_item_cl_{cl['id']}"):
                    texte = st.text_input("Texte de l'item")
                    ordre = st.number_input("Ordre", min_value=1, value=len(items)+1)
                    if st.form_submit_button("Ajouter") and texte:
                        with sqlite3.connect(DB_PATH) as conn:
                            c = conn.cursor()
                            c.execute("INSERT INTO checklist_items (checklist_id, texte, fait, ordre) VALUES (?, ?, 0, ?)", (cl['id'], texte, ordre))
                            conn.commit()
                        st.success("Item ajouté !")
                        st.session_state[f"show_add_item_cl_{cl['id']}"] = False
                        st.rerun()
                    if st.form_submit_button("Annuler"):
                        st.session_state[f"show_add_item_cl_{cl['id']}"] = False
                        st.rerun()
            if st.button(f"Supprimer cette checklist", key=f"del_cl_{cl['id']}"):
                with sqlite3.connect(DB_PATH) as conn:
                    c = conn.cursor()
                    c.execute("DELETE FROM checklist_items WHERE checklist_id=?", (cl['id'],))
                    c.execute("DELETE FROM checklists WHERE id=?", (cl['id'],))
                    conn.commit()
                st.success("Checklist supprimée !")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

with tab2:
    st.header("Modèles de checklist")
    with sqlite3.connect(DB_PATH) as conn:
        templates = pd.read_sql_query("SELECT * FROM checklist_templates", conn)
    if st.button("Créer un modèle de checklist"):
        st.session_state['show_new_template'] = True
    if st.session_state.get('show_new_template'):
        with st.form("form_new_template"):
            nom = st.text_input("Nom du modèle")
            description = st.text_area("Description")
            submitted = st.form_submit_button("Créer")
            if submitted and nom:
                with sqlite3.connect(DB_PATH) as conn:
                    c = conn.cursor()
                    c.execute("INSERT INTO checklist_templates (nom, description) VALUES (?, ?)", (nom, description))
                    conn.commit()
                st.success("Modèle créé !")
                st.session_state['show_new_template'] = False
                st.rerun()
            if st.form_submit_button("Annuler"):
                st.session_state['show_new_template'] = False
                st.rerun()
    if not templates.empty:
        for _, tpl in templates.iterrows():
            st.subheader(f"Modèle : {tpl['nom']}")
            st.write(tpl['description'])
            with sqlite3.connect(DB_PATH) as conn:
                items = pd.read_sql_query("SELECT * FROM checklist_template_items WHERE template_id=? ORDER BY ordre", conn, params=(tpl['id'],))
            for idx, item in items.iterrows():
                st.markdown(f"{idx+1}. {item['texte']}")
            if st.button(f"Ajouter un item", key=f"add_item_tpl_{tpl['id']}"):
                st.session_state[f"show_add_item_tpl_{tpl['id']}"] = True
            if st.session_state.get(f"show_add_item_tpl_{tpl['id']}"):
                with st.form(f"form_add_item_tpl_{tpl['id']}"):
                    texte = st.text_input("Texte de l'item")
                    ordre = st.number_input("Ordre", min_value=1, value=len(items)+1)
                    if st.form_submit_button("Ajouter") and texte:
                        with sqlite3.connect(DB_PATH) as conn:
                            c = conn.cursor()
                            c.execute("INSERT INTO checklist_template_items (template_id, texte, ordre) VALUES (?, ?, ?)", (tpl['id'], texte, ordre))
                            conn.commit()
                        st.success("Item ajouté !")
                        st.session_state[f"show_add_item_tpl_{tpl['id']}"] = False
                        st.rerun()
                    if st.form_submit_button("Annuler"):
                        st.session_state[f"show_add_item_tpl_{tpl['id']}"] = False
                        st.rerun()
            if st.button(f"Supprimer ce modèle", key=f"del_tpl_{tpl['id']}"):
                with sqlite3.connect(DB_PATH) as conn:
                    c = conn.cursor()
                    c.execute("DELETE FROM checklist_template_items WHERE template_id=?", (tpl['id'],))
                    c.execute("DELETE FROM checklist_templates WHERE id=?", (tpl['id'],))
                    conn.commit()
                st.success("Modèle supprimé !")
                st.rerun()

# --- DEBUG : Afficher les tables et leur contenu (5 premières lignes) ---
if __name__ == "__main__":
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    print("Tables dans la base de données :")
    for row in c.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        print("-", row[0])
        table = row[0]
        res = c.execute(f"SELECT * FROM {table} LIMIT 5").fetchall()
        print("  5 premières lignes :", res)
    conn.close() 