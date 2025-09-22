import os.path
from customtkinter import *
import base64
import io
import threading
from socket import *
from tkinter import filedialog
from PIL import Image


class MainWindow(CTk):
    def __init__(self):
        super().__init__()
        self.geometry("600x500")
        self.title("💬 Чат")
        self.label = None
        self.avatars = {}  # тут зберігаються аватари користувачів

        # дефолтний аватар (іконка)
        default_img = Image.new("RGB", (32, 32), color="gray")
        self.default_avatar = CTkImage(default_img, size=(32, 32))


        # --- Глобальна тема ---
        set_appearance_mode("dark")
        set_default_color_theme("blue")

        # --- Бокова Панель ---
        self.menu_frame = CTkFrame(self, width=40, height=self.winfo_height(), fg_color="#1e1e2e")
        self.menu_frame.pack_propagate(False)
        self.menu_frame.place(x=0, y=0)

        self.is_show_menu = False
        self.speed_animate_menu = -6

        self.btn = CTkButton(self, text='▶️', command=self.toggle_show_menu, width=30, fg_color="#313244")
        self.btn.place(x=0, y=0)

        self.avatar_btn = CTkButton(self.menu_frame, text="🖼️ Змінити аватар",
                                    command=self.change_avatar, fg_color="#f38ba8")
        self.theme_btn = CTkButton(self.menu_frame, text="🎨 Змінити тему",
                                   command=self.toggle_theme, fg_color="#89b4fa")

        # спочатку ховаємо їх, покажемо при відкритті меню
        self.avatar_btn.pack_forget()
        self.theme_btn.pack_forget()

        # --- Область чата ---
        self.chat_field = CTkScrollableFrame(
            self,
            fg_color="#11111b",
            width=self.winfo_width() - self.menu_frame.winfo_width(),
            height=self.winfo_height() - 50
        )
        self.chat_field.place(x=40, y=0)

        # --- Нижня панель ---
        self.message_entry = CTkEntry(self, placeholder_text="✍️ Напишіть повідомлення...",
                                      height=40, border_width=2, corner_radius=15)
        self.message_entry.place(x=50, y=self.winfo_height() - 45)

        self.send_button = CTkButton(self, text="➤", width=50, height=40,
                                     command=self.send_message, corner_radius=20, fg_color="#89b4fa")
        self.send_button.place(x=self.winfo_width() - 55, y=self.winfo_height() - 45)

        self.open_img_button = CTkButton(self, text='📂', width=50, height=40,
                                         command=self.open_image, corner_radius=20, fg_color="#313244")
        self.open_img_button.place(x=self.winfo_width() - 110, y=self.winfo_height() - 45)

        self.addptive_ui()

        self.username = "Test"
        self.current_theme = "dark"

        try:
            self.sock = socket(AF_INET, SOCK_STREAM)
            #self.sock.connect(("localhost", 2525))
            self.sock.connect(("0.tcp.ngrok.io", 15105))
            hello = f"TEXT@{self.username}@[SYSTEM] {self.username} приєднався(лась) до чату!\n"
            self.sock.send(hello.encode('utf-8'))

            threading.Thread(target=self.recv_message, daemon=True).start()
        except Exception as e:
            self.add_message(f"❌ Не вдалося підключитися до сервера: {e}", system=True)

    def addptive_ui(self):
        self.menu_frame.configure(height=self.winfo_height())

        # ✅ лишаємо тільки place з координатами
        self.chat_field.place(x=self.menu_frame.winfo_width(), y=0)
        self.chat_field.configure(
            width=self.winfo_width() - self.menu_frame.winfo_width(),
            height=self.winfo_height() - 50
        )

        self.send_button.place(x=self.winfo_width() - 55, y=self.winfo_height() - 45)
        self.open_img_button.place(x=self.winfo_width() - 110, y=self.winfo_height() - 45)

        # ✅ width у конструкторі, тут тільки координати
        self.message_entry.place(
            x=self.menu_frame.winfo_width() + 10,
            y=self.winfo_height() - 45
        )
        self.message_entry.configure(
            width=self.winfo_width() - self.menu_frame.winfo_width() - 130
        )

        self.after(50, self.addptive_ui)

    def toggle_show_menu(self):
        self.is_show_menu = not self.is_show_menu
        self.speed_animate_menu *= -1
        self.btn.configure(text='◀️' if self.is_show_menu else '▶️')
        self.show_menu()

        if self.is_show_menu:
            # показуємо кнопки, якщо меню відкрите
            self.avatar_btn.pack(pady=5)
            self.theme_btn.pack(pady=5)

            self.label = CTkLabel(self.menu_frame, text='Ваше імʼя:', text_color="white")
            self.label.pack(pady=20)
            self.entry = CTkEntry(self.menu_frame)
            self.entry.pack(pady=5)
            self.save_btn = CTkButton(self.menu_frame, text="💾 Зберегти",
                                      command=self.save_name, fg_color="#a6e3a1")
            self.save_btn.pack(pady=10)
        else:
            # ховаємо кнопки і поля, коли меню закрите
            self.avatar_btn.pack_forget()
            self.theme_btn.pack_forget()
            if self.label:
                self.label.destroy()
                self.entry.destroy()
                self.save_btn.destroy()

    def show_menu(self):
        self.menu_frame.configure(width=self.menu_frame.winfo_width() + self.speed_animate_menu)
        if self.is_show_menu and self.menu_frame.winfo_width() < 200:
            self.after(10, self.show_menu)
        elif not self.is_show_menu and self.menu_frame.winfo_width() > 40:
            self.after(10, self.show_menu)
            if self.label:
                self.label.destroy()
                self.entry.destroy()
                self.save_btn.destroy()

    def save_name(self):
        new_name = self.entry.get().strip()
        if new_name:
            self.username = new_name
            self.add_message("✅ Ваш новий нік: " + self.username, system=True)

    def add_message(self, text, img=None, system=False, author=None):
        # вибираємо колір фону для повідомлення
        if system:
            bg_color = "#45475a" if self.current_theme == "dark" else "#b0b0b0"
        else:
            bg_color = "#313244" if self.current_theme == "dark" else "#e0e0e0"

        message_frame = CTkFrame(self.chat_field,
                                 fg_color=bg_color,
                                 corner_radius=12)
        message_frame.pack(pady=5, padx=10, anchor='w')

        wrapleng_size = self.winfo_width() - self.menu_frame.winfo_width() - 100

        # аватар
        if author and author in self.avatars:
            avatar_img = self.avatars[author]
        else:
            avatar_img = self.default_avatar

        avatar_label = CTkLabel(message_frame, image=avatar_img, text="")
        avatar_label.pack(side="left", padx=5, pady=5)

        # текст або зображення
        text_color = "white" if self.current_theme == "dark" else "black"

        if not img:
            CTkLabel(message_frame, text=text, wraplength=wrapleng_size,
                     text_color=text_color, justify='left').pack(side="left", padx=10, pady=5)
        else:
            CTkLabel(message_frame, text=text, wraplength=wrapleng_size,
                     text_color=text_color, image=img, compound='top',
                     justify='left').pack(side="left", padx=10, pady=5)

    def send_message(self):
        message = self.message_entry.get()
        if message:
            data = f"TEXT@{self.username}@{message}\n"
            try:
                self.sock.send(data.encode("utf-8"))
                self.add_message(message)
            except:
                self.add_message("⚠️ Повідомлення не вдалося надіслати", system=True)
        self.message_entry.delete(0, END)


    def recv_message(self):
        buffer = ""
        while True:
            try:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                buffer += chunk.decode('utf-8', errors='ignore')
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    self.handle_line(line.strip())
            except:
                break


    def handle_line(self, line):
        if not line:
            return
        parts = line.split("@", 3)
        msg_type = parts[0]

        if msg_type == "TEXT":
            if len(parts) >= 3:
                author, message = parts[1], parts[2]
                self.add_message(f"{author}: {message}", author=author)

        elif msg_type == "IMAGE":
            if len(parts) >= 4:
                author, filename, b64_img = parts[1], parts[2], parts[3]
                try:
                    img_data = base64.b64decode(b64_img)
                    pil_img = Image.open(io.BytesIO(img_data))
                    ctk_img = CTkImage(pil_img, size=(200, 200))
                    self.add_message(f"{author} надіслав(ла) зображення: {filename}",
                                     img=ctk_img, author=author)
                except Exception as e:
                    self.add_message(f"⚠️ Помилка зображення: {e}", system=True)

        elif msg_type == "AVATAR":
            if len(parts) >= 3:
                author, b64_img = parts[1], parts[2]
                try:
                    img_data = base64.b64decode(b64_img)
                    pil_img = Image.open(io.BytesIO(img_data))
                    avatar = CTkImage(pil_img, size=(32, 32))
                    self.avatars[author] = avatar
                    self.add_message(f"👤 {author} змінив(ла) аватар", system=True)
                except Exception:
                    self.add_message(f"⚠️ Помилка завантаження аватара {author}", system=True)

        else:
            self.add_message(line, system=True)

    def toggle_theme(self):
        if self.current_theme == "dark":
            set_appearance_mode("light")
            self.current_theme = "light"
        else:
            set_appearance_mode("dark")
            self.current_theme = "dark"

        self.update_theme()

    def update_theme(self):
        # змінюємо колір меню та кнопок
        if self.current_theme == "dark":
            self.menu_frame.configure(fg_color="#1e1e2e")
            self.chat_field.configure(fg_color="#11111b")
            self.send_button.configure(fg_color="#89b4fa")
            self.open_img_button.configure(fg_color="#313244")
            if hasattr(self, "avatar_btn"):
                self.avatar_btn.configure(fg_color="#f38ba8")
            if hasattr(self, "theme_btn"):
                self.theme_btn.configure(fg_color="#89b4fa")
        else:  # світла тема
            self.menu_frame.configure(fg_color="#e0e0e0")
            self.chat_field.configure(fg_color="#f8f8f8")
            self.send_button.configure(fg_color="#4c7bd9")
            self.open_img_button.configure(fg_color="#cccccc")
            if hasattr(self, "avatar_btn"):
                self.avatar_btn.configure(fg_color="#f28ca0")
            if hasattr(self, "theme_btn"):
                self.theme_btn.configure(fg_color="#4c7bd9")

        # оновлюємо всі повідомлення у чаті
        for child in self.chat_field.winfo_children():
            if isinstance(child, CTkFrame):
                # визначаємо фон для системних та звичайних повідомлень
                if hasattr(child, "system") and child.system:
                    child.configure(fg_color="#45475a" if self.current_theme == "dark" else "#b0b0b0")
                else:
                    child.configure(fg_color="#313244" if self.current_theme == "dark" else "#e0e0e0")
                # змінюємо колір тексту всередині
                for lbl in child.winfo_children():
                    if isinstance(lbl, CTkLabel):
                        lbl.configure(text_color="white" if self.current_theme == "dark" else "black")

    def change_avatar(self):
        file_name = filedialog.askopenfilename()
        if not file_name:
            return
        try:
            with open(file_name, 'rb') as f:
                raw = f.read()
            b64 = base64.b64encode(raw).decode()
            data = f"AVATAR@{self.username}@{b64}\n"
            self.sock.send(data.encode())
        except Exception:
            self.add_message("❌ Не вдалося змінити аватар", system=True)

    def open_image(self):
        file_name = filedialog.askopenfilename()
        if not file_name:
            return
        try:
            with open(file_name, 'rb') as f:
                raw = f.read()

            b64 = base64.b64encode(raw).decode()
            short_name = os.path.basename(file_name)
            data = f"IMAGE@{self.username}@{short_name}@{b64}\n"
            self.sock.send(data.encode())
        except Exception:
            self.add_message("❌ Не вдалося надіслати зображення", system=True)



win = MainWindow()
win.mainloop()
