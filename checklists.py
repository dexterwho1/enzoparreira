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

tab1, tab2 = st.tabs(["Mes checklists", "Modèles de checklist"])

with tab1:
    # --- Liste des checklists existantes ---
    with sqlite3.connect(DB_PATH) as conn:
        checklists = pd.read_sql_query("SELECT * FROM checklists ORDER BY date_creation DESC", conn)
    if not checklists.empty:
        for _, cl in checklists.iterrows():
            st.subheader(f"Checklist : {cl['nom']}")
            st.write(cl['description'])
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
            with st.expander(f"{tpl['nom']}  ", expanded=False):
                st.write(tpl['description'])
                show_items = st.checkbox(f"Afficher les items", key=f"show_items_tpl_{tpl['id']}")
                if show_items:
                    with sqlite3.connect(DB_PATH) as conn:
                        items = pd.read_sql_query("SELECT * FROM checklist_template_items WHERE template_id=? ORDER BY ordre", conn, params=(tpl['id'],))
                    for idx, item in items.iterrows():
                        st.markdown(f"{idx+1}. {item['texte']}")
                if st.button(f"Ajouter un item", key=f"add_item_tpl_{tpl['id']}"):
                    st.session_state[f"show_add_item_tpl_{tpl['id']}"] = True
                if st.session_state.get(f"show_add_item_tpl_{tpl['id']}"):
                    with st.form(f"form_add_item_tpl_{tpl['id']}"):
                        texte = st.text_input("Texte de l'item")
                        ordre = st.number_input("Ordre", min_value=1, value=1)
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
                if st.button(f"Créer une checklist à partir de ce modèle", key=f"create_cl_from_tpl_{tpl['id']}"):
                    st.session_state['show_new_checklist'] = True
                    st.session_state['preselect_tpl_id'] = tpl['id']
                    st.session_state['preselect_tpl_nom'] = tpl['nom']
                    st.rerun()
                if st.button(f"Supprimer ce modèle", key=f"del_tpl_{tpl['id']}"):
                    with sqlite3.connect(DB_PATH) as conn:
                        c = conn.cursor()
                        c.execute("DELETE FROM checklist_template_items WHERE template_id=?", (tpl['id'],))
                        c.execute("DELETE FROM checklist_templates WHERE id=?", (tpl['id'],))
                        conn.commit()
                    st.success("Modèle supprimé !")
                    st.rerun()
    # Formulaire de création de checklist (seulement ici)
    if st.session_state.get('show_new_checklist'):
        with st.form("form_new_checklist"):
            nom = st.text_input("Nom de la checklist")
            description = st.text_area("Description")
            # Préselection du modèle si on vient de cliquer sur un modèle
            templates_options = ["Aucun"]
            templates_ids = [None]
            with sqlite3.connect(DB_PATH) as conn:
                templates_df = pd.read_sql_query("SELECT * FROM checklist_templates", conn)
                for _, t in templates_df.iterrows():
                    templates_options.append(t['nom'])
                    templates_ids.append(t['id'])
            preselect_tpl_id = st.session_state.get('preselect_tpl_id')
            preselect_tpl_nom = st.session_state.get('preselect_tpl_nom')
            if preselect_tpl_nom and preselect_tpl_nom in templates_options:
                idx_tpl = templates_options.index(preselect_tpl_nom)
            else:
                idx_tpl = 0
            template_label = st.selectbox("Modèle (optionnel)", templates_options, index=idx_tpl)
            tpl_id = templates_ids[templates_options.index(template_label)] if template_label != "Aucun" else None
            commandes_options = ["Aucune"]
            commandes_ids = [None]
            with sqlite3.connect(DB_PATH) as conn:
                commandes_df = pd.read_sql_query("SELECT c.commande_id, c.nom_service, cl.name as client FROM commandes c LEFT JOIN clients cl ON c.client_id = cl.client_id ORDER BY c.commande_id DESC", conn)
                for _, c in commandes_df.iterrows():
                    commandes_options.append(f"{c['client']} - {c['nom_service']} (ID:{c['commande_id']})")
                    commandes_ids.append(c['commande_id'])
            commande_label = st.selectbox("Associer à une commande (optionnel)", commandes_options)
            commande_id = commandes_ids[commandes_options.index(commande_label)] if commande_label != "Aucune" else None
            submitted = st.form_submit_button("Créer")
            if submitted and nom:
                with sqlite3.connect(DB_PATH) as conn:
                    c = conn.cursor()
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
                st.session_state['preselect_tpl_id'] = None
                st.session_state['preselect_tpl_nom'] = None
                st.rerun()
            if st.form_submit_button("Annuler"):
                st.session_state['show_new_checklist'] = False
                st.session_state['preselect_tpl_id'] = None
                st.session_state['preselect_tpl_nom'] = None
                st.rerun() 