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

st.title("Gestion des checklists & modèles")

# --- Section : Modèles de checklist ---
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
            st.session_state[f'show_add_item_tpl_{tpl['id']}'] = True
        if st.session_state.get(f'show_add_item_tpl_{tpl['id']}'):
            with st.form(f"form_add_item_tpl_{tpl['id']}"):
                texte = st.text_input("Texte de l'item")
                ordre = st.number_input("Ordre", min_value=1, value=len(items)+1)
                if st.form_submit_button("Ajouter") and texte:
                    with sqlite3.connect(DB_PATH) as conn:
                        c = conn.cursor()
                        c.execute("INSERT INTO checklist_template_items (template_id, texte, ordre) VALUES (?, ?, ?)", (tpl['id'], texte, ordre))
                        conn.commit()
                    st.success("Item ajouté !")
                    st.session_state[f'show_add_item_tpl_{tpl['id']}'] = False
                    st.rerun()
                if st.form_submit_button("Annuler"):
                    st.session_state[f'show_add_item_tpl_{tpl['id']}'] = False
                    st.rerun()
        if st.button(f"Supprimer ce modèle", key=f"del_tpl_{tpl['id']}"):
            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                c.execute("DELETE FROM checklist_template_items WHERE template_id=?", (tpl['id'],))
                c.execute("DELETE FROM checklist_templates WHERE id=?", (tpl['id'],))
                conn.commit()
            st.success("Modèle supprimé !")
            st.rerun()

st.write("---")

# --- Section : Checklists existantes ---
st.header("Checklists")
with sqlite3.connect(DB_PATH) as conn:
    checklists = pd.read_sql_query("SELECT * FROM checklists ORDER BY date_creation DESC", conn)
if st.button("Créer une checklist"):
    st.session_state['show_new_checklist'] = True
if st.session_state.get('show_new_checklist'):
    with st.form("form_new_checklist"):
        nom = st.text_input("Nom de la checklist")
        description = st.text_area("Description")
        with sqlite3.connect(DB_PATH) as conn:
            templates = pd.read_sql_query("SELECT * FROM checklist_templates", conn)
        template_id = st.selectbox("Modèle (optionnel)", ["Aucun"] + templates['nom'].tolist()) if not templates.empty else "Aucun"
        commande_id = st.text_input("ID Commande (optionnel)")
        process_id = st.text_input("ID Process (optionnel)")
        submitted = st.form_submit_button("Créer")
        if submitted and nom:
            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                tpl_id = None
                if template_id != "Aucun":
                    tpl_id = templates[templates['nom'] == template_id]['id'].iloc[0]
                c.execute("INSERT INTO checklists (nom, description, commande_id, process_id, template_id, date_creation) VALUES (?, ?, ?, ?, ?, ?)", (nom, description, commande_id or None, process_id or None, tpl_id, datetime.now().isoformat()))
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
            st.session_state[f'show_add_item_cl_{cl['id']}'] = True
        if st.session_state.get(f'show_add_item_cl_{cl['id']}'):
            with st.form(f"form_add_item_cl_{cl['id']}"):
                texte = st.text_input("Texte de l'item")
                ordre = st.number_input("Ordre", min_value=1, value=len(items)+1)
                if st.form_submit_button("Ajouter") and texte:
                    with sqlite3.connect(DB_PATH) as conn:
                        c = conn.cursor()
                        c.execute("INSERT INTO checklist_items (checklist_id, texte, fait, ordre) VALUES (?, ?, 0, ?)", (cl['id'], texte, ordre))
                        conn.commit()
                    st.success("Item ajouté !")
                    st.session_state[f'show_add_item_cl_{cl['id']}'] = False
                    st.rerun()
                if st.form_submit_button("Annuler"):
                    st.session_state[f'show_add_item_cl_{cl['id']}'] = False
                    st.rerun()
        if st.button(f"Supprimer cette checklist", key=f"del_cl_{cl['id']}"):
            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                c.execute("DELETE FROM checklist_items WHERE checklist_id=?", (cl['id'],))
                c.execute("DELETE FROM checklists WHERE id=?", (cl['id'],))
                conn.commit()
            st.success("Checklist supprimée !")
            st.rerun() 