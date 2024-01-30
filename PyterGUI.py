import os
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, font
from datetime import datetime
from threading import Thread
from ImageScraper import ImageScraper
from ttkbootstrap import Style
import re

def sort_folders_by_date(folder_path):
    folders = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]
    date_time_pattern = re.compile(r'(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})')
    date_time_folders_dict = {}

    for folder in folders:
        match = date_time_pattern.search(folder)
        if match:
            date_str, time_str = match.groups()
            date_time_folders_dict.setdefault(date_str, []).append((folder, time_str))

    sorted_folder = os.path.join(folder_path, "Sorted")
    os.makedirs(sorted_folder, exist_ok=True)

    for date, folders_with_time in date_time_folders_dict.items():
        date_folder = os.path.join(sorted_folder, date)
        os.makedirs(date_folder, exist_ok=True)

        for folder, time_str in folders_with_time:
            source_path = os.path.join(folder_path, folder)
            destination_folder = os.path.join(date_folder, time_str)
            os.makedirs(destination_folder, exist_ok=True)

            for file_name in os.listdir(source_path):
                source_file = os.path.join(source_path, file_name)
                destination_file = os.path.join(destination_folder, file_name)
                os.rename(source_file, destination_file)

            os.rmdir(source_path)

    for root, dirs, files in os.walk(folder_path, topdown=False):
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            if not os.listdir(dir_path):
                os.rmdir(dir_path)

    print("Folders sorted and cleared")

class ImageDownloaderApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Pyterest")

        self.stop_flag = False

        self.tags = tk.StringVar(value="nature")
        self.save_folder_path = tk.StringVar(value="Default/default_download")
        self.max_images_var = tk.StringVar(value="10")
        self.credentials_file = tk.StringVar(value="Default/credentials.txt")

        custom_font = font.Font(family='Courier New', size=11)
        self.style = Style(theme="darkly")

        self.master.minsize(450, 500)
        self.master.maxsize(600, 600)
        self.master.geometry("450x500")

        icon_path = "app.ico"
        self.master.iconbitmap(icon_path)

        self.style.configure('TButton', font=custom_font)
        self.style.configure('TLabel', font=custom_font)

        self.create_widgets()

    def create_widgets(self):

        self.tags_entry = ttk.Entry(self.master, textvariable=self.tags)
        self.tags_entry.grid(row=0, column=0, pady=(20, 10), padx=(25, 5), columnspan=3, sticky='e')

        choose_tags_btn = ttk.Button(self.master, text="◦◦◦", command=self.choose_tags_file, style="info.TButton")
        choose_tags_btn.grid(row=0, column=3, pady=(20, 10), padx=(5, 25), columnspan=1, sticky='w')

        self.folder_entry = ttk.Entry(self.master, textvariable=self.save_folder_path, state='readonly')
        self.folder_entry.grid(row=1, column=0, pady=(10, 5), padx=(25, 5), columnspan=3, sticky='w')

        choose_folder_btn = ttk.Button(self.master, text="◦◦◦", command=self.choose_save_folder, style="info.TButton")
        choose_folder_btn.grid(row=1, column=3, pady=(10, 5), padx=(5, 25), columnspan=1, sticky='w')

        self.cred_entry = ttk.Entry(self.master, textvariable=self.credentials_file, state='readonly')
        self.cred_entry.grid(row=2, column=0, pady=(5, 10), padx=(25, 5), columnspan=3, sticky='e')

        choose_cred_btn = ttk.Button(self.master, text="◦◦◦", command=self.choose_cred_file, style="info.TButton")
        choose_cred_btn.grid(row=2, column=3, pady=(5, 10), padx=(5, 25), columnspan=1, sticky='w')

        ttk.Label(self.master, text="Image amount:").grid(row=3, column=0, pady=(5, 10), padx=(25, 5), sticky='w')
        ttk.Entry(self.master, textvariable=self.max_images_var).grid(row=3, column=1, pady=(5, 10), padx=(5, 25), columnspan=3, sticky='e')

        self.download_btn = ttk.Button(self.master, text="Download", command=self.start_download, style="success.TButton")
        self.download_btn.grid(row=4, column=0, columnspan=2, pady=(5, 5), padx=(25, 5), sticky='w')

        self.stop_btn = ttk.Button(self.master, text="Stop", command=self.stop_download, style="danger.TButton")
        self.stop_btn.grid(row=4, column=2, columnspan=2, pady=(5, 5), padx=(5, 25), sticky='e')

        self.progressbar = ttk.Progressbar(self.master, length=300, mode="determinate")
        self.progressbar.grid(row=5, column=0, columnspan=4, pady=(5, 5), padx=(25), sticky='w')

        self.log_field = scrolledtext.ScrolledText(self.master, height=10, width=50, wrap=tk.WORD)
        self.log_field.grid(row=6, column=0, columnspan=4, pady=(5, 5), padx=(25), sticky='w')

        self.sort_folders_btn = ttk.Button(self.master, text="Sort folders", command=self.sort_folders, style="warning.TButton")
        self.sort_folders_btn.grid(row=7, column=0, columnspan=4, pady=(5, 25), padx=(25), sticky='w')

        for i in range(6):
            self.master.grid_rowconfigure(i, weight=1)

        for i in range(2):
            self.master.grid_columnconfigure(i, weight=1)

        for widget in self.master.winfo_children():
            widget.grid_configure(sticky="nsew")

    def choose_tags_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        with open(file_path, 'r') as file:
            self.tags.set(file.read().split())
        self.insert_log(f"Tags path: {file_path}")

    def stop_download(self):
        self.stop_flag = True
        self.insert_log("Process canceled")

    def choose_save_folder(self):
        folder_path = filedialog.askdirectory()
        self.save_folder_path.set(folder_path)
        self.insert_log(f"Folder path: {folder_path}")

    def choose_cred_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        self.credentials_file.set(file_path)
        self.insert_log(f"Login path: {file_path}")

    def sort_folders(self):
        sort_folder = filedialog.askdirectory()

        if sort_folder:
            self.insert_log(f"Sorting started in {sort_folder}")
            sort_folders_by_date(sort_folder)
            self.insert_log(f"Sorting complete. Folders sorted by date.")
        else:
            self.insert_log("Sorting canceled. No chosen folder.")

    def start_download(self):
        save_folder_path = self.save_folder_path.get()
        credentials_file = self.credentials_file.get()
        max_images = int(self.max_images_var.get()) if self.max_images_var.get() else None

        current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        download_folder = os.path.join(save_folder_path, f"Download_{current_datetime}")
        os.makedirs(download_folder, exist_ok=True)
        self.insert_log(f"Download folder created: {download_folder}")

        scraper = ImageScraper(self, self.tags, download_folder, max_images, credentials_file)
        scraper.start_download()

    def insert_log(self, message):
        self.log_field.insert(tk.END, f"{message}\n")
        self.log_field.yview(tk.END)

    def clear_log(self):
        self.log_field.delete('1.0', tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageDownloaderApp(root)
    root.mainloop()
