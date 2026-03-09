import customtkinter as ctk
from tkinter import filedialog, messagebox
import json
import os
import re
import requests
import threading
from dotenv import load_dotenv
from PIL import Image

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()
TRELLO_API_KEY = os.getenv("TRELLO_API_KEY")
TRELLO_TOKEN = os.getenv("TRELLO_TOKEN")

def get_list_id(board_url, api_key, token):
    match = re.search(r'trello\.com/b/([a-zA-Z0-9]+)', board_url)
    if not match:
        raise ValueError("Lien Trello invalide. Utilisez un lien du type https://trello.com/b/... ")
    short_id = match.group(1)
    
    # 1. Obtenir le vrai ID du tableau avec l'Identifiant Court
    board_info_url = f"https://api.trello.com/1/boards/{short_id}"
    board_response = requests.get(board_info_url, params={"key": api_key, "token": token})
    if board_response.status_code != 200:
        raise ValueError(f"Impossible d'accéder au tableau Trello.\nErreur: {board_response.text}")
        
    true_board_id = board_response.json()['id']
    
    # 2. Récupérer les listes du tableau
    url = f"https://api.trello.com/1/boards/{true_board_id}/lists"
    query = {"key": api_key, "token": token}
    response = requests.get(url, params=query)
    
    if response.status_code == 200:
        lists = response.json()
        if lists:
            return lists[0]['id']
        else:
            # Le tableau est vide, on tente de créer une liste automatiquement
            create_url = "https://api.trello.com/1/lists"
            create_query = {
                "name": "Cartes Importées JSON",
                "idBoard": true_board_id,
                "key": api_key,
                "token": token
            }
            create_response = requests.post(create_url, params=create_query)
            if create_response.status_code == 200:
                return create_response.json()['id']
            else:
                # Afficher la vraie erreur de Trello
                raise ValueError(f"Le tableau est vide et la création automatique a échoué.\nErreur Trello: {create_response.text}")
    else:
        raise ValueError(f"Erreur (Code {response.status_code}): {response.text}")

def create_card(list_id, card_data, api_key, token):
    url = "https://api.trello.com/1/cards"
    query = {
        "idList": list_id,
        "key": api_key,
        "token": token,
        "name": card_data.get("name", "Sans nom"),
        "desc": card_data.get("desc", "")
    }
    response = requests.post(url, params=query)
    response.raise_for_status()


class TrelloApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Trello Sync Pro")
        self.geometry("650x700")
        self.resizable(False, False)
        
        # Configuration des couleurs et polices globales (Style Trello-esque moderne)
        ctk.set_appearance_mode("dark")
        self.configure(fg_color="#0F172A") # Deep Slate Blue background
        
        # Police principale
        self.font_main = ctk.CTkFont(family="Segoe UI", size=14)
        self.font_title = ctk.CTkFont(family="Segoe UI", size=26, weight="bold")
        self.font_btn = ctk.CTkFont(family="Segoe UI", size=15, weight="bold")
        
        # Header (Logo et Titre)
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(pady=(40, 20), fill="x")
        
        try:
            logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
            logo_image = ctk.CTkImage(Image.open(logo_path), size=(80, 80))
            self.logo_label = ctk.CTkLabel(self.header_frame, image=logo_image, text="")
            self.logo_label.pack(pady=(0, 10))
        except Exception:
            self.logo_label = ctk.CTkLabel(self.header_frame, text="[ LOGO ]", font=ctk.CTkFont(size=24, weight="bold"))
            self.logo_label.pack(pady=(0, 10))
            
        self.title_label = ctk.CTkLabel(self.header_frame, text="Trello Data Importer", font=self.font_title, text_color="#FFFFFF")
        self.title_label.pack()
        
        self.subtitle_label = ctk.CTkLabel(self.header_frame, text="Convertissez vos fichiers JSON en cartes Trello", font=self.font_main, text_color="#94A3B8")
        self.subtitle_label.pack()
        
        # Container Principal (Carte)
        self.card_frame = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=15, border_width=1, border_color="#334155")
        self.card_frame.pack(pady=10, padx=40, fill="both", expand=True)
        
        # Section Lien Trello
        self.link_label = ctk.CTkLabel(self.card_frame, text="🔗 Lien du tableau Trello", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color="#E2E8F0")
        self.link_label.pack(anchor="w", padx=30, pady=(30, 5))
        
        self.link_entry = ctk.CTkEntry(self.card_frame, 
                                       placeholder_text="https://trello.com/b/.......", 
                                       height=45, 
                                       font=self.font_main,
                                       fg_color="#0F172A",
                                       border_color="#334155",
                                       text_color="#FFFFFF",
                                       placeholder_text_color="#64748B",
                                       corner_radius=8)
        self.link_entry.pack(padx=30, fill="x")
        
        # Section Fichier JSON
        self.file_label = ctk.CTkLabel(self.card_frame, text="📄 Fichier de données JSON", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color="#E2E8F0")
        self.file_label.pack(anchor="w", padx=30, pady=(25, 5))
        
        self.file_frame = ctk.CTkFrame(self.card_frame, fg_color="transparent")
        self.file_frame.pack(fill="x", padx=30)
        
        self.file_entry = ctk.CTkEntry(self.file_frame, 
                                       placeholder_text="Aucun fichier sélectionné", 
                                       height=45, 
                                       font=self.font_main,
                                       fg_color="#0F172A",
                                       border_color="#334155",
                                       text_color="#FFFFFF",
                                       placeholder_text_color="#64748B",
                                       corner_radius=8)
        self.file_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.browse_btn = ctk.CTkButton(self.file_frame, 
                                        text="Parcourir", 
                                        height=45, 
                                        width=110, 
                                        font=self.font_btn,
                                        fg_color="#3B82F6", # Bleu clair
                                        hover_color="#2563EB",
                                        text_color="white",
                                        corner_radius=8,
                                        command=self.browse_file)
        self.browse_btn.pack(side="right")
        
        # Footer Action (Bouton et Statut)
        self.footer_frame = ctk.CTkFrame(self.card_frame, fg_color="transparent")
        self.footer_frame.pack(fill="both", expand=True, padx=30, pady=(30, 30))
        
        self.start_btn = ctk.CTkButton(self.footer_frame, 
                                       text="🚀 Lancer l'importation", 
                                       height=50, 
                                       font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                                       fg_color="#10B981", # Emerald Green
                                       hover_color="#059669",
                                       text_color="white",
                                       corner_radius=10,
                                       command=self.start_import)
        self.start_btn.pack(fill="x", pady=(0, 15))
        
        self.status_label = ctk.CTkLabel(self.footer_frame, text="Prêt à importer.", font=self.font_main, text_color="#94A3B8")
        self.status_label.pack()

    def browse_file(self):
        filename = filedialog.askopenfilename(title="Sélectionnez un fichier JSON", filetypes=[("Fichiers JSON", "*.json")])
        if filename:
            self.file_entry.delete(0, 'end')
            self.file_entry.insert(0, filename)
            
    def start_import(self):
        board_url = self.link_entry.get().strip()
        json_file = self.file_entry.get().strip()
        
        if not board_url or not json_file:
            messagebox.showwarning("Champs requis", "Veuillez spécifier le lien du tableau Trello et le fichier JSON.")
            return
            
        if not TRELLO_API_KEY or not TRELLO_TOKEN or "votre" in TRELLO_API_KEY.lower() or "votre" in TRELLO_TOKEN.lower():
            messagebox.showerror("Authentification", "Veuillez mettre vos vraies clés Trello (TRELLO_API_KEY et TRELLO_TOKEN) dans le fichier .env.")
            return
            
        self.status_label.configure(text="⏳ Connexion à Trello... Création des cartes...", text_color="#F59E0B") # Amber
        self.start_btn.configure(state="disabled", text="⏳ Traitement...", fg_color="#64748B")
        
        threading.Thread(target=self.process_import, args=(board_url, json_file), daemon=True).start()

    def process_import(self, board_url, json_file):
        try:
            list_id = get_list_id(board_url, TRELLO_API_KEY, TRELLO_TOKEN)
            
            with open(json_file, 'r', encoding='utf-8') as f:
                cards = json.load(f)
                
            if not isinstance(cards, list):
                raise ValueError("Format JSON invalide : doit être une liste d'objets (cartes).")
                
            for index, card in enumerate(cards, start=1):
                self.status_label.configure(text=f"⏳ Création de la carte {index}/{len(cards)}...")
                create_card(list_id, card, TRELLO_API_KEY, TRELLO_TOKEN)
                
            self.status_label.configure(text="✅ Importation réussie ! Toutes les cartes ont été ajoutées.", text_color="#10B981") # Emerald
            messagebox.showinfo("Succès 🎉", f"{len(cards)} cartes ont été créées avec succès sur votre tableau Trello !")
            
        except json.JSONDecodeError:
            self.status_label.configure(text="❌ Erreur de lecture du JSON.", text_color="#EF4444")
            messagebox.showerror("Erreur JSON", "Le fichier JSON sélectionné est corrompu ou mal formaté.")
        except Exception as e:
            self.status_label.configure(text="❌ Une erreur est survenue.", text_color="#EF4444")
            messagebox.showerror("Erreur d'importation", str(e))
        finally:
            self.start_btn.configure(state="normal", text="🚀 Lancer l'importation", fg_color="#10B981")
            
if __name__ == "__main__":
    app = TrelloApp()
    app.mainloop()
