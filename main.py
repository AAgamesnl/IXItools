from __future__ import annotations

"""IXINA Tools GUI – hoofdmenu
===============================
Enkel het deel voor **Toestellenmanager** is aangepast:
• De placeholder‑klasse is verwijderd.
• We importeren nu `ApplianceManagerWindow` uit `ApplianceManagerFrame`.
Alle andere functionalitefit blijft ongewijzigd.
"""

from pathlib import Path
from tkinter import messagebox
import tkinter as tk
from typing import Tuple

import customtkinter as ctk
from PIL import Image, ImageOps

# ↳ nieuwe import uit aparte module
from ApplianceManagerFrame import ApplianceManagerWindow

# ───────────────────────────────────────────────────────────────────────────────
#  BASIS‑INSTELLINGEN & CONSTANTEN
# ───────────────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

TITLE = "IXINA tools"
VERSION = "Versie v0.7.28.06.25"
AUTHOR = "aelyaakoubi@ixina.com"
LABEL_TEXT = "Ixina Tools"

BUTTON_LABELS: Tuple[str, ...] = (
    "Elementenlijst\n(alpha – binnenkort)",
    "Steen berekening\n(alpha – binnenkort)",
    "Toestellenmanager",
)

BASE_DIR = Path(__file__).parent
LOGO_IMAGE_PATH = BASE_DIR / "logo.png"

# ───────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ───────────────────────────────────────────────────────────────────────────────

def load_ctk_image(path: Path | str, size: tuple[int, int] | None = None) -> ctk.CTkImage:
    """Return CTkImage; placeholder if bestand ontbreekt."""
    img_path = Path(path)
    if img_path.is_file():
        img = Image.open(img_path)
        if size:
            img = ImageOps.contain(img, size, method=Image.LANCZOS)
    else:
        w, h = size or (150, 45)
        img = Image.new("RGB", (w, h), color="grey")
    return ctk.CTkImage(img, size=size)

# ───────────────────────────────────────────────────────────────────────────────
#  HOOFD‑APPLICATIE
# ───────────────────────────────────────────────────────────────────────────────

class IxinaToolsApp(ctk.CTk):
    """Main window."""

    def __init__(self) -> None:  # noqa: D401
        super().__init__()
        self.icon_image = tk.PhotoImage(file=LOGO_IMAGE_PATH)
        self.iconphoto(False, self.icon_image)
        self.title(TITLE)
        self.minsize(900, 300)

        self.columnconfigure((0, 1, 2, 3), weight=1)
        # Plaats de grid-inhoud steeds bovenaan wanneer het venster groter wordt
        self.grid_anchor("n")

        self._create_header_section()
        self._create_button_section()

    # ───────────────────────────────────────────────────────────────────────
    #  UI Builders
    # ───────────────────────────────────────────────────────────────────────

    def _create_header_section(self) -> None:
        logo_img = load_ctk_image(LOGO_IMAGE_PATH, size=(150, 45))
        ctk.CTkLabel(self, image=logo_img, text="").grid(
            row=0, column=0, padx=20, pady=(20, 5), sticky="nw"
        )
        ctk.CTkLabel(self, text=LABEL_TEXT, font=("Helvetica", 24, "bold"), anchor="center").grid(
            row=0, column=1, columnspan=3, pady=20
        )
        ctk.CTkLabel(self, text=AUTHOR, font=("Helvetica", 12)).grid(
            row=1, column=0, sticky="w", padx=20
        )
        ctk.CTkLabel(self, text=VERSION, font=("Helvetica", 12)).grid(
            row=1, column=3, sticky="e", padx=20
        )

    def _create_button_section(self) -> None:
        font_cfg = ("Helvetica", 15)
        for idx, label in enumerate(BUTTON_LABELS, start=1):
            frame = ctk.CTkFrame(self, width=280, height=150)
            frame.grid(row=2, column=idx, padx=15, pady=20, sticky="nsew")
            frame.rowconfigure(0, weight=1)
            frame.columnconfigure(0, weight=1)

            # detecteer case‑onafhankelijk “toestellenmanager”
            if "toestellenmanager" in label.lower():
                cmd = self._open_manager
            else:
                cmd = lambda: messagebox.showinfo("Nog niet beschikbaar", "Deze functie is in ontwikkeling.")

            ctk.CTkButton(
                frame,
                text=label,
                command=cmd,
                font=font_cfg,
                corner_radius=10,
                hover_color="gray",
            ).grid(sticky="nsew")

    # ------------------------------------------------------------------
    def _open_manager(self) -> None:
        """Verberg hoofdvenster en open ApplianceManagerWindow."""
        self.withdraw()
        manager = ApplianceManagerWindow(self)
        manager.protocol("WM_DELETE_WINDOW", lambda: (manager.destroy(), self.deiconify()))

# ───────────────────────────────────────────────────────────────────────────────
#  ENTRY‑POINT
# ───────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    IxinaToolsApp().mainloop()
