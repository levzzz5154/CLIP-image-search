import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import threading
import subprocess
from PIL import Image, ImageTk
import io

from clip_service import CLIPService
from cache_manager import CacheManager
from search_engine import SearchEngine


SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}


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

        self._setup_ui()

    def _setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        top_frame = ttk.Frame(main_frame)
        top_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(top_frame, text="Folders to scan:").grid(row=0, column=0, sticky=tk.W)
        
        self.folders_text = tk.Text(top_frame, height=3, width=60, state='disabled')
        self.folders_text.grid(row=1, column=0, padx=(0, 10), pady=5)

        btn_frame = ttk.Frame(top_frame)
        btn_frame.grid(row=1, column=1)

        ttk.Button(btn_frame, text="Add Folder", command=self._add_folder).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="Generate Embeddings", command=self._start_embedding_thread).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="Clear Cache", command=self._clear_cache).pack(fill=tk.X, pady=2)

        self.stats_label = ttk.Label(btn_frame, text="", font=('Arial', 8))
        self.stats_label.pack(pady=5)
        self._update_stats()

        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="5")
        status_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.status_label = ttk.Label(status_frame, text="Ready")
        self.status_label.pack()

        self.progress = ttk.Progressbar(status_frame, mode='determinate')
        self.progress.pack(fill=tk.X, pady=5)

        search_frame = ttk.LabelFrame(main_frame, text="Search", padding="5")
        search_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(search_frame, text="Query:").grid(row=0, column=0, sticky=tk.W)
        self.search_entry = ttk.Entry(search_frame, width=60)
        self.search_entry.grid(row=0, column=1, padx=5)
        self.search_entry.bind('<Return>', lambda e: self._start_search())
        ttk.Button(search_frame, text="Search", command=self._start_search).grid(row=0, column=2)

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

    def _add_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folders.add(folder)
        self._update_folders_text()

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
        if not query:
            return
        
        if not self.model_loaded:
            self.status_label.config(text="Loading CLIP model...")
            thread = threading.Thread(target=self._load_and_search, args=(query,))
            thread.start()
        else:
            self._do_search(query)

    def _load_and_search(self, query):
        self.clip_service.load()
        self.model_loaded = True
        self.root.after(0, lambda: self._do_search(query))

    def _do_search(self, query):
        self.status_label.config(text=f"Searching for: {query}")
        
        results = self.search_engine.search(query)
        
        self._display_results(results)
        self.status_label.config(text=f"Found {len(results)} results")

    def _display_results(self, results):
        for widget in self.results_frame.winfo_children():
            widget.destroy()

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
                
                lbl = ttk.Label(frame, image=photo, cursor="hand2")
                lbl.image = photo
                lbl.pack()
                
                lbl.bind("<Button-1>", lambda e, p=img_path: self._open_image(p))
                lbl.bind("<Button-3>", lambda e, p=img_path, f=frame: self._show_context_menu(e, p, f))
                
                ttk.Label(frame, text=f"{score:.3f}", font=('Arial', 8)).pack()
                
                ttk.Label(frame, text=os.path.basename(img_path), font=('Arial', 7), wraplength=140, cursor="hand2").pack()
                
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
        menu = tk.Menu(frame, tearoff=0)
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


def main():
    root = tk.Tk()
    app = ImageSearchApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
