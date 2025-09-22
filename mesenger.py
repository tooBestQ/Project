from customtkinter import *
import base64
import io
import threading
import os
import time
from socket import *
from tkinter import filedialog
from PIL import Image
from datetime import datetime

class MainWindow(CTk):
    def __init__(self):
        super().__init__()
        self.geometry("600x500")
        self.title("ChatPro")
        self.label = None

        # --- Змінні ---
        self.username = "Yaroslav"
        self.avatar_path = None
        self.user_avatars = {}  # Словник для аватарок всіх користувачів
        self.sock = None
        self.server_address = ("localhost", 2525)
        self.connected = False

        # --- Бокова панель ---
        self.menu_frame = CTkFrame(self, width=30, height=self.winfo_height())
        self.menu_frame.pack_propagate(False)
        self.menu_frame.place(x=0, y=0)

        self.is_show_menu = False
        self.speed_animate_menu = -5

        self.btn = CTkButton(self, text='▶️', command=self.toggle_show_menu, width=30)
        self.btn.place(x=0, y=0)

        # --- Область чату ---
        self.chat_field = CTkScrollableFrame(self)
        self.chat_field.place(x=0, y=0)

        self.message_entry = CTkEntry(self, placeholder_text="Надіслати повідомлення", height=40)
        self.message_entry.place(x=0, y=0)

        self.send_button = CTkButton(self, text=">", width=50, height=40, command=self.send_message)
        self.send_button.place(x=0, y=0)

        self.img_button = CTkButton(self, text="📷", width=50, height=40, command=self.choose_image)
        self.img_button.place(x=60, y=0)

        self.addptive_ui()
        self.connect_to_server()

    # --- Адаптивний UI ---
    def addptive_ui(self):
        self.menu_frame.configure(height=self.winfo_height())
        self.chat_field.place(x=self.menu_frame.winfo_width())
        self.chat_field.configure(width=self.winfo_width() - self.menu_frame.winfo_width() - 20,
                                  height=self.winfo_height() - 40)

        self.send_button.place(x=self.winfo_width() - 50, y=self.winfo_height() - 40)
        self.img_button.place(x=self.winfo_width() - 100, y=self.winfo_height() - 40)

        self.message_entry.place(x=self.menu_frame.winfo_width(), y=self.send_button.winfo_y())
        self.message_entry.configure(
            width=self.winfo_width() - self.menu_frame.winfo_width() - self.send_button.winfo_width() - 60)

        self.after(50, self.addptive_ui)

    # --- Бокове меню ---
    def toggle_show_menu(self):
        if self.is_show_menu:
            self.is_show_menu = False
            self.speed_animate_menu *= -1
            self.btn.configure(text='▶️')
            self.show_menu()
        else:
            self.is_show_menu = True
            self.speed_animate_menu *= -1
            self.btn.configure(text='◀️')
            self.show_menu()

            self.label = CTkLabel(self.menu_frame, text='Імʼя')
            self.label.pack(pady=10)
            self.entry = CTkEntry(self.menu_frame)
            self.entry.pack(pady=5)
            self.save_btn = CTkButton(self.menu_frame, text="Зберегти Імя", command=self.save_name)
            self.save_btn.pack(pady=5)

            self.avatar_label = CTkLabel(self.menu_frame, text="Аватарка")
            self.avatar_label.pack(pady=10)
            self.avatar_btn = CTkButton(self.menu_frame, text="Оберіть аватарку", command=self.choose_avatar)
            self.avatar_btn.pack()

    def show_menu(self):
        self.menu_frame.configure(width=self.menu_frame.winfo_width() + self.speed_animate_menu)
        if not self.menu_frame.winfo_width() >= 200 and self.is_show_menu:
            self.after(10, self.show_menu)
        elif self.menu_frame.winfo_width() >= 40 and not self.is_show_menu:
            self.after(10, self.show_menu)
            if self.label and self.entry:
                self.label.destroy()
                self.entry.destroy()
                self.save_btn.destroy()
                self.avatar_label.destroy()
                self.avatar_btn.destroy()

    # --- Зміна імені ---
    def save_name(self):
        new_name = self.entry.get().strip()
        if new_name:
            self.username = new_name
            self.add_message("Ваш новий нік: " + self.username)

    # --- Вибір аватарки ---
    def choose_avatar(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.gif")]
        )
        if file_path:
            try:
                pil_img = Image.open(file_path)
                ctk_img = CTkImage(pil_img, size=(30, 30))  # Конвертуємо в CTkImage
                self.user_avatars[self.username] = ctk_img  # Зберігаємо для себе
                self.add_message("Ви обрали аватарку.")
                # Тепер можна відправити аватарку на сервер у base64, якщо хочеш
                with open(file_path, "rb") as f:
                    b64_data = base64.b64encode(f.read()).decode()
                data = f"AVATAR@{self.username}@{b64_data}\n"
                try:
                    self.sock.sendall(data.encode())
                except:
                    pass
            except Exception as e:
                self.add_message(f"Помилка завантаження аватарки: {e}")

    # --- Додавання повідомлення ---
    def add_message(self, text, img=None, author=None):
        if not author:
            author = self.username

        message_frame = CTkFrame(self.chat_field, fg_color='grey')
        message_frame.pack(pady=5, fill="x")

        wrapleng_size = self.winfo_width() - self.menu_frame.winfo_width() - 40
        time_str = datetime.now().strftime("%H:%M")
        text_with_time = f"[{time_str}] {text}"

        avatar_img = self.user_avatars.get(author)
        side = 'e' if author == self.username else 'w'

        if avatar_img:
            CTkLabel(message_frame, image=avatar_img, text=text_with_time,
                     compound="right" if side == 'e' else "left",
                     wraplength=wrapleng_size, text_color='white', anchor=side).pack(padx=5, pady=5, anchor=side)
        elif img:
            CTkLabel(message_frame, text=text_with_time,
                     wraplength=wrapleng_size, text_color='white',
                     image=img, compound='top', anchor=side).pack(padx=10, pady=5, anchor=side)
        else:
            CTkLabel(message_frame, text=text_with_time,
                     wraplength=wrapleng_size, text_color='white', anchor=side).pack(padx=5, pady=5, anchor=side)

    # --- Відправка тексту ---
    def send_message(self):
        message = self.message_entry.get().strip()
        if message and self.connected:
            data = f"TEXT@{self.username}@{message}\n"
            try:
                self.sock.sendall(data.encode())
            except:
                self.add_message("[Система] Помилка надсилання. Перепідключення...")
                self.reconnect()
        self.message_entry.delete(0, END)

    # --- Вибір фото ---
    def choose_image(self):
        file_name = filedialog.askopenfilename(
            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.gif")]
        )
        if file_name:
            self.open_image(file_name)

    # --- Відправка фото ---
    def open_image(self, file_name):
        if not self.connected:
            self.add_message("[Система] Відсутнє з'єднання. Спробуйте пізніше.")
            return
        try:
            with open(file_name, "rb") as f:
                raw = f.read()
                b64_data = base64.b64encode(raw).decode()
            short_name = os.path.basename(file_name)
            data = f"IMAGE@{self.username}@{short_name}@{b64_data}\n"
            self.sock.sendall(data.encode())
        except Exception as e:
            self.add_message(f"Не вдалося надіслати зображення: {e}")

    # --- Підключення ---
    def connect_to_server(self):
        try:
            self.sock = socket(AF_INET, SOCK_STREAM)
            self.sock.connect(self.server_address)
            self.connected = True
            self.user_avatars[self.username] = self.avatar_path
            hello = f"TEXT@{self.username}@[SYSTEM] {self.username} приєднався(лась) до чату!\n"
            self.sock.sendall(hello.encode())
            threading.Thread(target=self.recv_message, daemon=True).start()
        except:
            self.connected = False
            self.add_message("[Система] Не вдалося підключитися. Перепідключення...")
            threading.Thread(target=self.reconnect, daemon=True).start()

    # --- Автоматичне перепідключення ---
    def reconnect(self):
        while not self.connected:
            try:
                self.sock = socket(AF_INET, SOCK_STREAM)
                self.sock.connect(self.server_address)
                self.connected = True
                self.add_message("[Система] З'єднання відновлено!")
                hello = f"TEXT@{self.username}@[SYSTEM] {self.username} приєднався(лась) до чату!\n"
                self.sock.sendall(hello.encode())
                threading.Thread(target=self.recv_message, daemon=True).start()
                break
            except:
                self.add_message("[Система] Помилка підключення. Спробую через 5 сек...")
                time.sleep(5)

    # --- Отримання повідомлень ---
    def recv_message(self):
        buffer = ""
        while True:
            try:
                chunk = self.sock.recv(4096)
                if not chunk:
                    self.connected = False
                    self.add_message("[Система] Втрачене з'єднання. Перепідключення...")
                    threading.Thread(target=self.reconnect, daemon=True).start()
                    break
                buffer += chunk.decode('utf-8', errors='ignore')
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    self.handle_line(line.strip())
            except:
                self.connected = False
                self.add_message("[Система] Втрачене з'єднання. Перепідключення...")
                threading.Thread(target=self.reconnect, daemon=True).start()
                break

    # --- Обробка повідомлень ---
    def handle_line(self, line):
        if not line:
            return
        parts = line.split("@", 3)
        msg_type = parts[0]

        if msg_type == "TEXT" and len(parts) >= 3:
            author = parts[1]
            message = parts[2]
            self.add_message(f"{author}: {message}", author=author)

        elif msg_type == "IMAGE" and len(parts) >= 4:
            author = parts[1]
            filename = parts[2]
            b64_img = parts[3]
            try:
                img_data = base64.b64decode(b64_img)
                pil_img = Image.open(io.BytesIO(img_data))
                ctk_img = CTkImage(pil_img, size=(300, 300))
                self.add_message(f"{author} надіслав(ла) зображення: {filename}", img=ctk_img, author=author)
            except Exception as e:
                self.add_message(f"Помилка відображення зображення: {e}")

        elif msg_type == "AVATAR" and len(parts) >= 3:
            author = parts[1]
            b64_data = parts[2]
            self.set_user_avatar(author, b64_data)

    def choose_avatar(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.gif")]
        )
        if file_path:
            try:
                pil_img = Image.open(file_path)
                ctk_img = CTkImage(pil_img, size=(30, 30))  # Конвертуємо в CTkImage
                self.avatar_path = ctk_img  # Зберігаємо об'єкт CTkImage
                self.user_avatars[self.username] = ctk_img  # І для словника всіх користувачів
                self.add_message("Ви обрали аватарку.")
            except Exception as e:
                self.add_message(f"Помилка завантаження аватарки: {e}")

    def set_user_avatar(self, username, b64_data):
        try:
            img_data = base64.b64decode(b64_data)
            pil_img = Image.open(io.BytesIO(img_data))
            ctk_img = CTkImage(pil_img, size=(30, 30))
            self.user_avatars[username] = ctk_img
        except Exception as e:
            print(f"Помилка завантаження аватарки {username}: {e}")


win = MainWindow()
win.mainloop()
