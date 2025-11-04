# К всем частям кода есть примечания, можете брать и редактировать под свои нужды
# There are notes to all parts of the code, you can take and edit to suit your needs
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import requests
import os
import json
import time
import hashlib
from datetime import datetime
import threading
from PIL import Image
import io
import urllib.parse

class GelbooruDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("Gelbooru Downloader")
        self.root.geometry("900x700")
        
        # API настройки
        # API settings
        self.api_key = ""
        self.user_id = ""
        
        # Пути и настройки
        # Paths and Settings
        self.download_path = ""
        self.tags_history_file = "gelbooru_tags_history.json"
        self.downloaded_hashes_file = "gelbooru_downloaded_hashes.json"
        self.downloaded_ids_file = "gelbooru_downloaded_ids.json"
        
        # Загружаем историю
        # history download
        self.tags_history = self.load_tags_history()
        self.downloaded_hashes = self.load_downloaded_hashes()
        self.downloaded_ids = self.load_downloaded_ids()
        
        # Переменные для управления
        # Variables to control
        self.is_downloading = False
        self.stop_download = False
        
        self.setup_ui()
    
    def setup_ui(self):
        # Главный фрейм
        # main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Заголовок
        # Title
        title_label = ttk.Label(main_frame, text="Gelbooru Downloader", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 10))
        
        # Фрейм API настроек
        # Frame api settings
        api_frame = ttk.LabelFrame(main_frame, text="API Настройки Gelbooru", padding="10")
        api_frame.pack(fill="x", pady=(0, 10))
        
        # API Key
        ttk.Label(api_frame, text="API Key:").grid(row=0, column=0, sticky="w", pady=2)
        self.api_key_entry = ttk.Entry(api_frame, width=60)
        self.api_key_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=2, sticky="we")
        
        # User ID
        ttk.Label(api_frame, text="User ID:").grid(row=1, column=0, sticky="w", pady=2)
        self.user_id_entry = ttk.Entry(api_frame, width=20)
        self.user_id_entry.grid(row=1, column=1, padx=5, pady=2, sticky="w")
        
        # Пример формата
        # Example of the format
        example_label = ttk.Label(api_frame, text="Формат: &api_key=XXX&user_id=XXX", 
                                 font=("Arial", 8), foreground="gray")
        example_label.grid(row=1, column=2, sticky="w", padx=5)
        
        # Фрейм тегов
        # tags frame
        tags_frame = ttk.LabelFrame(main_frame, text="Теги для поиска", padding="10")
        tags_frame.pack(fill="x", pady=(0, 10))
        
        # Поле ввода тегов
        # Tag entry field
        ttk.Label(tags_frame, text="Теги (через пробел, + для И, | для ИЛИ):").pack(anchor="w")
        self.tags_entry = ttk.Entry(tags_frame, width=80)
        self.tags_entry.pack(fill="x", pady=5)
        
        # Примеры тегов
        # Tag Examples
        examples_frame = ttk.Frame(tags_frame)
        examples_frame.pack(fill="x", pady=5)
        ttk.Label(examples_frame, text="Примеры:").pack(side="left")
        example_tags = ["hatsune_miku", "solo", "rating:safe", "1girl", "blue_archive"]
        for tag in example_tags:
            ttk.Button(examples_frame, text=tag, width=10,
                      command=lambda t=tag: self.insert_tag(t)).pack(side="left", padx=2)
        
        # История тегов
        # tags history
        ttk.Label(tags_frame, text="История тегов:").pack(anchor="w", pady=(10, 0))
        self.tags_history_listbox = tk.Listbox(tags_frame, height=4)
        self.tags_history_listbox.pack(fill="x", pady=5)
        self.tags_history_listbox.bind("<<ListboxSelect>>", self.on_tags_history_select)
        
        # Кнопки для истории тегов
        # button for tags history
        history_buttons_frame = ttk.Frame(tags_frame)
        history_buttons_frame.pack(fill="x")
        ttk.Button(history_buttons_frame, text="Добавить в историю", 
                  command=self.add_to_tags_history).pack(side="left", padx=(0, 5))
        ttk.Button(history_buttons_frame, text="Удалить из истории", 
                  command=self.remove_from_tags_history).pack(side="left")
        
        # Фрейм настроек загрузки
        # frame setting downloads
        settings_frame = ttk.LabelFrame(main_frame, text="Настройки загрузки", padding="10")
        settings_frame.pack(fill="x", pady=(0, 10))
        
        # Количество постов
        # Number of posts
        ttk.Label(settings_frame, text="Количество постов:").grid(row=0, column=0, sticky="w", pady=2)
        self.limit_var = tk.StringVar(value="100")
        self.limit_spinbox = ttk.Spinbox(settings_frame, from_=1, to=1000, 
                                        textvariable=self.limit_var, width=10)
        self.limit_spinbox.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        # Папка для сохранения
        # folder for download
        ttk.Label(settings_frame, text="Папка для сохранения:").grid(row=1, column=0, sticky="w", pady=2)
        self.download_path_var = tk.StringVar()
        ttk.Entry(settings_frame, textvariable=self.download_path_var, width=50).grid(
            row=1, column=1, padx=5, pady=2, sticky="we")
        ttk.Button(settings_frame, text="Выбрать", 
                  command=self.select_download_folder).grid(row=1, column=2, padx=5, pady=2)
        
        # Дополнительные опции
        # additional settings
        ttk.Label(settings_frame, text="Рейтинг:").grid(row=2, column=0, sticky="w", pady=2)
        self.rating_var = tk.StringVar(value="all")
        rating_frame = ttk.Frame(settings_frame)
        rating_frame.grid(row=2, column=1, columnspan=2, sticky="w", padx=5, pady=2)
        ttk.Radiobutton(rating_frame, text="Все", variable=self.rating_var, 
                       value="all").pack(side="left")
        ttk.Radiobutton(rating_frame, text="Safe", variable=self.rating_var, 
                       value="safe").pack(side="left", padx=(10, 0))
        ttk.Radiobutton(rating_frame, text="Questionable", variable=self.rating_var, 
                       value="questionable").pack(side="left", padx=(10, 0))
        ttk.Radiobutton(rating_frame, text="Explicit", variable=self.rating_var, 
                       value="explicit").pack(side="left", padx=(10, 0))
        
        # Пропускать дубликаты
        # skip dupl
        self.skip_duplicates_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, text="Пропускать уже скачанные арты", 
                       variable=self.skip_duplicates_var).grid(row=3, column=1, sticky="w", pady=2)
        
        # Сортировка
        # sort
        ttk.Label(settings_frame, text="Сортировка:").grid(row=4, column=0, sticky="w", pady=2)
        self.sort_var = tk.StringVar(value="date")
        sort_frame = ttk.Frame(settings_frame)
        sort_frame.grid(row=4, column=1, columnspan=2, sticky="w", padx=5, pady=2)
        ttk.Radiobutton(sort_frame, text="По дате", variable=self.sort_var, 
                       value="date").pack(side="left")
        ttk.Radiobutton(sort_frame, text="По рейтингу", variable=self.sort_var, 
                       value="score").pack(side="left", padx=(10, 0))
        
        # Кнопки управления
        # Control buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill="x", pady=(0, 10))
        
        self.start_button = ttk.Button(buttons_frame, text="Начать загрузку", 
                                      command=self.start_download)
        self.start_button.pack(side="left", padx=(0, 5))
        
        self.stop_button = ttk.Button(buttons_frame, text="Остановить", 
                                     command=self.stop_download_process, state="disabled")
        self.stop_button.pack(side="left")
        
        # Прогресс бар
        # progress bar
        self.progress = ttk.Progressbar(main_frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", pady=(0, 10))
        
        # Статус
        # Status
        self.status_var = tk.StringVar(value="Готов к работе")
        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.pack(anchor="w")
        
        # Лог
        # log
        log_frame = ttk.LabelFrame(main_frame, text="Лог загрузки", padding="10")
        log_frame.pack(fill="both", expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, wrap="word")
        self.log_text.pack(fill="both", expand=True)
        
        self.update_tags_history_listbox()
    
    def insert_tag(self, tag):
        """Вставляет тег в поле ввода"""
        current_text = self.tags_entry.get()
        if current_text:
            new_text = current_text + " " + tag
        else:
            new_text = tag
        self.tags_entry.delete(0, "end")
        self.tags_entry.insert(0, new_text)
    
    def log(self, message):
        """Добавляет сообщение в лог"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        self.log_text.insert("end", log_message)
        self.log_text.see("end")
        self.root.update_idletasks()
    
    def load_tags_history(self):
        """Загружает историю тегов из файла"""
        try:
            if os.path.exists(self.tags_history_file):
                with open(self.tags_history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.log(f"Ошибка загрузки истории тегов: {e}")
        return []
    
    def save_tags_history(self):
        """Сохраняет историю тегов в файл"""
        try:
            with open(self.tags_history_file, 'w', encoding='utf-8') as f:
                json.dump(self.tags_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f"Ошибка сохранения истории тегов: {e}")
    
    def load_downloaded_hashes(self):
        """Загружает хеши скачанных изображений"""
        try:
            if os.path.exists(self.downloaded_hashes_file):
                with open(self.downloaded_hashes_file, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
        except Exception as e:
            self.log(f"Ошибка загрузки хешей: {e}")
        return set()
    
    def save_downloaded_hashes(self):
        """Сохраняет хеши скачанных изображений"""
        try:
            with open(self.downloaded_hashes_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.downloaded_hashes), f)
        except Exception as e:
            self.log(f"Ошибка сохранения хешей: {e}")
    
    def load_downloaded_ids(self):
        """Загружает ID скачанных постов"""
        try:
            if os.path.exists(self.downloaded_ids_file):
                with open(self.downloaded_ids_file, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
        except Exception as e:
            self.log(f"Ошибка загрузки ID: {e}")
        return set()
    
    def save_downloaded_ids(self):
        """Сохраняет ID скачанных постов"""
        try:
            with open(self.downloaded_ids_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.downloaded_ids), f)
        except Exception as e:
            self.log(f"Ошибка сохранения ID: {e}")
    
    def add_to_tags_history(self):
        """Добавляет текущие теги в историю"""
        tags = self.tags_entry.get().strip()
        if tags and tags not in self.tags_history:
            self.tags_history.append(tags)
            self.save_tags_history()
            self.update_tags_history_listbox()
            self.log(f"Теги добавлены в историю: {tags}")
    
    def remove_from_tags_history(self):
        """Удаляет выбранные теги из истории"""
        selection = self.tags_history_listbox.curselection()
        if selection:
            index = selection[0]
            removed_tags = self.tags_history.pop(index)
            self.save_tags_history()
            self.update_tags_history_listbox()
            self.log(f"Теги удалены из истории: {removed_tags}")
    
    def on_tags_history_select(self, event):
        """Обрабатывает выбор тегов из истории"""
        selection = self.tags_history_listbox.curselection()
        if selection:
            tags = self.tags_history[selection[0]]
            self.tags_entry.delete(0, "end")
            self.tags_entry.insert(0, tags)
    
    def update_tags_history_listbox(self):
        """Обновляет список истории тегов"""
        self.tags_history_listbox.delete(0, "end")
        for tags in self.tags_history:
            self.tags_history_listbox.insert("end", tags)
    
    def select_download_folder(self):
        """Выбирает папку для сохранения"""
        folder = filedialog.askdirectory()
        if folder:
            self.download_path_var.set(folder)
    
    def calculate_image_hash(self, image_data):
        """Вычисляет хеш изображения для проверки дубликатов"""
        return hashlib.md5(image_data).hexdigest()
    
    def download_image(self, url, filename, post_id):
        """Скачивает изображение по URL"""
        try:
            # Проверяем по ID поста
            # id check of post
            if self.skip_duplicates_var.get() and post_id in self.downloaded_ids:
                return False, "Пропущено (уже скачано по ID)"
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Проверяем дубликаты по хешу
            # check dupl by hesh
            if self.skip_duplicates_var.get():
                image_hash = self.calculate_image_hash(response.content)
                if image_hash in self.downloaded_hashes:
                    return False, "Пропущено (дубликат по хешу)"
                
                self.downloaded_hashes.add(image_hash)
                self.downloaded_ids.add(post_id)
            
            # Сохраняем изображение
            # download the pic
            filepath = os.path.join(self.download_path, filename)
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            return True, "Успешно"
            
        except requests.RequestException as e:
            return False, f"Ошибка сети: {e}"
        except Exception as e:
            return False, f"Ошибка: {e}"
    
    def search_gelbooru_posts(self, tags, limit=100, pid=0):
        """Ищет посты на Gelbooru по тегам"""
        try:
            # Базовые параметры
            # base params
            params = {
                'page': 'dapi',
                's': 'post',
                'q': 'index',
                'tags': tags,
                'limit': limit,
                'pid': pid,
                'json': 1
            }
            
            # Добавляем API credentials в правильном формате
            # adding api credential in correct format
            api_key = self.api_key_entry.get().strip()
            user_id = self.user_id_entry.get().strip()
            
            if api_key and user_id:
                # Убираем возможные & в начале если есть
                # remove the possible & at the beginning if there is
                if api_key.startswith('&'):
                    api_key = api_key[1:]
                if user_id.startswith('&'):
                    user_id = user_id[1:]
                
                # Добавляем credentials
                params['api_key'] = api_key
                params['user_id'] = user_id
            
            # Добавляем рейтинг если выбран
            # additg rating if selected
            if self.rating_var.get() != 'all':
                params['tags'] = f"{tags} rating:{self.rating_var.get()}"
            
            # Добавляем сортировку
            # adding sorting
            if self.sort_var.get() == 'score':
                params['tags'] = f"{params['tags']} sort:score:desc"
            else:
                params['tags'] = f"{params['tags']} sort:id:desc"
            
            self.log(f"Поиск с параметрами: {params['tags']}")
            
            response = requests.get(
                'https://gelbooru.com/index.php',
                params=params,
                timeout=15,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            
            if response.status_code != 200:
                self.log(f"Ошибка API: {response.status_code}")
                return []
            
            data = response.json()
            
            if 'post' in data and data['post']:
                return data['post']
            else:
                self.log("Посты не найдены или пустой ответ")
                return []
            
        except requests.RequestException as e:
            self.log(f"Ошибка сети при поиске: {e}")
            return []
        except json.JSONDecodeError as e:
            self.log(f"Ошибка парсинга JSON: {e}")
            self.log(f"Ответ сервера: {response.text[:200]}...")
            return []
        except Exception as e:
            self.log(f"Неизвестная ошибка при поиске: {e}")
            return []
    
    def get_safe_filename(self, post):
        """Создает безопасное имя файла из данных поста"""
        # Пробуем получить оригинальное имя файла
        # trying to collect original file name
        if 'file_url' in post and post['file_url']:
            original_name = os.path.basename(post['file_url'])
            name, ext = os.path.splitext(original_name)
        else:
            # Используем ID поста если нет URL
            # using ID of post if there is no url
            name = f"gelbooru_{post['id']}"
            ext = ".jpg"  # дефолтное расширение / default resolution
        
        # Добавляем теги для удобства (первые 3 тега)
        # adding tags for convenience
        tags = post.get('tags', '').split()
        tag_suffix = "_".join(tags[:3]) if tags else "unknown"
        
        safe_filename = f"{post['id']}_{tag_suffix}{ext}"
        
        # Заменяем небезопасные символы
        # replacing not safe symbols
        safe_chars = " -_."
        return ''.join(c if c.isalnum() or c in safe_chars else '_' for c in safe_filename)
    
    def download_thread(self):
        """Поток для загрузки изображений"""
        try:
            self.is_downloading = True
            self.stop_download = False
            
            # Получаем настройки
            # collecting settings
            tags = self.tags_entry.get().strip()
            limit = int(self.limit_var.get())
            self.download_path = self.download_path_var.get()
            
            # Проверяем обязательные поля
            # checking required boxes
            if not tags:
                messagebox.showerror("Ошибка", "Введите теги для поиска")
                return
            
            if not self.download_path:
                messagebox.showerror("Ошибка", "Выберите папку для сохранения")
                return
            
            # Создаем папку если не существует
            # creating folder if not existing
            os.makedirs(self.download_path, exist_ok=True)
            
            self.log(f"Начинаем загрузку с тегами: {tags}")
            self.log(f"Лимит: {limit} постов")
            self.log(f"Папка: {self.download_path}")
            
            downloaded_count = 0
            skipped_count = 0
            error_count = 0
            page = 0
            
            self.progress['maximum'] = limit
            self.progress['value'] = 0
            
            while downloaded_count < limit and not self.stop_download:
                posts_per_page = min(100, limit - downloaded_count)
                self.log(f"Поиск постов (страница {page + 1}, лимит: {posts_per_page})...")
                
                posts = self.search_gelbooru_posts(tags, posts_per_page, page)
                
                if not posts:
                    self.log("Больше постов не найдено")
                    break
                
                self.log(f"Найдено {len(posts)} постов для обработки")
                
                for post in posts:
                    if self.stop_download or downloaded_count >= limit:
                        break
                    
                    try:
                        post_id = post.get('id')
                        if not post_id:
                            continue
                        
                        # Получаем URL изображения
                        # collecting URL of pic
                        image_url = post.get('file_url')
                        if not image_url:
                            self.log(f"Пост {post_id}: нет URL изображения")
                            continue
                        
                        # Создаем имя файла
                        # creating name of file
                        filename = self.get_safe_filename(post)
                        filepath = os.path.join(self.download_path, filename)
                        
                        # Пропускаем если файл уже существует
                        # skiping file existing
                        if os.path.exists(filepath):
                            self.log(f"Пост {post_id}: пропущено (файл существует)")
                            skipped_count += 1
                            continue
                        
                        self.log(f"Пост {post_id}: скачивание...")
                        
                        success, message = self.download_image(image_url, filename, str(post_id))
                        
                        if success:
                            downloaded_count += 1
                            self.log(f"Пост {post_id}: успешно скачан")
                        else:
                            error_count += 1
                            self.log(f"Пост {post_id}: {message}")
                        
                        # Обновляем прогресс
                        # updating progress
                        self.progress['value'] = downloaded_count
                        self.status_var.set(f"Скачано: {downloaded_count} | Ошибок: {error_count} | Пропущено: {skipped_count}")
                        
                        # Соблюдаем лимит API (10 запросов в секунду)
                        # follow the limit of API (10 requests per second)
                        time.sleep(0.12)  # Немного больше для надежности / a little more for safety
                        
                    except Exception as e:
                        error_count += 1
                        self.log(f"Ошибка обработки поста {post.get('id', 'unknown')}: {e}")
                
                page += 1
                
                # Пауза между страницами
                # pause between pages
                if not self.stop_download and downloaded_count < limit:
                    time.sleep(1)
            
            # Сохраняем хеши и ID
            # Saving hashes and IDs
            if self.skip_duplicates_var.get():
                self.save_downloaded_hashes()
                self.save_downloaded_ids()
            
            self.log(f"Загрузка завершена! Скачано: {downloaded_count}, Ошибок: {error_count}, Пропущено: {skipped_count}")
            messagebox.showinfo("Готово", f"Загрузка завершена!\nСкачано: {downloaded_count}\nОшибок: {error_count}\nПропущено: {skipped_count}")
            
        except Exception as e:
            self.log(f"Критическая ошибка: {e}")
            messagebox.showerror("Ошибка", f"Произошла ошибка: {e}")
        finally:
            self.is_downloading = False
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
            self.status_var.set("Готов к работе")
    
    def start_download(self):
        """Начинает процесс загрузки"""
        if self.is_downloading:
            return
        
        # Запускаем в отдельном потоке
        # Launch in different flow
        download_thread = threading.Thread(target=self.download_thread)
        download_thread.daemon = True
        download_thread.start()
        
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.status_var.set("Загрузка...")
    
    def stop_download_process(self):
        """Останавливает процесс загрузки"""
        self.stop_download = True
        self.status_var.set("Остановка...")
        self.log("Остановка загрузки...")

def main():
    root = tk.Tk()
    app = GelbooruDownloader(root)
    root.mainloop()

if __name__ == "__main__":
    main()
