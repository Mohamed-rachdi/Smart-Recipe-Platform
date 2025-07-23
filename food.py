import tkinter as tk
from tkinter import ttk, messagebox
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service

import json
import requests
from PIL import Image, ImageDraw, ImageFont
import sys
import io

# Pour bien voir les accents dans la console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ─── CHEMINS DE BASE ────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Si le script est déjà dans "repas", on prend BASE_DIR, sinon on crée "repas" à côté
if os.path.basename(BASE_DIR).lower() == "rdepas":
    REPAS_DIR = BASE_DIR
else:
    REPAS_DIR = os.path.join(BASE_DIR, "repas")
os.makedirs(REPAS_DIR, exist_ok=True)

# ─── Variables globales ────────────────────────────────────────────────────────
url_list = []
article_limit = 50
user_action = None

# ─── Fichier des URLs déjà scrappées ───────────────────────────────────────────
scraped_file = os.path.join(REPAS_DIR, "scrape3.json")
if os.path.exists(scraped_file):
    try:
        with open(scraped_file, "r", encoding="utf-8") as f:
            scraped_urls = set(json.load(f))
    except Exception:
        scraped_urls = set()
else:
    scraped_urls = set()

def save_scraped():
    with open(scraped_file, "w", dencoding="utf-8") as f:
        json.dump(list(scraped_urls), f, ensure_ascii=False, indent=2)

# ─── Interface Tkinter ────────────────────────────────────────────────────────
def on_enter_url(event):
    text = entry_url.get().strip()
    if text and not text.endswith(","):
        entry_url.delete(0, tk.END)
        entry_url.insert(0, text + ", ")
    return "break"

def on_launch():
    global url_list, article_limit, user_action
    ul = entry_url.get().strip()
    if not ul:
        messagebox.showwarning("Erreur", "Veuillez entrer au moins une URL de collection.")
        return
    try:
        alim = int(entry_article_limit.get().strip())
        if alim <= 0:
            raise ValueError
    except ValueError:
        messagebox.showwarning("Erreur", "Le champ 'Articles à traiter' doit être un entier positif.")
        return

    url_list[:] = [u.strip() for u in ul.split(",") if u.strip()]
    article_limit = alim
    user_action =d "launch"
    root.destroy()

def on_cancel():
    global user_action
    user_action = "cancel"
    root.destroy()

root.title("Scraping Food Network UK")
root.geometry("700x300")
root.configure(bg="#f5f5f5")
root.resizable(False, False)

style = ttk.Style()
style.theme_use("clam")
style.configure("TLabel", background="#f5f5f5", font=("Segoe UI", 10))
style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), foreground="#1c3d5a")
style.configure("TEntry", padding=5, relief="flat", fieldbackground="#ffffff")
style.configure("TButton", font=("Segoe UI", 10, "bold"), foreground="#fff",
                background="#1c3d5a", padding=8, relief="flat")
style.map("TButton", background=[('active', '#174263'), ('disabled', '#a0a0a0')])

ttk.Label(root, text="⚙️ Paramètres de Scraping Food Network UK", style="Header.TLabel").pack(pady=(20,10))
frame = tk.Frame(root, bg="#f5f5f5"); frame.pack(padx=40, fill="x")

ttk.Label(frame, text="URLs de collections (séparées par des virgules) :").grid(row=0, column=0, sticky="w")
entry_url = ttk.Entry(frame, width=50); entry_url.grid(row=1, column=0, pady=(0,15))
entry_url.bind("<Return>", on_enter_url)

ttk.Label(frame, text="Articles à traiter (limite) :").grid(row=2, column=0, sticky="w")
entry_article_limit = ttk.Entry(frame, width=8)
entry_article_limit.insert(0, str(article_limit))
entry_article_limit.grid(row=3, column=0, sticky="w", pady=(0,15))

btn_frame = tk.Frame(root, bg="#f5f5f5"); btn_frame.pack(pady=(10,20))
ttk.Button(btn_frame, text="Lancer le scraping", command=on_launch).grid(row=0, column=0, padx=20)
ttk.Button(btn_frame, text="Annuler", command=on_cancel).grid(row=0, column=1)

root.mainloop()
if user_action != "launch":
    exit()

# ─── Image Processing ──────────────────────────────────────────────────────────
PHOTO_FOLDER = os.path.join(REPAS_DIR, "photos")
os.makedirs(PHOTO_FOLDER, exist_ok=True)


def is_processed(link):
    return isinstance(link, str) and "imagekit.io" in link

def add_watermark(path, text, size=30):
    try:
        with Image.open(path).convert("RGBA") as img:
            txt = Image.new("RGBA", img.size, (255,255,255,0))
            draw = ImageDraw.Draw(txt)
            try:
                font = ImageFont.truetype("arial.ttf", size)
            except IOError:
                font = ImageFont.load_default()
            bbox = draw.textbbox((0,0), text, font=font)
            x = (img.width - (bbox[2]-bbox[0]))/2
            y = img.height - (bbox[3]-bbox[1]) - 10
            draw.text((x,y), text, font=font, fill=(255,255,255,128))
            combined = Image.alpha_composite(img, txt)
            ext = os.path.splitext(path)[1].lower()
            if ext == ".png":
                combined.save(path, "PNG")
            else:
                combined.convert("RGB").save(path, "JPEG")
    except Exception as e:
        print("Watermark error:", e)

def compress_image(path, quality=40):
    try:
        with Image.open(path) as img:
            if img.mode in ("RGBA","P"):
                img = img.convert("RGB")
            img.save(path, optimize=True, quality=quality)
    except Exception as e:
        print("Compression error:", e)

def upload_to_imagekit(path):
    try:
        filename = os.path.basename(path)
        auth = (IMAGEKIT_PRIVATE_KEY, "")
        files = {"file": (filename, open(path,"rb"))}
        data = {"fileName": filename, "folder":"/"}
        resp = requests.post(IMAGEKIT_UPLOAD_URL, auth=auth, files=files, data=data, timeout=30)
        resp.raise_for_status()
        return resp.json().get("url")
    except Exception as e:
        print("Upload error:", e)
        return None

def process_image_link(link, base, idx):
    if pd.isna(link) or is_processed(link):
        return link if isinstance(link, str) else None
    local = os.path.join(PHOTO_FOLDER, f"{base}_{idx}.jpg")
    try:
        r = requests.get(link, timeout=20); r.raise_for_status()
        with open(local,"wb") as f:
            f.write(r.content)
        compress_image(local)
        add_watermark(local, WATERMARK_TEXT, FONT_SIZE)
        return upload_to_imagekit(local) or link
    except Exception as e:
        print("Download error:", e)
        return link

# ─── Lancement du navigateur ───────────────────────────────────────────────────
chromedriver_path = os.path.join(BASE_DIR, "chromedriver-win64", "chromedriver.exe")
service = Service(chromedriver_path)
driver = webdriver.Chrome(service=service)

# ─── Boucle principale ─────────────────────────────────────────────────────────
for collection_url in url_list:
    print(f"\n🔍 Accès à la collection : {collection_url}")
    driver.get(collection_url)
    time.sleep(2)

    page_links = {collection_url}
    try:
        for a in driver.find_elements(By.CSS_SELECTOR, "div.pagination-items a[href]"):
            page_links.add(a.get_attribute("href"))
    except:
        pass
        driver.get(page)
        time.sleep(2)
        for a in driver.find_elements(By.CSS_SELECTOR, "a.block.group[href]"):
            all_recipes.append(a.get_attribute("href"))
    all_recipes = list(dict.fromkeys(all_recipes))[:article_limit]
    print(f"→ {len(all_recipes)} recettes extraites")

    # Crée un dossier par collection DANS repas/
    folder_name = re.sub(r'[^\w\s-]', '', collection_url.rstrip("/").split("/")[-1]).strip().replace(" ", "_")
    folder_path = os.path.join(REPAS_DIR, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    for idx, link in enumerate(all_recipes, 1):
        if link in scraped_urls:
            print(f"⏭️ Déjà scrappé : {link}")
            continue
        print(f"➡️ ({idx}/{len(all_recipes)}) {link}")
        driver.get(link)
        time.sleep(2)

        try:
            title = driver.find_element(By.TAG_NAME, "h1").text.strip()
        except:
            title = "Sans_titre"
        try:
            img_elem = driver.find_element(By.CSS_SELECTOR, "img.u-photo")
            img_url = img_elem.get_attribute("src") or img_elem.get_attribute("srcset").split()[0]
        except:
            img_url = None
        if not img_url:
            print(f"⚠️ Recette sans image, ignorée : {link}")
            continue
        try:
            prep = driver.find_element(By.CSS_SELECTOR, "div.flex.items-center.opacity-60 span.h5").text.strip()
        except:
            prep = None

        ingredients = [el.text.strip() for el in driver.find_elements(By.CSS_SELECTOR, "label.p-ingredient")]
        steps = [p.text.strip() for p in driver.find_elements(By.CSS_SELECTOR, "div.e-instructions > p") if p.text.strip()]

        max_len = max(len(ingredients), len(steps))
        ingredients += [None]*(max_len-len(ingredients))
        steps += [None]*(max_len-len(steps))

        rows = [{"ingrédient": ingredients[i], "étape": steps[i], "img_link": None} for i in range(max_len)]
        df = pd.DataFrame(rows)
        top = pd.DataFrame([{"ingrédient": None, "étape": None, "img_link": img_url,
                              "titre": title, "temps": prep}])
        final_df = pd.concat([top, df], ignore_index=True)

        base = re.sub(r'[^\w\s-]', '', title).strip().replace(" ", "_")
        final_df["img_link"] = [
            process_image_link(l, base, i) for i, l in enumerate(final_df["img_link"])
        ]

        # Sauvegarde Excel DANS le dossier de la collection SOUS repas/
        xlsx_path = os.path.join(folder_path, f"{base}.xlsx")
        with pd.ExcelWriter(xlsx_path, engine="xlsxwriter") as writer:
            final_df.to_excel(writer, index=False, sheet_name="Recette")
            fmt = writer.book.add_format({'text_wrap': True})
            writer.sheets["Recette"].set_column('C:C', 40, fmt)
        print(f"✅ Sauvegardé : {xlsx_path}")

        scraped_urls.add(link)
        save_scraped()

driver.quit()
print("\n🏁 Extraction terminée.")
