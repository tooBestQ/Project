from customtkinter import *
import base64
import io
import threading
import time
import os
import socket  # <-- виправлено
from tkinter import filedialog, messagebox
from PIL import Image
from datetime import datetime

# Optional audio support
try:
    import sounddevice as sd
    import wavio
    AUDIO_AVAILABLE = True
except Exception:
    AUDIO_AVAILABLE = False


class MainWindow(CTk):
    def __init__(self):
        super().__init__()
        self.geometry("800x600")
        self.title("ChatPro")
        self.update_idletasks()  # для правильного отримання розмірів

        # --- UI state ---
        self.is_show_menu = False
        self.menu_width = 40
        self.menu_target_width = 300
        self.menu_animation_speed = 10
        self.animating = False
        self._after_ui_id = None
        self._anim_after_id = None

        # --- Networking ---
        self.sock = None
        self.keep_receiving = False

        # --- User ---
        self.username = "test"
        self.avatar_path = None
        self.avatar_ctk = None
        self.avatars_by_user = {}
        self._img_refs = []

        # --- Bubble colors ---
        self.my_color = "#2b6aff"

        # --- menu widget list ---
        self.menu_widgets = []
        self.menu_widgets_created = False

        # --- UI ---
        self.menu_frame = CTkFrame(self, width=self.menu_width, height=self.winfo_height())
        self.menu_frame.pack_propagate(False)
        self.menu_frame.place(x=0, y=0)

        self.btn = CTkButton(self, text='▶️', width=30, command=self.toggle_show_menu)
        self.btn.place(x=0, y=0)

        self.chat_field = CTkScrollableFrame(self)
        self.chat_field.place(x=self.menu_width, y=0)
        self.chat_field.configure(width=self.winfo_width() - self.menu_width - 20,
                                  height=self.winfo_height() - 60)

        self.message_entry = CTkEntry(self, placeholder_text="Надіслати повідомлення", width=400, height=40)
        self.message_entry.place(x=self.menu_width + 10, y=self.winfo_height() - 50)

        self.send_button = CTkButton(self, text=">", width=50, height=40, command=self.send_message)
        self.send_button.place(x=self.winfo_width() - 60, y=self.winfo_height() - 50)

        self.image_button = CTkButton(self, text="📷", width=50, height=40, command=self.send_image)
        self.image_button.place(x=self.winfo_width() - 120, y=self.winfo_height() - 50)

        # Layout updater
        self.after(50, self.addptive_ui)

        # Connect
        self.connect_to_server()

        # Close protocol
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ----------------- UI Layout -----------------
    def addptive_ui(self):
        if not self.winfo_exists():
            return
        w = self.winfo_width()
        h = self.winfo_height()
        if self.menu_frame.winfo_exists():
            self.menu_frame.configure(height=h)
        if self.chat_field.winfo_exists():
            self.chat_field.place(x=self.menu_frame.winfo_width(), y=0)
            self.chat_field.configure(width=w - self.menu_frame.winfo_width() - 20,
                                      height=h - 60)
        self.send_button.place(x=w - 60, y=h - 50)
        self.image_button.place(x=w - 120, y=h - 50)
        self.message_entry.place(x=self.menu_frame.winfo_width() + 10, y=h - 50)

        self._after_ui_id = self.after(50, self.addptive_ui)

    def toggle_show_menu(self):
        if self.animating:
            return
        self.is_show_menu = not self.is_show_menu
        self.animating = True
        if self.is_show_menu and not self.menu_widgets_created:
            self.create_menu_widgets()
            self.menu_widgets_created = True
        self.animate_menu()

    def animate_menu(self):
        if not self.winfo_exists() or not self.menu_frame.winfo_exists():
            self.animating = False
            return

        current_w = self.menu_frame.winfo_width()
        target = self.menu_target_width if self.is_show_menu else 40
        step = self.menu_animation_speed if self.is_show_menu else -self.menu_animation_speed

        new_w = current_w + step
        if (step > 0 and new_w > target) or (step < 0 and new_w < target):
            new_w = target

        self.menu_frame.configure(width=new_w)

        if new_w != target:
            self._anim_after_id = self.after(10, self.animate_menu)
        else:
            self.animating = False
            if not self.is_show_menu:
                self.destroy_menu_widgets()

    def create_menu_widgets(self):
        self.destroy_menu_widgets()

        lbl = CTkLabel(self.menu_frame, text='Імʼя')
        lbl.pack(pady=(18, 4), padx=8, anchor='w')
        self.menu_widgets.append(lbl)

        entry = CTkEntry(self.menu_frame)
        entry.insert(0, self.username)
        entry.pack(pady=4, padx=8, fill='x')
        self.menu_widgets.append(entry)
        self.entry = entry

        save_btn = CTkButton(self.menu_frame, text="Зберегти Імя", command=self.save_name)
        save_btn.pack(pady=4, padx=8, fill='x')
        self.menu_widgets.append(save_btn)

        avatar_btn = CTkButton(self.menu_frame, text="Змінити аватарку", command=self.change_avatar)
        avatar_btn.pack(pady=4, padx=8, fill='x')
        self.menu_widgets.append(avatar_btn)

        if AUDIO_AVAILABLE:
            voice_btn = CTkButton(self.menu_frame, text="Записати голос (3с)", command=self.record_voice_short)
        else:
            voice_btn = CTkButton(self.menu_frame, text="Голос недоступний", state="disabled")
        voice_btn.pack(pady=4, padx=8, fill='x')
        self.menu_widgets.append(voice_btn)

    def destroy_menu_widgets(self):
        for w in list(self.menu_widgets):
            try:
                if w.winfo_exists():
                    w.destroy()
            except Exception:
                pass
        self.menu_widgets = []
        self.menu_widgets_created = False

    # ----------------- Messages -----------------
    def add_message(self, text, img=None, author=None, timestamp=None, system=False, avatar_ctk=None):
        if timestamp is None:
            timestamp = datetime.now()
        time_str = timestamp.strftime("%H:%M")
        fg_color = self.my_color if author == self.username else "#2b2b2b"
        anchor_side = 'e' if author == self.username else 'w'

        frame = CTkFrame(self.chat_field, fg_color=fg_color, corner_radius=8)
        frame.pack(pady=3, padx=6, anchor=anchor_side, fill='x')
        frame.author = author

        if system:
            CTkLabel(frame, text=f"[{time_str}] {text}", wraplength=self.winfo_width() - 200,
                     justify='center').pack(pady=4)
            return

        # Header з аватаркою і ім'ям
        header_frame = CTkFrame(frame, fg_color="transparent")
        header_frame.pack(anchor='w', padx=4, pady=(2, 0))

        avatar = avatar_ctk or self.avatars_by_user.get(author)
        if avatar:
            avatar_lbl = CTkLabel(header_frame, image=avatar, text="")  # <-- text=""
            avatar_lbl.pack(side='left', padx=(0, 4))
            self._img_refs.append(avatar)

        CTkLabel(header_frame, text=f"{author or 'Unknown'} • {time_str}", anchor='w', font=("Arial", 9, "bold")).pack(
            side='left')

        if img:
            label = CTkLabel(frame, image=img, text="", wraplength=self.winfo_width() - 220,
                             anchor='w', justify='left')
            label.pack(anchor='w', padx=4, pady=(1, 4))
            self._img_refs.append(img)  # обов'язково зберігаємо посилання

        else:
            CTkLabel(frame, text=text, wraplength=self.winfo_width() - 220, anchor='w', justify='left',
                     font=("Arial", 10)).pack(anchor='w', padx=4, pady=(1, 4))

    # ----------------- Networking -----------------
    def connect_to_server(self):
        threading.Thread(target=self._connect_thread, daemon=True).start()

    def _connect_thread(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect(("localhost", 2525))
            self.keep_receiving = True
            threading.Thread(target=self.recv_message, daemon=True).start()
            self.add_message("[Система] З'єднання встановлено.", system=True)
        except Exception as e:
            self.add_message(f"[Система] Не вдалося підключитися: {e}", system=True)

    def recv_message(self):
        buffer = ""
        while self.sock and self.keep_receiving:
            try:
                chunk = self.sock.recv(8192)
                if not chunk:
                    break
                buffer += chunk.decode('utf-8', errors='ignore')
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    self.handle_line(line.strip())
            except Exception as e:
                self.add_message(f"[Система] Втрачено зв'язок: {e}", system=True)
                break

    def handle_line(self, line):
        if not line:
            return
        parts = line.split("@", 3)
        msg_type = parts[0]

        if msg_type == "TEXT" and len(parts) >= 3:
            autor, message = parts[1], parts[2]
            if autor != self.username:  # <-- Додано
                self.add_message(message, author=autor, avatar_ctk=self.avatars_by_user.get(autor))

        elif msg_type == "IMAGE" and len(parts) >= 4:
            autor, fname, b64img = parts[1], parts[2], parts[3]
            if autor == self.username:  # <-- пропускаємо свої власні зображення
                return
            try:
                raw = base64.b64decode(b64img)
                pil_img = Image.open(io.BytesIO(raw))
                pil_img.thumbnail((250, 250))
                ctk_img = CTkImage(pil_img, size=pil_img.size)
                self.add_message(f"{autor} надіслав(ла) фото {fname}", img=ctk_img, author=autor,
                                 avatar_ctk=self.avatars_by_user.get(autor))
            except Exception:
                self.add_message(f"[Система] Не вдалося завантажити зображення від {autor}", system=True)

        elif msg_type == "AVATAR" and len(parts) >= 4:
            user, fname, b64img = parts[1], parts[2], parts[3]
            try:
                raw = base64.b64decode(b64img)
                pil = Image.open(io.BytesIO(raw))
                pil.thumbnail((40, 40))
                ctk = CTkImage(pil, size=pil.size)
                self.avatars_by_user[user] = ctk
                self._img_refs.append(ctk)
            except Exception:
                pass

    # ----------------- Sending -----------------
    def send_message(self):
        msg = self.message_entry.get().strip()
        if not msg:
            return
        self.add_message(msg, author=self.username, avatar_ctk=self.avatar_ctk)
        data = f"TEXT@{self.username}@{msg}\n"
        try:
            if self.sock:
                self.sock.send(data.encode('utf-8'))
        except Exception:
            self.add_message("[Система] Не вдалося надіслати повідомлення.", system=True)
        self.message_entry.delete(0, 'end')

    def send_image(self):
        file_name = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.gif")])
        if not file_name:
            return
        try:
            with open(file_name, "rb") as f:
                raw = f.read()
                b64_data = base64.b64encode(raw).decode()
            short_name = os.path.basename(file_name)
            data = f"IMAGE@{self.username}@{short_name}@{b64_data}\n"
            if self.sock:
                self.sock.sendall(data.encode())
            pil_img = Image.open(file_name)
            pil_img.thumbnail((250, 250))
            ctk_img = CTkImage(pil_img, size=pil_img.size)
            self.add_message(f"{self.username} надіслав(ла) фото {short_name}", img=ctk_img, author=self.username,
                             avatar_ctk=self.avatar_ctk)
        except Exception:
            self.add_message(f"[Система] Не вдалося надіслати зображення", system=True)

    # ----------------- Avatar -----------------
    def change_avatar(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.gif")])
        if not path:
            return
        try:
            pil = Image.open(path)
            pil.thumbnail((40, 40))
            ctk = CTkImage(pil, size=pil.size)
            self.avatar_path = path
            self.avatar_ctk = ctk
            self._img_refs.append(ctk)
            self.add_message("[Система] Аватарку змінено ✅", system=True)
        except Exception:
            self.add_message("[Система] Не вдалося змінити аватарку", system=True)

    # ----------------- Audio -----------------
    def record_voice_short(self):
        if not AUDIO_AVAILABLE:
            messagebox.showinfo("Голосові", "Модулі sounddevice/wavio не встановлені.")
            return
        duration = 3
        samplerate = 44100
        tmpfile = f"voice_{int(time.time())}.wav"
        self.add_message("[Система] Запис голосу (3с)...", system=True)
        try:
            rec = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1)
            sd.wait()
            wavio.write(tmpfile, rec, samplerate, sampwidth=2)
        except Exception:
            self.add_message("[Система] Не вдалося записати голос", system=True)

    # ----------------- Save Name -----------------
    def save_name(self):
        new_name = getattr(self, "entry", None)
        if new_name:
            new_name = self.entry.get().strip()
            if new_name:
                self.username = new_name
                self.add_message(f"[Система] Ваш новий нік: {self.username}", system=True)

    # ----------------- Close -----------------
    def on_close(self):
        try:
            if self._after_ui_id:
                self.after_cancel(self._after_ui_id)
                self._after_ui_id = None
        except Exception:
            pass
        try:
            if self._anim_after_id:
                self.after_cancel(self._anim_after_id)
                self._anim_after_id = None
        except Exception:
            pass
        try:
            self.keep_receiving = False
            if self.sock:
                try:
                    self.sock.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                try:
                    self.sock.close()
                except Exception:
                    pass
                self.sock = None
        except Exception:
            pass
        try:
            self.destroy_menu_widgets()
        except Exception:
            pass
        try:
            for w in list(self.chat_field.winfo_children()):
                try:
                    w.destroy()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            self.send_button.place_forget()
            self.image_button.place_forget()
            self.message_entry.place_forget()
            self.btn.place_forget()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            try:
                self.quit()
            except Exception:
                pass


if __name__ == "__main__":
    win = MainWindow()
    win.mainloop()
