import os
import re
import threading
import asyncio
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List, Dict, Any
import time

# Selenium imports (with webdriver_manager fallback if available)
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import SessionNotCreatedException, WebDriverException
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service as ChromeService
    try:
        from webdriver_manager.chrome import ChromeDriverManager  # type: ignore
    except Exception:
        ChromeDriverManager = None  # type: ignore
except Exception:
    webdriver = None  # type: ignore

from pinterest_db import init_db, upsert_pin, fetch_pins, update_file_path
from code_download import download_pinterest

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
)

async def fetch_html(url: str) -> str:
    import aiohttp
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return ""
            return await resp.text()

def parse_pins(html: str) -> List[Dict[str, Any]]:
    pins: List[Dict[str, Any]] = []
    for m in re.finditer(r'data-test-pin-id="(\d+)"', html):
        pin_id = m.group(1)
        start = max(0, m.start() - 2000)
        end = min(len(html), m.end() + 2000)
        snippet = html[start:end]
        href_match = re.search(r'href="(/pin/\d+/)"', snippet)
        title_match = re.search(r'aria-label="([^"]+)"', snippet)
        pins.append({
            "pin_id": pin_id,
            "href": f"https://www.pinterest.com{href_match.group(1)}" if href_match else f"https://www.pinterest.com/pin/{pin_id}/",
            "title": title_match.group(1) if title_match else None,
        })
    seen = set()
    unique_pins: List[Dict[str, Any]] = []
    for p in pins:
        if p["pin_id"] in seen:
            continue
        seen.add(p["pin_id"])
        unique_pins.append(p)
    return unique_pins

class ModernStyle:
    """Modern color scheme and styling"""
    BG_DARK = "#1a1a2e"
    BG_MEDIUM = "#16213e"
    BG_LIGHT = "#0f3460"
    ACCENT = "#e94560"
    ACCENT_HOVER = "#c93550"
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#a0a0a0"
    SUCCESS = "#00d9ff"
    BORDER = "#2a2a3e"

class App(ttk.Frame):
    def __init__(self, master: tk.Tk):
        super().__init__(master)
        self.master.title("Pinterest Downloader Pro")
        self.master.geometry("1100x700")
        self.master.configure(bg=ModernStyle.BG_DARK)
        
        # Apply modern styling
        self.setup_styles()
        init_db()

        # Header
        self.build_header()

        # Notebook with modern tabs
        self.nb = ttk.Notebook(self.master, style="Modern.TNotebook")
        self.tab_download = ttk.Frame(self.nb, style="Dark.TFrame")
        self.tab_scrape = ttk.Frame(self.nb, style="Dark.TFrame")
        self.tab_db = ttk.Frame(self.nb, style="Dark.TFrame")
        
        self.nb.add(self.tab_download, text="  📥 Download by ID  ")
        self.nb.add(self.tab_scrape, text="  🔍 Smart Scrape  ")
        self.nb.add(self.tab_db, text="  💾 Database  ")
        self.nb.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        self.build_download_tab()
        self.build_scrape_tab()
        self.build_db_tab()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Notebook styling
        style.configure("Modern.TNotebook", 
                       background=ModernStyle.BG_DARK,
                       borderwidth=0)
        style.configure("Modern.TNotebook.Tab", 
                       background=ModernStyle.BG_MEDIUM,
                       foreground=ModernStyle.TEXT_SECONDARY,
                       padding=[20, 10],
                       borderwidth=0,
                       font=('Segoe UI', 10, 'bold'))
        style.map("Modern.TNotebook.Tab",
                 background=[('selected', ModernStyle.BG_LIGHT)],
                 foreground=[('selected', ModernStyle.TEXT_PRIMARY)])
        
        # Frame styling
        style.configure("Dark.TFrame", background=ModernStyle.BG_DARK)
        style.configure("Card.TFrame", background=ModernStyle.BG_MEDIUM, relief="flat")
        
        # Label styling
        style.configure("Modern.TLabel", 
                       background=ModernStyle.BG_MEDIUM,
                       foreground=ModernStyle.TEXT_PRIMARY,
                       font=('Segoe UI', 10))
        style.configure("Title.TLabel",
                       background=ModernStyle.BG_DARK,
                       foreground=ModernStyle.TEXT_PRIMARY,
                       font=('Segoe UI', 20, 'bold'))
        style.configure("Subtitle.TLabel",
                       background=ModernStyle.BG_DARK,
                       foreground=ModernStyle.TEXT_SECONDARY,
                       font=('Segoe UI', 9))
        
        # Entry styling
        style.configure("Modern.TEntry",
                       fieldbackground=ModernStyle.BG_LIGHT,
                       foreground=ModernStyle.TEXT_PRIMARY,
                       borderwidth=2,
                       relief="flat",
                       insertcolor=ModernStyle.TEXT_PRIMARY)
        
        # Button styling
        style.configure("Accent.TButton",
                       background=ModernStyle.ACCENT,
                       foreground=ModernStyle.TEXT_PRIMARY,
                       borderwidth=0,
                       relief="flat",
                       font=('Segoe UI', 10, 'bold'),
                       padding=[20, 10])
        style.map("Accent.TButton",
                 background=[('active', ModernStyle.ACCENT_HOVER)])
        
        style.configure("Secondary.TButton",
                       background=ModernStyle.BG_LIGHT,
                       foreground=ModernStyle.TEXT_PRIMARY,
                       borderwidth=0,
                       relief="flat",
                       font=('Segoe UI', 9),
                       padding=[15, 8])
        style.map("Secondary.TButton",
                 background=[('active', ModernStyle.BORDER)])

    def build_header(self):
        header = tk.Frame(self.master, bg=ModernStyle.BG_DARK, height=80)
        header.pack(fill=tk.X, padx=15, pady=(15, 10))
        header.pack_propagate(False)
        
        title = ttk.Label(header, text=" Pinterest Downloader Pro", style="Title.TLabel")
        title.pack(side=tk.LEFT, pady=10)
        
        subtitle = ttk.Label(header, text="Download & Scrape Pinterest content with ease", style="Subtitle.TLabel")
        subtitle.pack(side=tk.LEFT, padx=(15, 0), pady=10)

    def create_card(self, parent):
        card = tk.Frame(parent, bg=ModernStyle.BG_MEDIUM, relief="flat", bd=0)
        card.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        return card

    def create_modern_entry(self, parent, placeholder=""):
        entry = tk.Entry(parent,
                        bg=ModernStyle.BG_LIGHT,
                        fg=ModernStyle.TEXT_PRIMARY,
                        insertbackground=ModernStyle.TEXT_PRIMARY,
                        font=('Segoe UI', 10),
                        relief="flat",
                        bd=0)
        entry.configure(highlightthickness=2, 
                       highlightbackground=ModernStyle.BORDER,
                       highlightcolor=ModernStyle.ACCENT)
        return entry

    def create_modern_text(self, parent):
        text = tk.Text(parent,
                      bg=ModernStyle.BG_LIGHT,
                      fg=ModernStyle.TEXT_PRIMARY,
                      insertbackground=ModernStyle.TEXT_PRIMARY,
                      font=('Consolas', 9),
                      relief="flat",
                      bd=0,
                      wrap=tk.WORD)
        text.configure(highlightthickness=2,
                      highlightbackground=ModernStyle.BORDER,
                      highlightcolor=ModernStyle.ACCENT)
        return text

    def build_download_tab(self):
        frm = self.tab_download
        frm.configure(style="Dark.TFrame")
        
        card = self.create_card(frm)
        
        # Pin ID Section
        lbl_id = ttk.Label(card, text=" Pin ID or URL", style="Modern.TLabel")
        lbl_id.grid(row=0, column=0, sticky="w", padx=20, pady=(20, 5))
        
        self.ent_id = self.create_modern_entry(card)
        self.ent_id.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 15), columnspan=3)
        
        # Download Folder Section
        lbl_dir = ttk.Label(card, text=" Download Folder", style="Modern.TLabel")
        lbl_dir.grid(row=2, column=0, sticky="w", padx=20, pady=(0, 5))
        
        self.ent_dir = self.create_modern_entry(card)
        self.ent_dir.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 15), columnspan=2)
        
        btn_browse = ttk.Button(card, text="Browse", style="Secondary.TButton", command=self.pick_folder_download)
        btn_browse.grid(row=3, column=2, sticky="e", padx=20, pady=(0, 15))
        
        # Filename Section
        lbl_name = ttk.Label(card, text="✏️ Custom Filename (optional)", style="Modern.TLabel")
        lbl_name.grid(row=4, column=0, sticky="w", padx=20, pady=(0, 5))
        
        self.ent_name = self.create_modern_entry(card)
        self.ent_name.grid(row=5, column=0, sticky="ew", padx=20, pady=(0, 20), columnspan=3)
        
        # Download Button
        self.btn_download = ttk.Button(card, text="⬇️  Download Now", style="Accent.TButton", command=self.on_download)
        self.btn_download.grid(row=6, column=0, padx=20, pady=(0, 20), sticky="w")
        
        # Log Section
        lbl_log = ttk.Label(card, text="Activity Log", style="Modern.TLabel")
        lbl_log.grid(row=7, column=0, sticky="w", padx=20, pady=(10, 5))
        
        self.txt_log1 = self.create_modern_text(card)
        self.txt_log1.grid(row=8, column=0, columnspan=3, sticky="nsew", padx=20, pady=(0, 20))
        
        card.columnconfigure(1, weight=1)
        card.rowconfigure(8, weight=1)

    def pick_folder_download(self):
        path = filedialog.askdirectory()
        if path:
            self.ent_dir.delete(0, tk.END)
            self.ent_dir.insert(0, path)

    def on_download(self):
        pin = self.ent_id.get().strip()
        out_dir = self.ent_dir.get().strip()
        name = self.ent_name.get().strip() or None
        if not pin:
            messagebox.showerror("Error", "Enter Pin ID or URL")
            return
        if not out_dir:
            messagebox.showerror("Error", "Choose download folder")
            return
        self.btn_download.config(state=tk.DISABLED)
        self.log1(f"Starting download for: {pin}")
        threading.Thread(target=self._download_worker, args=(pin, out_dir, name), daemon=True).start()

    def _download_worker(self, pin: str, out_dir: str, name: str | None):
        try:
            result = asyncio.run(download_pinterest(pin, out_dir, name))
            if result.get("success"):
                fp = result.get("filepath")
                self.log1(f"Success! Saved to: {fp}")
                pin_id = self._extract_pin_id(pin)
                upsert_pin({
                    "pin_id": pin_id,
                    "href": f"https://www.pinterest.com/pin/{pin_id}/",
                    "title": name or None,
                    "description": None,
                    "media_type": result.get("type"),
                    "media_url": None,
                    "file_path": fp,
                    "query": None,
                })
                self.refresh_db()
            else:
                self.log1("Download failed")
        except Exception as e:
            self.log1(f"Error: {str(e)}")
        finally:
            self.btn_download.config(state=tk.NORMAL)

    def _extract_pin_id(self, pin: str) -> str:
        m = re.search(r"/pin/(\d+)/", pin)
        if m:
            return m.group(1)
        return re.sub(r"\D", "", pin)

    def log1(self, msg: str):
        self.txt_log1.after(0, lambda: (self.txt_log1.insert(tk.END, msg + "\n"), self.txt_log1.see(tk.END)))

    def build_scrape_tab(self):
        frm = self.tab_scrape
        frm.configure(style="Dark.TFrame")
        
        card = self.create_card(frm)
        
        # Search Query
        lbl_q = ttk.Label(card, text="🔍 Search Query", style="Modern.TLabel")
        lbl_q.grid(row=0, column=0, sticky="w", padx=20, pady=(20, 5))
        
        self.ent_q = self.create_modern_entry(card)
        self.ent_q.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 15), columnspan=3)
        
        # Number of Videos
        lbl_n = ttk.Label(card, text="🎬 Number of Videos", style="Modern.TLabel")
        lbl_n.grid(row=2, column=0, sticky="w", padx=20, pady=(0, 5))
        
        self.ent_n = self.create_modern_entry(card)
        self.ent_n.insert(0, "20")
        self.ent_n.grid(row=3, column=0, sticky="w", padx=20, pady=(0, 15))
        
        # Download Folder
        lbl_dir = ttk.Label(card, text="Download Folder", style="Modern.TLabel")
        lbl_dir.grid(row=4, column=0, sticky="w", padx=20, pady=(0, 5))
        
        self.ent_dir2 = self.create_modern_entry(card)
        self.ent_dir2.grid(row=5, column=0, sticky="ew", padx=20, pady=(0, 15), columnspan=2)
        
        btn_browse = ttk.Button(card, text="Browse", style="Secondary.TButton", command=self.pick_folder_scrape)
        btn_browse.grid(row=5, column=2, sticky="e", padx=20, pady=(0, 15))
        
        # Scrape Button
        self.btn_scrape_dl = ttk.Button(card, text="Start Scraping", style="Accent.TButton", command=self.on_scrape)
        self.btn_scrape_dl.grid(row=6, column=0, padx=20, pady=(0, 20), sticky="w")
        
        # Log Section
        lbl_log = ttk.Label(card, text="Scraping Progress", style="Modern.TLabel")
        lbl_log.grid(row=7, column=0, sticky="w", padx=20, pady=(10, 5))
        
        self.txt_log2 = self.create_modern_text(card)
        self.txt_log2.grid(row=8, column=0, columnspan=3, sticky="nsew", padx=20, pady=(0, 20))
        
        card.columnconfigure(1, weight=1)
        card.rowconfigure(8, weight=1)

    def pick_folder_scrape(self):
        path = filedialog.askdirectory()
        if path:
            self.ent_dir2.delete(0, tk.END)
            self.ent_dir2.insert(0, path)

    def on_scrape(self):
        q = self.ent_q.get().strip()
        if not q:
            messagebox.showerror("Error", "Enter search query")
            return
        try:
            n = int(self.ent_n.get().strip())
        except Exception:
            messagebox.showerror("Error", "Enter valid number of videos")
            return
        out_dir = self.ent_dir2.get().strip()
        if not out_dir:
            messagebox.showerror("Error", "Choose download folder")
            return
        self.btn_scrape_dl.config(state=tk.DISABLED)
        self.log2(f"🔍 Searching for: {q}")
        threading.Thread(target=self._scrape_worker_selenium, args=(q, n, out_dir), daemon=True).start()

    def _scrape_worker_selenium(self, q: str, n: int, out_dir: str):
        try:
            if webdriver is None:
                self.log2("Selenium not available. Please install selenium and Chrome driver.")
                return
            url = f"https://www.pinterest.com/search/videos/?q={q.replace(' ', '%20')}&rs=typed"

            options = ChromeOptions()
            options.add_argument(f"user-agent={USER_AGENT}")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--log-level=3")

            driver = None
            try:
                # Prefer Selenium Manager (Selenium 4.6+). It auto-matches Chrome/driver.
                driver = webdriver.Chrome(options=options)
            except SessionNotCreatedException as e:
                # If a pinned/cached ChromeDriver exists on PATH, Selenium Manager may still fail.
                # Fall back to webdriver_manager only if available.
                if ChromeDriverManager:
                    try:
                        service = ChromeService(ChromeDriverManager().install())
                        driver = webdriver.Chrome(service=service, options=options)
                    except Exception:
                        raise e
                else:
                    raise
            except WebDriverException:
                # Generic driver startup errors: try webdriver_manager as fallback.
                if ChromeDriverManager:
                    service = ChromeService(ChromeDriverManager().install())
                    driver = webdriver.Chrome(service=service, options=options)
                else:
                    raise

            driver.get(url)

            seen_ids = set()
            collected: List[Dict[str, Any]] = []
            last_height = 0
            idle_rounds = 0
            max_rounds = 60

            while len(collected) < n and idle_rounds < max_rounds:
                time.sleep(1.5)
                html = driver.page_source
                pins = parse_pins(html)
                added_this_round = 0
                for p in pins:
                    pid = p["pin_id"]
                    if pid in seen_ids:
                        continue
                    seen_ids.add(pid)
                    collected.append(p)
                    added_this_round += 1
                    if len(collected) >= n:
                        break
                if added_this_round == 0:
                    idle_rounds += 1
                else:
                    idle_rounds = 0

                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.0)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    idle_rounds += 1
                last_height = new_height

            if not collected:
                self.log2("⚠️ No pins found")

            count = 0
            for i, p in enumerate(collected):
                if count >= n:
                    break
                self.log2(f"Downloading {i+1}/{min(n, len(collected))}: {p['pin_id']}")
                rec = {
                    "pin_id": p["pin_id"],
                    "href": p.get("href"),
                    "title": p.get("title"),
                    "description": None,
                    "media_type": None,
                    "media_url": None,
                    "file_path": None,
                    "query": q,
                }
                upsert_pin(rec)
                try:
                    res = asyncio.run(download_pinterest(p["pin_id"], out_dir, None))
                    if res.get("success") and res.get("filepath"):
                        update_file_path(p["pin_id"], res["filepath"])
                        self.log2(f"Saved: {os.path.basename(res['filepath'])}")
                    else:
                        self.log2(f"Failed: {p['pin_id']}")
                except Exception as e:
                    self.log2(f"Error: {str(e)}")
                count += 1

            self.log2(f"Completed! Downloaded {count} videos")
            self.refresh_db()
        except Exception as e:
            self.log2(f"Error: {str(e)}")
        finally:
            try:
                driver.quit()  # type: ignore
            except Exception:
                pass
            self.btn_scrape_dl.config(state=tk.NORMAL)

    def log2(self, msg: str):
        self.txt_log2.after(0, lambda: (self.txt_log2.insert(tk.END, msg + "\n"), self.txt_log2.see(tk.END)))

    def build_db_tab(self):
        frm = self.tab_db
        frm.configure(style="Dark.TFrame")
        
        card = self.create_card(frm)
        
        # Search Section
        top = tk.Frame(card, bg=ModernStyle.BG_MEDIUM)
        top.pack(fill=tk.X, padx=20, pady=20)
        
        lbl = ttk.Label(top, text="Search Database", style="Modern.TLabel")
        lbl.pack(side=tk.LEFT, padx=(0, 10))
        
        self.ent_search = self.create_modern_entry(top)
        self.ent_search.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        btn_refresh = ttk.Button(top, text="Refresh", style="Secondary.TButton", command=self.refresh_db)
        btn_refresh.pack(side=tk.LEFT)

        # Treeview with modern styling
        tree_frame = tk.Frame(card, bg=ModernStyle.BG_MEDIUM)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        style = ttk.Style()
        style.configure("Modern.Treeview",
                       background=ModernStyle.BG_LIGHT,
                       foreground=ModernStyle.TEXT_PRIMARY,
                       fieldbackground=ModernStyle.BG_LIGHT,
                       borderwidth=0,
                       font=('Segoe UI', 9))
        style.configure("Modern.Treeview.Heading",
                       background=ModernStyle.BG_DARK,
                       foreground=ModernStyle.TEXT_PRIMARY,
                       borderwidth=0,
                       font=('Segoe UI', 10, 'bold'))
        style.map('Modern.Treeview',
                 background=[('selected', ModernStyle.ACCENT)])
        
        cols = ("id", "pin_id", "href", "title", "media_type", "file_path", "query", "created_at")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", style="Modern.Treeview")
        
        for c in cols:
            self.tree.heading(c, text=c.replace("_", " ").title())
            self.tree.column(c, width=130, anchor=tk.W)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.refresh_db()

    def refresh_db(self):
        q = self.ent_search.get().strip() if hasattr(self, 'ent_search') else None
        rows = fetch_pins(limit=200, search=q or None)
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in rows:
            self.tree.insert("", tk.END, values=(r[0], r[1], r[2], r[3], r[5], r[7], r[8], r[9]))


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()

if __name__ == "__main__":
    main()