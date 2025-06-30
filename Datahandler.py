import openpyxl
import os
import GOT
import Elementen
import shutil
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox

from openpyxl import Workbook
# Get the output data from GOT.py
data = GOT.get_output()

# Load an existing Workbook
wb = openpyxl.load_workbook('Opmetingsaanvraag.xlsx')

# Select the active worksheet
ws = wb.active

# Dictionary of the specific cells where you want to put each line
# Here, replace the cell addresses with your own
cells = {
    1: 'C6',
    2: 'C7',
    3: 'C9',
    4: 'C10',
    5: 'D12',
    6: 'G6',
}

# Write each line into its specific cell
for i, line in enumerate(data, 1):
    ws[cells[i]] = line


total_count_onderkasten_kolomkasten = Elementen.count_onderkasten_kolomkasten(Elementen.filename, Elementen.target_words_onderkasten_kolomkasten)
total_count_Hangkasten = Elementen.count_Hangkasten(Elementen.filename, Elementen.target_words_Hangkasten)
total_count_plinten = Elementen.count_plinten(Elementen.filename, Elementen.target_words_plinten)
total_count_Kroonlijsten = Elementen.count_Kroonlijsten(Elementen.filename, Elementen.target_words_Kroonlijsten)
total_count_Lichtlijsten = Elementen.count_Lichtlijsten(Elementen.filename, Elementen.target_words_Lichtlijsten)
total_count_Werkbladen = Elementen.count_Werkbladen(Elementen.filename, Elementen.target_words_Werkbladen)
total_count_Spoelbak_kraan = Elementen.count_Spoelbak_kraan(Elementen.filename, Elementen.target_words_Spoelbak_kraan)
total_count_Kookplaat = Elementen.count_Kookplaat(Elementen.filename, Elementen.target_words_Kookplaat)
total_count_Dampkap = Elementen.count_Dampkap(Elementen.filename, Elementen.target_words_Dampkap)
total_count_Oven = Elementen.count_Oven(Elementen.filename, Elementen.target_words_Oven)
total_count_Microgolfoven = Elementen.count_Microgolfoven(Elementen.filename, Elementen.target_words_Microgolfoven)
total_count_koelkast = Elementen.count_koelkast(Elementen.filename, Elementen.target_words_koelkast)
total_count_Vaatwasser = Elementen.count_Vaatwasser(Elementen.filename, Elementen.target_words_Vaatwasser)
total_count_Passtukken = Elementen.count_Passtukken(Elementen.filename, Elementen.target_words_Passtukken)
total_count_Deur_vaatwasser = Elementen.count_Deur_vaatwasser(Elementen.filename, Elementen.target_words_Deur_vaatwasser)
total_count_Achterwand = Elementen.count_Achterwand(Elementen.filename, Elementen.target_words_Achterwand)
total_count_Zij_steunwand = Elementen.count_Zij_steunwand(Elementen.filename, Elementen.target_words_Zij_steunwand)
total_count_Andere = Elementen.count_Andere(Elementen.filename, Elementen.target_words_Andere)
total_count_Verlichting = Elementen.count_Verlichting(Elementen.filename, Elementen.target_words_Verlichting)

ws['E15'] = total_count_onderkasten_kolomkasten
ws['E16'] = total_count_Hangkasten
ws['E17'] = total_count_plinten
ws['E18'] = total_count_Kroonlijsten
ws['E19'] = total_count_Lichtlijsten
ws['E20'] = total_count_Werkbladen
ws['E21'] = total_count_Spoelbak_kraan
ws['E22'] = total_count_Kookplaat
ws['E23'] = total_count_Dampkap
ws['E24'] = total_count_Oven
ws['E25'] = total_count_Microgolfoven
ws['E26'] = total_count_koelkast
ws['E27'] = total_count_Vaatwasser
ws['E30'] = total_count_Passtukken
ws['E33'] = total_count_Deur_vaatwasser
ws['E34'] = total_count_Achterwand
ws['E35'] = total_count_Zij_steunwand
ws['E37'] = total_count_Andere
ws['E38'] = total_count_Verlichting


# Assuming 'wb' is your Workbook object
wb.save('Opmetingsaanvraag.xlsx')

root = tk.Tk()
root.withdraw()  # to hide the empty tkinter window

action = messagebox.askyesno("Elementenlijst klaar", "Wil je het bestand openen? Klik op 'Nee' om de elementenlijst op te slaan")
if action:
    os.system('start excel.exe Opmetingsaanvraag.xlsx')
else:
    # ask the user where to save with explorer
    file_path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                             initialfile='Opmetingsaanvraag.xlsx',
                                             filetypes=[("Excel files", "*.xlsx")])

    # If a file path is provided
    if file_path:
        try:
            shutil.move('Opmetingsaanvraag.xlsx', file_path)
            print(f"Elementen lijst opgeslagen in {file_path}")
        except Exception as e:
            print(f"Er is een fout met het opslaan het de elementenlijst. Contacteer Ayoub: {str(e)}")
    else:
        messagebox.showinfo("Das pech, lijst weg.", "Geen locatie aangegeven")
# Save the workbook
wb.save('Opmetingsaanvraag.xlsx')
os.system('start excel.exe Opmetingsaanvraag.xlsx')
