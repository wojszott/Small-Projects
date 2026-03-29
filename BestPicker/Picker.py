import os
import random
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ArenaApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("BestPicker")
        self.geometry("900x600")

        # Dane
        self.all_items = []  # Lista słowników {'name': str, 'path': str}
        self.queue = []  # Aktualna runda
        self.winners = []  # Zwycięzcy rundy
        self.left_item = None
        self.right_item = None
        self.mode = None  # "bracket" lub "hill"

        self.setup_menu()

    def setup_menu(self):
        self.clear_screen()

        self.label = ctk.CTkLabel(self, text="Choose the folder with pictures", font=("Arial", 24))
        self.label.pack(pady=40)

        self.btn_load = ctk.CTkButton(self, text="Load folder", command=self.load_folder)
        self.btn_load.pack(pady=10)

        self.mode_frame = ctk.CTkFrame(self)
        self.mode_frame.pack(pady=20)

        self.btn_bracket = ctk.CTkButton(self.mode_frame, text="Mode: Bracket", state="disabled",
                                         command=lambda: self.start_game("bracket"))
        self.btn_bracket.grid(row=0, column=0, padx=10)

        self.btn_hill = ctk.CTkButton(self.mode_frame, text="Mode: King on the Hill", state="disabled",
                                      command=lambda: self.start_game("hill"))
        self.btn_hill.grid(row=0, column=1, padx=10)

    def load_folder(self):
        folder = filedialog.askdirectory()
        if not folder:
            return

        self.all_items = []
        for file in os.listdir(folder):
            if file.lower().endswith(".png"):
                name = os.path.splitext(file)[0]
                self.all_items.append({
                    "name": name,
                    "path": os.path.join(folder, file),
                    "wins": 0
                })

        if len(self.all_items) < 2:
            messagebox.showerror("Error", "Yuo need at least 2 PNG files!")
        else:
            self.label.configure(text=f"Loaded: {len(self.all_items)} files")
            self.btn_bracket.configure(state="normal")
            self.btn_hill.configure(state="normal")

    def start_game(self, mode):
        self.mode = mode
        self.queue = list(self.all_items)
        random.shuffle(self.queue)
        self.winners = []
        self.setup_arena()
        self.next_match()

    def setup_arena(self):
        self.clear_screen()
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Lewy kontener
        self.left_container = ctk.CTkFrame(self, corner_radius=15, border_width=2)
        self.left_container.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

        # Obraz lewy
        self.left_img_label = ctk.CTkLabel(self.left_container, text="")
        self.left_img_label.pack(expand=True, fill="both", padx=5, pady=5)

        #  Tytuł lewy
        self.left_name_label = ctk.CTkLabel(
            self.left_container,
            text="",
            font=("Verdana", 24, "bold"),
            text_color="#493fa1",  # Złoty kolor dla lepszej widoczności
            fg_color="#1A1A1A",  # Ciemne tło pod napisem
            corner_radius=8,
            height=45
        )
        self.left_name_label.pack(pady=(0, 15), padx=20, fill="x")

        self.left_btn = ctk.CTkButton(self.left_container, text="WYBIERZ", command=lambda: self.select(0),
                                      font=("Arial", 14, "bold"))
        self.left_btn.pack(pady=(0, 20))

        # Prawy kontener
        self.right_container = ctk.CTkFrame(self, corner_radius=15, border_width=2)
        self.right_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        # Obraz prawy
        self.right_img_label = ctk.CTkLabel(self.right_container, text="")
        self.right_img_label.pack(expand=True, fill="both", padx=5, pady=5)

        # Tytuł prawy
        self.right_name_label = ctk.CTkLabel(
            self.right_container,
            text="",
            font=("Verdana", 24, "bold"),
            text_color="#9e4f35",
            fg_color="#1A1A1A",
            corner_radius=8,
            height=45
        )
        self.right_name_label.pack(pady=(0, 15), padx=20, fill="x")

        self.right_btn = ctk.CTkButton(self.right_container, text="WYBIERZ", command=lambda: self.select(1),
                                       font=("Arial", 14, "bold"))
        self.right_btn.pack(pady=(0, 20))
        self.right_btn.pack(pady=10)

    def next_match(self):
        if self.mode == "bracket":
            if len(self.queue) < 2:
                if not self.winners:  # Koniec gry
                    self.show_winner(self.queue[0])
                    return
                # Przejście do następnej rundy
                self.queue.extend(self.winners)
                self.winners = []
                if len(self.queue) < 2:
                    self.show_winner(self.queue[0])
                    return

            self.left_item = self.queue.pop(0)
            self.right_item = self.queue.pop(0)

        elif self.mode == "hill":
            if not self.left_item:
                self.left_item = self.queue.pop(0)

            if not self.queue:
                self.show_winner(self.left_item)
                return

            self.right_item = self.queue.pop(0)

        self.update_ui()

    def update_ui(self):
        img_size = (400, 400)

        # Lewy
        l_img = Image.open(self.left_item['path'])
        l_ctk = ctk.CTkImage(light_image=l_img, dark_image=l_img, size=img_size)
        self.left_img_label.configure(image=l_ctk)
        # Formatowanie tekstu: Nazwa z pliku, zamiana podkreślników na spacje i Duże Litery
        pretty_name_l = self.left_item['name'].replace("_", " ").upper()
        self.left_name_label.configure(text=pretty_name_l)

        # Prawy
        r_img = Image.open(self.right_item['path'])
        r_ctk = ctk.CTkImage(light_image=r_img, dark_image=r_img, size=img_size)
        self.right_img_label.configure(image=r_ctk)
        pretty_name_r = self.right_item['name'].replace("_", " ").upper()
        self.right_name_label.configure(text=pretty_name_r)

    def select(self, side):
        if side == 0:
            winner, loser = self.left_item, self.right_item
        else:
            winner, loser = self.right_item, self.left_item

        # KLUCZOWA ZMIANA:
        winner['wins'] += 1

        if self.mode == "bracket":
            self.winners.append(winner)
        else:
            self.left_item = winner

        self.next_match()

    def show_winner(self, winner):
        self.clear_screen()
        lbl = ctk.CTkLabel(self, text=f"Winner:\n{winner['name']}", font=("Arial", 32, "bold"))
        lbl.pack(pady=50)

        img = Image.open(winner['path'])
        img_ctk = ctk.CTkImage(light_image=img, dark_image=img, size=(350, 350))
        ctk.CTkLabel(self, image=img_ctk, text="").pack()

        ctk.CTkButton(self, text="Statistics", command=self.show_statistics).pack(pady=20)

    def show_statistics(self):
        self.clear_screen()

        # Tytuł
        ctk.CTkLabel(self, text="End Ranking", font=("Verdana", 28, "bold"), text_color="#FFCC00").pack(pady=20)

        # Przewijalna lista (Scrollable Frame)
        stats_frame = ctk.CTkScrollableFrame(self, width=600, height=400)
        stats_frame.pack(pady=10, padx=20, fill="both", expand=True)

        # Sortowanie zawodników po liczbie zwycięstw (od największej)
        ranked_list = sorted(self.all_items, key=lambda x: x['wins'], reverse=True)

        for i, item in enumerate(ranked_list):
            # Kolor dla podium
            color = "#FFD700" if i == 0 else "#C0C0C0" if i == 1 else "#CD7F32" if i == 2 else "#FFFFFF"

            row = ctk.CTkFrame(stats_frame, fg_color="transparent")
            row.pack(fill="x", pady=5)

            # Numer miejsca, nazwa i liczba wygranych
            place_label = ctk.CTkLabel(row, text=f"{i + 1}.", font=("Arial", 18, "bold"), text_color=color, width=50)
            place_label.pack(side="left", padx=10)

            name_label = ctk.CTkLabel(row, text=item['name'].upper(), font=("Arial", 16), anchor="w")
            name_label.pack(side="left", padx=10, fill="x", expand=True)

            wins_label = ctk.CTkLabel(row, text=f"Wins: {item['wins']}", font=("Arial", 14, "italic"))
            wins_label.pack(side="right", padx=20)

        # Przycisk powrotu do menu na samym dole
        ctk.CTkButton(self, text="Main menu", command=self.setup_menu).pack(pady=20)

    def clear_screen(self):
        for widget in self.winfo_children():
            widget.destroy()


if __name__ == "__main__":
    app = ArenaApp()
    app.mainloop()