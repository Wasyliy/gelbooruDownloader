import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import requests
import os
import json
import time
import hashlib
from datetime import datetime
import threading
from PIL import Image, ImageTk
import io
import urllib.parse
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed

class BooruDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("Booru Downloader" )
        self.root.geometry("1200x850")
        self.root.configure(bg='#2b2b2b')
        self.setup_styles()
        self.api_settings_file = "booru_settings.json"
        self.load_api_settings()
        self.download_path = ""
        self.tags_history_file = "booru_tags_history.json"
        self.downloaded_hashes_file = "booru_downloaded_hashes.json"
        self.downloaded_ids_file = "booru_downloaded_ids.json"
        self.preview_images = []
        self.current_preview_page = 0
        self.tags_history = self.load_tags_history()
        self.downloaded_hashes = self.load_downloaded_hashes()
        self.downloaded_ids = self.load_downloaded_ids()
        self.is_downloading = False
        self.stop_download = False
        self.download_threads = 3
        self.setup_ui()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Custom.TFrame', background='#2b2b2b')
        style.configure('Custom.TLabelframe', background='#2b2b2b', foreground='white')
        style.configure('Custom.TLabelframe.Label', background='#2b2b2b', foreground='white')
        style.configure('Custom.TLabel', background='#2b2b2b', foreground='white')
        style.configure('Custom.TButton', background='#404040', foreground='white')
        style.configure('Custom.TRadiobutton', background='#2b2b2b', foreground='white')
        style.configure('Custom.TCheckbutton', background='#2b2b2b', foreground='white')
        style.configure('Custom.TEntry', fieldbackground='#404040', foreground='white')
        style.configure('Custom.TSpinbox', fieldbackground='#404040', foreground='white')
        style.configure('Custom.Horizontal.TProgressbar', background='#0078d7')

    def load_api_settings(self):
        default_settings = {
            "gelbooru": {"api_key": "", "user_id": ""},
            "e621": {"username": "", "api_key": ""},
            "last_source": "gelbooru",
            "download_threads": 3
        }
        try:
            if os.path.exists(self.api_settings_file):
                with open(self.api_settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    self.api_settings = {**default_settings, **loaded_settings}
            else:
                self.api_settings = default_settings
        except Exception:
            self.api_settings = default_settings
        self.download_threads = self.api_settings.get("download_threads", 3)

    def save_api_settings(self):
        try:
            self.api_settings["download_threads"] = self.download_threads
            with open(self.api_settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.api_settings, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def setup_ui(self):
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        left_frame = ttk.Frame(main_paned, style='Custom.TFrame')
        main_paned.add(left_frame, weight=1)
        right_frame = ttk.Frame(main_paned, style='Custom.TFrame')
        main_paned.add(right_frame, weight=1)
        title_label = ttk.Label(left_frame, text="Booru Downloader - Gelbooru & e621", font=("Arial", 14, "bold"), style='Custom.TLabel')
        title_label.pack(pady=(0, 15))
        source_frame = ttk.LabelFrame(left_frame, text="Источник данных", padding="10", style='Custom.TLabelframe')
        source_frame.pack(fill="x", pady=(0, 10))
        self.source_var = tk.StringVar(value=self.api_settings["last_source"])
        ttk.Radiobutton(source_frame, text="Gelbooru", variable=self.source_var, value="gelbooru", command=self.on_source_change, style='Custom.TRadiobutton').pack(side="left")
        ttk.Radiobutton(source_frame, text="e621", variable=self.source_var, value="e621", command=self.on_source_change, style='Custom.TRadiobutton').pack(side="left", padx=(20, 0))
        self.api_frame = ttk.LabelFrame(left_frame, text="API Настройки Gelbooru", padding="10", style='Custom.TLabelframe')
        self.api_frame.pack(fill="x", pady=(0, 10))
        self.setup_gelbooru_api_frame()
        self.setup_e621_api_frame()
        tags_frame = ttk.LabelFrame(left_frame, text="Теги для поиска", padding="10", style='Custom.TLabelframe')
        tags_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(tags_frame, text="Теги:", style='Custom.TLabel').pack(anchor="w")
        self.tags_entry = ttk.Entry(tags_frame, style='Custom.TEntry')
        self.tags_entry.pack(fill="x", pady=5)
        self.examples_frame = ttk.Frame(tags_frame, style='Custom.TFrame')
        self.examples_frame.pack(fill="x", pady=5)
        ttk.Label(tags_frame, text="История тегов:", style='Custom.TLabel').pack(anchor="w", pady=(10, 0))
        self.tags_history_listbox = tk.Listbox(tags_frame, height=3, bg='#404040', fg='white', selectbackground='#0078d7', selectforeground='white')
        self.tags_history_listbox.pack(fill="x", pady=5)
        self.tags_history_listbox.bind("<<ListboxSelect>>", self.on_tags_history_select)
        history_buttons_frame = ttk.Frame(tags_frame, style='Custom.TFrame')
        history_buttons_frame.pack(fill="x")
        ttk.Button(history_buttons_frame, text="Добавить в историю", command=self.add_to_tags_history, style='Custom.TButton').pack(side="left", padx=(0, 5))
        ttk.Button(history_buttons_frame, text="Удалить из истории", command=self.remove_from_tags_history, style='Custom.TButton').pack(side="left")
        settings_frame = ttk.LabelFrame(left_frame, text="Настройки загрузки", padding="10", style='Custom.TLabelframe')
        settings_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(settings_frame, text="Количество постов:", style='Custom.TLabel').grid(row=0, column=0, sticky="w", pady=2)
        self.limit_var = tk.StringVar(value="100")
        self.limit_spinbox = ttk.Spinbox(settings_frame, from_=1, to=1000, textvariable=self.limit_var, width=10, style='Custom.TSpinbox')
        self.limit_spinbox.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        ttk.Label(settings_frame, text="Потоки загрузки:", style='Custom.TLabel').grid(row=0, column=2, sticky="w", pady=2, padx=(20,0))
        self.threads_var = tk.StringVar(value=str(self.download_threads))
        threads_spinbox = ttk.Spinbox(settings_frame, from_=1, to=10, textvariable=self.threads_var, width=5, style='Custom.TSpinbox')
        threads_spinbox.grid(row=0, column=3, sticky="w", padx=5, pady=2)
        ttk.Label(settings_frame, text="Папка для сохранения:", style='Custom.TLabel').grid(row=1, column=0, sticky="w", pady=2)
        self.download_path_var = tk.StringVar()
        download_entry = ttk.Entry(settings_frame, textvariable=self.download_path_var, style='Custom.TEntry')
        download_entry.grid(row=1, column=1, columnspan=3, sticky="we", padx=5, pady=2)
        ttk.Button(settings_frame, text="Выбрать", command=self.select_download_folder, style='Custom.TButton').grid(row=1, column=4, padx=5, pady=2)
        ttk.Label(settings_frame, text="Рейтинг:", style='Custom.TLabel').grid(row=2, column=0, sticky="w", pady=2)
        self.rating_var = tk.StringVar(value="all")
        rating_frame = ttk.Frame(settings_frame, style='Custom.TFrame')
        rating_frame.grid(row=2, column=1, columnspan=4, sticky="w", padx=5, pady=2)
        for text, val in [("Все", "all"), ("Safe", "safe"), ("Questionable", "questionable"), ("Explicit", "explicit")]:
            ttk.Radiobutton(rating_frame, text=text, variable=self.rating_var, value=val, style='Custom.TRadiobutton').pack(side="left", padx=(10, 0))
        ttk.Label(settings_frame, text="Сортировка:", style='Custom.TLabel').grid(row=3, column=0, sticky="w", pady=2)
        self.sort_var = tk.StringVar(value="date")
        sort_frame = ttk.Frame(settings_frame, style='Custom.TFrame')
        sort_frame.grid(row=3, column=1, columnspan=4, sticky="w", padx=5, pady=2)
        ttk.Radiobutton(sort_frame, text="По дате", variable=self.sort_var, value="date", style='Custom.TRadiobutton').pack(side="left")
        ttk.Radiobutton(sort_frame, text="По рейтингу", variable=self.sort_var, value="score", style='Custom.TRadiobutton').pack(side="left", padx=(10, 0))
        self.skip_duplicates_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, text="Пропускать уже скачанные арты", variable=self.skip_duplicates_var, style='Custom.TCheckbutton').grid(row=4, column=0, columnspan=4, sticky="w", pady=5)
        settings_frame.columnconfigure(1, weight=1)
        buttons_frame = ttk.Frame(left_frame, style='Custom.TFrame')
        buttons_frame.pack(fill="x", pady=(0, 10))
        self.start_button = ttk.Button(buttons_frame, text="Начать загрузку", command=self.start_download, style='Custom.TButton')
        self.start_button.pack(side="left", padx=(0, 5))
        self.stop_button = ttk.Button(buttons_frame, text="Остановить", command=self.stop_download_process, state="disabled", style='Custom.TButton')
        self.stop_button.pack(side="left", padx=(0, 5))
        self.preview_button = ttk.Button(buttons_frame, text="Предпросмотр", command=self.show_preview, style='Custom.TButton')
        self.preview_button.pack(side="left", padx=(20, 5))
        ttk.Button(buttons_frame, text="Сохранить настройки", command=self.save_settings, style='Custom.TButton').pack(side="right")
        self.progress = ttk.Progressbar(left_frame, orient="horizontal", mode="determinate", style='Custom.Horizontal.TProgressbar')
        self.progress.pack(fill="x", pady=(0, 10))
        self.status_var = tk.StringVar(value="Готов к работе")
        ttk.Label(left_frame, textvariable=self.status_var, style='Custom.TLabel').pack(anchor="w")
        log_frame = ttk.LabelFrame(right_frame, text="Лог загрузки", padding="10", style='Custom.TLabelframe')
        log_frame.pack(fill="both", expand=True)
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap="word", bg='#1e1e1e', fg='white', insertbackground='white')
        self.log_text.pack(fill="both", expand=True)
        self.preview_frame = ttk.LabelFrame(right_frame, text="Предпросмотр артов", padding="10", style='Custom.TLabelframe')
        self.on_source_change()
        self.update_tags_history_listbox()

    def setup_gelbooru_api_frame(self):
        ttk.Label(self.api_frame, text="API Key:", style='Custom.TLabel').grid(row=0, column=0, sticky="w", pady=2)
        self.gelbooru_api_key_entry = ttk.Entry(self.api_frame, show="*", style='Custom.TEntry')
        self.gelbooru_api_key_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=2, sticky="we")
        self.gelbooru_api_key_entry.insert(0, self.api_settings["gelbooru"]["api_key"])
        ttk.Label(self.api_frame, text="User ID:", style='Custom.TLabel').grid(row=1, column=0, sticky="w", pady=2)
        self.gelbooru_user_id_entry = ttk.Entry(self.api_frame, style='Custom.TEntry')
        self.gelbooru_user_id_entry.grid(row=1, column=1, padx=5, pady=2, sticky="w")
        self.gelbooru_user_id_entry.insert(0, self.api_settings["gelbooru"]["user_id"])
        example_label = ttk.Label(self.api_frame, text="Формат: &api_key=XXX&user_id=XXX", font=("Arial", 8), foreground="gray", style='Custom.TLabel')
        example_label.grid(row=1, column=2, sticky="w", padx=5)
        self.api_frame.columnconfigure(1, weight=1)

    def setup_e621_api_frame(self):
        self.e621_frame = ttk.LabelFrame(self.api_frame, text="API Настройки e621", padding="10", style='Custom.TLabelframe')
        ttk.Label(self.e621_frame, text="Username:", style='Custom.TLabel').grid(row=0, column=0, sticky="w", pady=2)
        self.e621_username_entry = ttk.Entry(self.e621_frame, style='Custom.TEntry')
        self.e621_username_entry.grid(row=0, column=1, padx=5, pady=2, sticky="we")
        self.e621_username_entry.insert(0, self.api_settings["e621"]["username"])
        ttk.Label(self.e621_frame, text="API Key:", style='Custom.TLabel').grid(row=1, column=0, sticky="w", pady=2)
        self.e621_api_key_entry = ttk.Entry(self.e621_frame, show="*", style='Custom.TEntry')
        self.e621_api_key_entry.grid(row=1, column=1, padx=5, pady=2, sticky="we")
        self.e621_api_key_entry.insert(0, self.api_settings["e621"]["api_key"])
        info_label = ttk.Label(self.e621_frame, text="API ключ можно получить на e621.net/users/new", font=("Arial", 8), foreground="#0078d7", style='Custom.TLabel')
        info_label.grid(row=2, column=0, columnspan=2, sticky="w", pady=(5, 0))
        self.e621_frame.columnconfigure(1, weight=1)

    def on_source_change(self):
        source = self.source_var.get()
        self.api_settings["last_source"] = source
        if source == "gelbooru":
            self.api_frame.config(text="API Настройки Gelbooru")
            self.gelbooru_api_key_entry.grid()
            self.gelbooru_user_id_entry.grid()
            if hasattr(self, 'e621_frame'):
                self.e621_frame.grid_remove()
        else:
            self.api_frame.config(text="API Настройки e621")
            self.gelbooru_api_key_entry.grid_remove()
            self.gelbooru_user_id_entry.grid_remove()
            if not hasattr(self, 'e621_frame_gridded'):
                self.e621_frame.grid(row=0, column=0, columnspan=3, sticky="we", pady=5)
                self.e621_frame_gridded = True
            else:
                self.e621_frame.grid()
        self.update_examples()
        self.save_api_settings()
    def update_examples(self):
        for widget in self.examples_frame.winfo_children():
            widget.destroy()
        source = self.source_var.get()
        if source == "gelbooru":
            examples = [
                "1girl solo", "rating:safe", "cat_ears",
                "maid outfit", "thighhighs"
            ]
        else:
            examples = [
                "canine rating:safe", "female solo", "dragon",
                "digital_art", "feral"
            ]
        ttk.Label(self.examples_frame, text="Примеры:", style='Custom.TLabel').pack(anchor="w")
        examples_frame_inner = ttk.Frame(self.examples_frame, style='Custom.TFrame')
        examples_frame_inner.pack(fill="x")
        for ex in examples:
            ttk.Button(examples_frame_inner, text=ex, command=lambda e=ex: self.tags_entry.insert(tk.END, e + " "), style='Custom.TButton').pack(side="left", padx=2, pady=2)

    def select_download_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку для сохранения артов")
        if folder:
            self.download_path = folder
            self.download_path_var.set(folder)

    def add_to_tags_history(self):
        tags = self.tags_entry.get().strip()
        if tags and tags not in self.tags_history:
            self.tags_history.insert(0, tags)
            self.save_tags_history()
            self.update_tags_history_listbox()

    def remove_from_tags_history(self):
        selection = self.tags_history_listbox.curselection()
        if selection:
            index = selection[0]
            del self.tags_history[index]
            self.save_tags_history()
            self.update_tags_history_listbox()

    def on_tags_history_select(self, event):
        selection = self.tags_history_listbox.curselection()
        if selection:
            index = selection[0]
            self.tags_entry.delete(0, tk.END)
            self.tags_entry.insert(0, self.tags_history[index])

    def load_tags_history(self):
        if os.path.exists(self.tags_history_file):
            with open(self.tags_history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def save_tags_history(self):
        with open(self.tags_history_file, 'w', encoding='utf-8') as f:
            json.dump(self.tags_history, f, ensure_ascii=False, indent=2)

    def update_tags_history_listbox(self):
        self.tags_history_listbox.delete(0, tk.END)
        for tag in self.tags_history:
            self.tags_history_listbox.insert(tk.END, tag)

    def load_downloaded_hashes(self):
        if os.path.exists(self.downloaded_hashes_file):
            with open(self.downloaded_hashes_file, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        return set()

    def save_downloaded_hashes(self):
        with open(self.downloaded_hashes_file, 'w', encoding='utf-8') as f:
            json.dump(list(self.downloaded_hashes), f, ensure_ascii=False, indent=2)

    def load_downloaded_ids(self):
        if os.path.exists(self.downloaded_ids_file):
            with open(self.downloaded_ids_file, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        return set()

    def save_downloaded_ids(self):
        with open(self.downloaded_ids_file, 'w', encoding='utf-8') as f:
            json.dump(list(self.downloaded_ids), f, ensure_ascii=False, indent=2)

    def log(self, message):
        self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see(tk.END)

    def save_settings(self):
        self.api_settings["gelbooru"]["api_key"] = self.gelbooru_api_key_entry.get()
        self.api_settings["gelbooru"]["user_id"] = self.gelbooru_user_id_entry.get()
        self.api_settings["e621"]["username"] = self.e621_username_entry.get()
        self.api_settings["e621"]["api_key"] = self.e621_api_key_entry.get()
        self.download_threads = int(self.threads_var.get())
        self.api_settings["download_threads"] = self.download_threads
        self.save_api_settings()
        self.log("Настройки сохранены")

    def get_gelbooru_posts(self, tags, limit, rating, sort):
        api_key = self.gelbooru_api_key_entry.get()
        user_id = self.gelbooru_user_id_entry.get()
        base_url = "https://gelbooru.com/index.php?page=dapi&s=post&q=index&json=1"
        params = {
            "tags": tags,
            "limit": limit,
            "api_key": api_key,
            "user_id": user_id
        }
        if rating != "all":
            params["tags"] += f" rating:{rating}"
        if sort == "score":
            params["tags"] += " sort:score"
        url = base_url + "&" + urllib.parse.urlencode(params)
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if "post" in data:
                return data["post"]
            return []
        return []

    def get_e621_posts(self, tags, limit, rating, sort):
        username = self.e621_username_entry.get()
        api_key = self.e621_api_key_entry.get()
        headers = {"User-Agent": f"BooruDownloader/1.0 ({username})"}
        url = "https://e621.net/posts.json"
        params = {"tags": tags, "limit": limit}
        if rating != "all":
            params["tags"] += f" rating:{rating[0]}"
        if sort == "score":
            params["tags"] += " order:score"
        r = requests.get(url, headers=headers, auth=(username, api_key), params=params, timeout=15)
        if r.status_code == 200:
            data = r.json()
            return data.get("posts", [])
        return []

    def download_post(self, post, source, download_path):
        try:
            if source == "gelbooru":
                file_url = post.get("file_url")
                post_id = str(post.get("id"))
            else:
                file_url = post.get("file", {}).get("url")
                post_id = str(post.get("id"))

            if not file_url:
                return False

            if self.skip_duplicates_var.get() and post_id in self.downloaded_ids:
                return False

            response = requests.get(file_url, timeout=20)
            if response.status_code == 200:
                file_data = response.content
                file_hash = hashlib.md5(file_data).hexdigest()

                if self.skip_duplicates_var.get() and file_hash in self.downloaded_hashes:
                    return False

                ext = os.path.splitext(file_url)[-1]
                filename = f"{post_id}{ext}"
                file_path = os.path.join(download_path, filename)

                with open(file_path, 'wb') as f:
                    f.write(file_data)

                self.downloaded_hashes.add(file_hash)
                self.downloaded_ids.add(post_id)
                return True
            return False
        except Exception:
            return False

    def start_download(self):
        if self.is_downloading:
            messagebox.showinfo("Загрузка", "Процесс уже запущен.")
            return
        tags = self.tags_entry.get().strip()
        if not tags:
            messagebox.showerror("Ошибка", "Введите теги для поиска.")
            return
        download_path = self.download_path_var.get().strip()
        if not download_path:
            messagebox.showerror("Ошибка", "Выберите папку для сохранения.")
            return
        limit = int(self.limit_var.get())
        self.is_downloading = True
        self.stop_download = False
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.status_var.set("Загрузка началась...")
        self.progress["value"] = 0
        threading.Thread(target=self.download_thread, args=(tags, limit, download_path)).start()

    def stop_download_process(self):
        self.stop_download = True
        self.status_var.set("Остановка загрузки...")

    def download_thread(self, tags, limit, download_path):
        source = self.source_var.get()
        rating = self.rating_var.get()
        sort = self.sort_var.get()
        self.log(f"Начинается загрузка из {source} с тегами: {tags}")
        if source == "gelbooru":
            posts = self.get_gelbooru_posts(tags, limit, rating, sort)
        else:
            posts = self.get_e621_posts(tags, limit, rating, sort)
        total = len(posts)
        self.progress["maximum"] = total
        success = 0
        with ThreadPoolExecutor(max_workers=self.download_threads) as executor:
            futures = [executor.submit(self.download_post, p, source, download_path) for p in posts]
            for i, f in enumerate(as_completed(futures), 1):
                if self.stop_download:
                    break
                result = f.result()
                if result:
                    success += 1
                self.progress["value"] = i
                self.status_var.set(f"Загружено {i}/{total}")
        self.save_downloaded_hashes()
        self.save_downloaded_ids()
        self.is_downloading = False
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        if self.stop_download:
            self.status_var.set("Загрузка остановлена пользователем.")
            self.log("Загрузка остановлена.")
        else:
            self.status_var.set("Загрузка завершена.")
            self.log(f"Загрузка завершена. Успешно: {success}/{total}")

    def show_preview(self):
        for widget in self.preview_frame.winfo_children():
            widget.destroy()
        source = self.source_var.get()
        tags = self.tags_entry.get().strip()
        if not tags:
            messagebox.showerror("Ошибка", "Введите теги для предпросмотра.")
            return
        posts = []
        if source == "gelbooru":
            posts = self.get_gelbooru_posts(tags, 10, "all", "date")
        else:
            posts = self.get_e621_posts(tags, 10, "all", "date")
        if not posts:
            messagebox.showinfo("Предпросмотр", "Ничего не найдено.")
            return
        self.preview_frame.pack(fill="both", expand=True, pady=5)
        preview_canvas = tk.Canvas(self.preview_frame, bg="#1e1e1e")
        preview_canvas.pack(fill="both", expand=True)
        scrollbar = ttk.Scrollbar(self.preview_frame, orient="vertical", command=preview_canvas.yview)
        scrollbar.pack(side="right", fill="y")
        preview_canvas.configure(yscrollcommand=scrollbar.set)
        preview_inner = ttk.Frame(preview_canvas, style='Custom.TFrame')
        preview_canvas.create_window((0, 0), window=preview_inner, anchor="nw")
        self.preview_images.clear()
        for post in posts:
            if source == "gelbooru":
                url = post.get("preview_url")
            else:
                url = post.get("preview", {}).get("url")
            if not url:
                continue
            try:
                r = requests.get(url, timeout=10)
                img = Image.open(io.BytesIO(r.content))
                img = img.resize((150, 150))
                photo = ImageTk.PhotoImage(img)
                self.preview_images.append(photo)
                lbl = ttk.Label(preview_inner, image=photo, style='Custom.TLabel')
                lbl.pack(side="left", padx=5, pady=5)
            except Exception:
                continue
        preview_inner.update_idletasks()
        preview_canvas.configure(scrollregion=preview_canvas.bbox("all"))

if __name__ == "__main__":
    root = tk.Tk()
    app = BooruDownloader(root)
    root.mainloop()
