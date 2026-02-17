import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import threading
import subprocess
from PIL import Image, ImageTk
import io

try:
    import darkdetect
    HAS_DARKDETECT = True
except ImportError:
    HAS_DARKDETECT = False

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

from clip_service import CLIPService
from cache_manager import CacheManager
from search_engine import SearchEngine


SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}


THEMES = {
    'light': {
        'bg': '#FFFFFF',
        'fg': '#000000',
        'frame_bg': '#F0F0F0',
        'canvas_bg': '#FFFFFF',
        'entry_bg': '#FFFFFF',
        'entry_fg': '#000000',
        'text_bg': '#FFFFFF',
        'text_fg': '#000000',
        'accent': '#0078D4',
    },
    'dark': {
        'bg': '#1E1E1E',
        'fg': '#FFFFFF',
        'frame_bg': '#2D2D2D',
        'canvas_bg': '#1E1E1E',
        'entry_bg': '#3C3C3C',
        'entry_fg': '#FFFFFF',
        'text_bg': '#2D2D2D',
        'text_fg': '#FFFFFF',
        'accent': '#0078D4',
    }
}


class ImageSearchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CLIP Image Search")
        self.root.geometry("1000x700")

        self.clip_service = CLIPService()
        self.cache_manager = CacheManager()
        self.search_engine = SearchEngine(self.cache_manager, self.clip_service)

        self.folders = set()
        self.model_loaded = False
        self.embedding = False

        self.current_theme = 'dark' if self._detect_dark_mode() else 'light'

        self._setup_ui()
        self._apply_theme()

    def _detect_dark_mode(self):
        if HAS_DARKDETECT:
            try:
                return darkdetect.isDark()
            except:
                return False
        return False

    def _setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        top_frame = ttk.Frame(main_frame)
        top_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        self.folder_label = ttk.Label(top_frame, text="Folders to scan:")
        self.folder_label.grid(row=0, column=0, sticky=tk.W)
        
        self.folders_text = tk.Text(top_frame, height=3, width=60, state='disabled')
        self.folders_text.grid(row=1, column=0, padx=(0, 10), pady=5)

        btn_frame = ttk.Frame(top_frame)
        btn_frame.grid(row=1, column=1)

        self.add_folder_btn = ttk.Button(btn_frame, text="Add Folder", command=self._add_folder)
        self.add_folder_btn.pack(fill=tk.X, pady=2)
        
        self.gen_embeddings_btn = ttk.Button(btn_frame, text="Generate Embeddings", command=self._start_embedding_thread)
        self.gen_embeddings_btn.pack(fill=tk.X, pady=2)
        
        self.clear_cache_btn = ttk.Button(btn_frame, text="Clear Cache", command=self._clear_cache)
        self.clear_cache_btn.pack(fill=tk.X, pady=2)

        self.toggle_theme_btn = ttk.Button(btn_frame, text="Toggle Theme", command=self._toggle_theme)
        self.toggle_theme_btn.pack(fill=tk.X, pady=2)

        self.stats_label = ttk.Label(btn_frame, text="", font=('Roboto', 8))
        self.stats_label.pack(pady=5)
        self._update_stats()

        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="5")
        status_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        self.status_frame = status_frame
        
        self.status_label = ttk.Label(status_frame, text="Ready")
        self.status_label.pack()

        self.progress = ttk.Progressbar(status_frame, mode='determinate')
        self.progress.pack(fill=tk.X, pady=5)

        search_frame = ttk.LabelFrame(main_frame, text="Search", padding="5")
        search_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        self.search_frame = search_frame

        self.search_label = ttk.Label(search_frame, text="Query:")
        self.search_label.grid(row=0, column=0, sticky=tk.W)
        
        self.search_entry = ttk.Entry(search_frame, width=60)
        self.search_entry.grid(row=0, column=1, padx=5)
        self.search_entry.bind('<Return>', lambda e: self._start_search())
        
        self.search_btn = ttk.Button(search_frame, text="Search", command=self._start_search)
        self.search_btn.grid(row=0, column=2)

        self.drop_image_path = None
        
        if HAS_DND:
            self.drop_frame = tk.Frame(search_frame, width=200, height=60, relief="solid", bd=2)
            self.drop_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
            self.drop_frame.drop_target_register(DND_FILES)
            self.drop_frame.dnd_bind('<<Drop>>', self._on_drop)
            self.drop_label = tk.Label(self.drop_frame, text="Drag image here or click to browse")
            self.drop_label.place(relx=0.5, rely=0.5, anchor="center")
            self.drop_frame.bind('<Button-1>', lambda e: self._browse_image())
        else:
            self.drop_frame = tk.Frame(search_frame, width=200, height=60, relief="solid", bd=2)
            self.drop_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
            self.drop_label = tk.Label(self.drop_frame, text="Click to browse image")
            self.drop_label.place(relx=0.5, rely=0.5, anchor="center")
            self.drop_frame.bind('<Button-1>', lambda e: self._browse_image())
        
        self.clear_img_btn = ttk.Button(search_frame, text="Clear Image", command=self._clear_dropped_image)
        self.clear_img_btn.grid(row=1, column=2, padx=5)

        self.results_canvas = tk.Canvas(main_frame, bg='white')
        self.results_canvas.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.results_canvas.yview)
        scrollbar.grid(row=3, column=2, sticky=(tk.N, tk.S))
        self.results_canvas.configure(yscrollcommand=scrollbar.set)

        self.results_frame = ttk.Frame(self.results_canvas)
        self.results_canvas.create_window((0, 0), window=self.results_frame, anchor='nw')

        self.results_frame.bind('<Configure>', lambda e: self.results_canvas.configure(scrollregion=self.results_canvas.bbox('all')))

        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)

    def _apply_theme(self):
        theme = THEMES[self.current_theme]
        
        self.root.configure(bg=theme['bg'])
        
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('.', background=theme['bg'], foreground=theme['fg'], font=('Roboto', 10))
        style.configure('TFrame', background=theme['bg'])
        style.configure('TLabelframe', background=theme['bg'], foreground=theme['fg'])
        style.configure('TLabelframe.Label', background=theme['bg'], foreground=theme['fg'])
        style.configure('TButton', font=('Roboto', 10))
        
        self.folder_label.configure(background=theme['bg'], foreground=theme['fg'])
        self.stats_label.configure(background=theme['bg'], foreground=theme['fg'])
        self.status_label.configure(background=theme['bg'], foreground=theme['fg'])
        self.search_label.configure(background=theme['bg'], foreground=theme['fg'])
        
        self.folders_text.configure(background=theme['entry_bg'], foreground=theme['entry_fg'], insertbackground=theme['entry_fg'])
        
        self.search_entry.configure(style='Custom.TEntry')
        style.configure('Custom.TEntry', fieldbackground=theme['entry_bg'], foreground=theme['entry_fg'], insertcolor=theme['entry_fg'])
        
        self.results_canvas.configure(background=theme['canvas_bg'])
        
        style.configure('Vertical.TScrollbar', background=theme['frame_bg'])
        
        style.configure('Custom.TFrame', background=theme['frame_bg'])
        
        if hasattr(self, 'drop_frame'):
            self.drop_frame.configure(background=theme['entry_bg'], highlightbackground=theme['fg'], highlightcolor=theme['fg'])
        if hasattr(self, 'drop_label'):
            self.drop_label.configure(background=theme['entry_bg'], foreground=theme['fg'])

    def _toggle_theme(self):
        self.current_theme = 'dark' if self.current_theme == 'light' else 'light'
        self._apply_theme()

    def _add_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folders.add(folder)
            self._update_folders_text()

    def _update_folders_text(self):
        self.folders_text.configure(state='normal')
        self.folders_text.delete('1.0', tk.END)
        for folder in self.folders:
            self.folders_text.insert(tk.END, folder + '\n')
        self.folders_text.configure(state='disabled')

    def _update_stats(self):
        stats = self.cache_manager.get_stats()
        size_mb = stats["cache_size_mb"]
        self.stats_label.config(text=f"Cached: {stats['image_count']} images ({size_mb:.1f} MB)")

    def _get_images_from_folders(self):
        images = []
        for folder in self.folders:
            for root, dirs, files in os.walk(folder):
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in SUPPORTED_EXTENSIONS:
                        img_path = os.path.join(root, f)
                        if not self.cache_manager.has_embedding(img_path):
                            images.append(img_path)
        return images

    def _start_embedding_thread(self):
        if not self.folders:
            messagebox.showwarning("No folders", "Please add at least one folder to scan.")
            return
        
        if self.embedding:
            return
        
        self.embedding = True
        self.status_label.config(text="Loading CLIP model...")
        self.progress.pack_forget()
        
        thread = threading.Thread(target=self._run_embedding)
        thread.start()

    def _run_embedding(self):
        try:
            self.clip_service.load()
            self.model_loaded = True
            
            images = self._get_images_from_folders()
            
            if not images:
                self.root.after(0, lambda: self.status_label.config(text="No new images to process"))
                self.root.after(0, lambda: self._update_stats())
                self.root.after(0, lambda: messagebox.showinfo("Done", "All images already have embeddings!"))
            else:
                self.root.after(0, lambda: self.progress.pack(fill=tk.X, pady=5))
                self.root.after(0, lambda: self._update_progress(0, len(images)))
                
                total = len(images)
                processed = 0
                
                for img_path in images:
                    try:
                        embedding = self.clip_service.get_image_embedding(img_path)
                        self.cache_manager.save_embedding(img_path, embedding)
                    except Exception as e:
                        print(f"Error: {e}")
                    
                    processed += 1
                    self.root.after(0, lambda p=processed, t=total: self._update_progress(p, t))
                
                self.root.after(0, lambda: self.progress.pack_forget())
                self.root.after(0, lambda: self.status_label.config(text=f"Done! {total} images processed"))
                self.root.after(0, lambda: self._update_stats())
                self.root.after(0, lambda: messagebox.showinfo("Done", f"Successfully processed {total} images!"))
        
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
        
        finally:
            self.embedding = False

    def _update_progress(self, current, total):
        self.progress['maximum'] = total
        self.progress['value'] = current
        self.status_label.config(text=f"Processing {current}/{total}...")

    def _clear_cache(self):
        if messagebox.askyesno("Clear Cache", "This will delete all cached embeddings. Continue?"):
            self.cache_manager.clear_all()
            self.status_label.config(text="Cache cleared")
            self._update_stats()

    def _start_search(self):
        query = self.search_entry.get().strip()
        has_text = bool(query)
        has_image = self.drop_image_path is not None and os.path.exists(self.drop_image_path)
        
        if not has_text and not has_image:
            messagebox.showwarning("No input", "Please enter text or drop an image to search")
            return
        
        if not self.model_loaded:
            self.status_label.config(text="Loading CLIP model...")
            thread = threading.Thread(target=self._load_and_search)
            thread.start()
        else:
            self._do_search()

    def _load_and_search(self):
        self.clip_service.load()
        self.model_loaded = True
        self.root.after(0, self._do_search)

    def _do_search(self):
        query = self.search_entry.get().strip()
        has_image = self.drop_image_path is not None and os.path.exists(self.drop_image_path)
        
        if has_image:
            self.status_label.config(text=f"Searching by image: {os.path.basename(self.drop_image_path)}")
            results = self.search_engine.search_by_image(self.drop_image_path)
        else:
            self.status_label.config(text=f"Searching for: {query}")
            results = self.search_engine.search(query)
        
        self._display_results(results)
        self.status_label.config(text=f"Found {len(results)} results")

    def _display_results(self, results):
        for widget in self.results_frame.winfo_children():
            widget.destroy()

        theme = THEMES[self.current_theme]

        if not results:
            ttk.Label(self.results_frame, text="No results found").pack(pady=20)
            return

        row = 0
        col = 0
        max_cols = 4

        for img_path, score in results:
            try:
                img = Image.open(img_path)
                img.thumbnail((150, 150))
                photo = ImageTk.PhotoImage(img)
                
                frame = ttk.Frame(self.results_frame, relief="raised", padding="5")
                frame.grid(row=row, column=col, padx=5, pady=5, sticky=(tk.W, tk.E))
                frame.configure(style='Custom.TFrame')
                
                lbl = ttk.Label(frame, image=photo, cursor="hand2")
                lbl.image = photo
                lbl.pack()
                
                lbl.bind("<Button-1>", lambda e, p=img_path: self._open_image(p))
                lbl.bind("<Button-3>", lambda e, p=img_path, f=frame: self._show_context_menu(e, p, f))
                
                ttk.Label(frame, text=f"{score:.3f}", font=('Roboto', 8)).pack()
                
                safe_filename = ''.join(c if ord(c) < 128 else '?' for c in os.path.basename(img_path))
                ttk.Label(frame, text=safe_filename, font=('Roboto', 7), wraplength=140, cursor="hand2").pack()
                
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1
            
            except Exception as e:
                print(f"Error displaying {img_path}: {e}")

    def _open_image(self, img_path):
        if os.path.exists(img_path):
            subprocess.run(["xdg-open", img_path])

    def _show_context_menu(self, event, img_path, frame):
        theme = THEMES[self.current_theme]
        menu = tk.Menu(frame, tearoff=0, bg=theme['entry_bg'], fg=theme['entry_fg'])
        menu.add_command(label="Open Path", command=lambda: self._open_folder(img_path))
        menu.add_command(label="Copy Path", command=lambda: self._copy_path(img_path))
        menu.tk_popup(event.x_root, event.y_root)

    def _open_folder(self, img_path):
        folder = os.path.dirname(img_path)
        if os.path.exists(folder):
            subprocess.run(["xdg-open", folder])

    def _copy_path(self, img_path):
        self.root.clipboard_clear()
        self.root.clipboard_append(img_path)

    def _on_drop(self, event):
        files = self.root.tk.splitlist(event.data)
        if files:
            self._set_dropped_image(files[0])

    def _browse_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif *.bmp *.webp")]
        )
        if file_path:
            self._set_dropped_image(file_path)

    def _set_dropped_image(self, image_path):
        ext = os.path.splitext(image_path)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            messagebox.showwarning("Invalid file", "Please drop an image file")
            return
        
        self.drop_image_path = image_path
        
        try:
            img = Image.open(image_path)
            img.thumbnail((180, 50))
            photo = ImageTk.PhotoImage(img)
            
            self.drop_label.config(image=photo, text="")
            self.drop_label.image = photo
        except Exception as e:
            print(f"Error loading preview: {e}")
            self.drop_label.config(text=os.path.basename(image_path)[:30])

    def _clear_dropped_image(self):
        self.drop_image_path = None
        self.drop_label.config(image="", text="Drag image here or click to browse")


def main():
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = ImageSearchApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
