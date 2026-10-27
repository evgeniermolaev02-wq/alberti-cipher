import os
import random
import math
import socket
import threading
import curses

ALPHABET = "АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ "

DH_P = 2147483647  
DH_G = 16807

class AlbertiNetworkCrypto:
    def __init__(self):
        self.shift = 0
        self.secret_seed = 42
        self.sock = None
        self.conn = None
        self.my_secret_dh = random.randint(1000, 9999)
        self.history = []
        self.running = True
        self.stdscr = None
        self.input_buffer = ""
        self.auto_shift_enabled = True  # Синхронный статус автосдвига
        self.rng_tx = None  
        self.rng_rx = None  

    def init_crypto(self, final_shared_key):
        self.secret_seed = final_shared_key
        self.rng_tx = random.Random(self.secret_seed)
        self.rng_rx = random.Random(self.secret_seed)
        self.shift = self.rng_tx.randint(0, len(ALPHABET) - 1)
        self.rng_rx.randint(0, len(ALPHABET) - 1)

    def get_rotated_internal(self):
        char_list = list(ALPHABET)
        random.Random(self.secret_seed).shuffle(char_list)
        base = "".join(char_list)
        return base[self.shift:] + base[:self.shift]

    def draw_disk(self):
        if not self.stdscr: return
        self.stdscr.clear()
        
        int_r = self.get_rotated_internal()
        width, height = 55, 23
        center_x, center_y = width // 2, height // 2
        r_ext_x, r_ext_y = 22, 10
        r_int_x, r_int_y = 14, 6
        
        screen = [[" " for _ in range(width)] for _ in range(height)]
        
        for i, char in enumerate(ALPHABET):
            angle = (i * 2 * math.pi / 32) - math.pi / 2
            x = int(center_x + r_ext_x * math.cos(angle))
            y = int(center_y + r_ext_y * math.sin(angle))
            if 0 <= x < width and 0 <= y < height: screen[y][x] = char
            
        for i, char in enumerate(int_r):
            angle = (i * 2 * math.pi / 32) - math.pi / 2
            x = int(center_x + r_int_x * math.cos(angle))
            y = int(center_y + r_int_y * math.sin(angle))
            if 0 <= x < width and 0 <= y < height: screen[y][x] = char
            
        info_str = f"СДВИГ:{self.shift:02d}"
        for i, char in enumerate(info_str):
            screen[center_y][center_x - len(info_str)//2 + i] = char

        status_auto = "ВКЛ (Прыжки)" if self.auto_shift_enabled else "ВЫКЛ (Заморожен)"

        self.stdscr.addstr(0, 0, "=== СЕТЕВОЙ ЧАТ АЛЬБЕРТИ + ДИФФИ-ХЕЛЛМАН ===", curses.A_BOLD)
        self.stdscr.addstr(1, 0, f"Управление: [F1] Лево | [F2] Право | [F3] Автосдвиг: {status_auto} | [Enter] Отправить")
        
        for idx, row in enumerate(screen):
            self.stdscr.addstr(3 + idx, 0, "".join(row))
            
        start_y = 27
        self.stdscr.addstr(start_y, 0, " Последние сообщения в канале:")
        for i, msg in enumerate(self.history[-5:]):
            self.stdscr.addstr(start_y + 1 + i, 2, msg)
            
        self.stdscr.addstr(start_y + 7, 0, f"Ввод: {self.input_buffer}")
        self.stdscr.refresh()

    def send_toggle_auto(self):
        """Отправляет команду переключения режима автосдвига собеседнику"""
        try:
            self.conn.sendall(b"_TOGGLE_AUTO_")
            self.auto_shift_enabled = not self.auto_shift_enabled
            self.draw_disk()
        except Exception:
            self.history.append("!! Не удалось отправить команду управления.")

    def send_message(self, text):
        cipher_chars = []
        start_shift = self.shift
        
        for char in text.upper():
            if char in ALPHABET:
                int_r = self.get_rotated_internal()
                idx = ALPHABET.index(char)
                cipher_chars.append(int_r[idx])
                
                # Делаем случайный прыжок только если режим ВКЛ
                if self.auto_shift_enabled:
                    self.shift = self.rng_tx.randint(0, len(ALPHABET) - 1)
            else:
                cipher_chars.append(char)
                
        cipher_text = "".join(cipher_chars)
        try:
            self.conn.sendall(cipher_text.encode('utf-8'))
            self.history.append(f"Вы: {text.upper()} (Шифр: {cipher_text} Сдвиг: {start_shift:02d} -> {self.shift:02d})")
        except Exception:
            self.history.append("!! Ошибка отправки.")

    def receive_loop(self):
        while self.running:
            try:
                data = self.conn.recv(1024)
                if not data: break
                
                # Проверяем, не служебная ли это команда переключения F3
                if data == b"_TOGGLE_AUTO_":
                    self.auto_shift_enabled = not self.auto_shift_enabled
                    self.draw_disk()
                    continue
                    
                cipher_text = data.decode('utf-8')
                start_shift = self.shift
                
                orig_chars = []
                for cipher_char in cipher_text:
                    if cipher_char in ALPHABET:
                        int_r = self.get_rotated_internal()
                        if cipher_char in int_r:
                            idx = int_r.index(cipher_char)
                            orig_chars.append(ALPHABET[idx])
                            
                            # Делаем синхронный случайный прыжок на приемнике
                            if self.auto_shift_enabled:
                                self.shift = self.rng_rx.randint(0, len(ALPHABET) - 1)
                        else:
                            orig_chars.append(cipher_char)
                    else:
                        orig_chars.append(cipher_char)
                        
                orig_text = "".join(orig_chars)
                self.history.append(f"Соб-к: {orig_text} (Шифр: {cipher_text} Сдвиг: {start_shift:02d} -> {self.shift:02d})")
                self.draw_disk()
            except Exception:
                break
        self.history.append("!! Отключено.")
        self.draw_disk()

    def start_server(self, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('0.0.0.0', port))
        self.sock.listen(1)
        self.conn, addr = self.sock.accept()
        self.handle_dh_exchange(is_server=True)

    def start_client(self, host, port):
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.connect((host, port))
        self.handle_dh_exchange(is_server=False)

    def handle_dh_exchange(self, is_server):
        my_public_dh = pow(DH_G, self.my_secret_dh, DH_P)
        if is_server:
            peer_public_dh = int(self.conn.recv(1024).decode('utf-8'))
            self.conn.sendall(str(my_public_dh).encode('utf-8'))
        else:
            self.conn.sendall(str(my_public_dh).encode('utf-8'))
            peer_public_dh = int(self.conn.recv(1024).decode('utf-8'))
        shared_secret = pow(peer_public_dh, self.my_secret_dh, DH_P)
        self.init_crypto(shared_secret)
        threading.Thread(target=self.receive_loop, daemon=True).start()

def curses_main(stdscr, app, mode, host, port):
    app.stdscr = stdscr
    curses.curs_set(1)
    stdscr.keypad(True)
    
    stdscr.clear()
    stdscr.addstr(0, 0, "[*] Установка связи и обмен Диффи-Хеллмана...")
    stdscr.refresh()
    
    try:
        if mode == "1":
            app.start_server(port)
        else:
            app.start_client(host, port)
    except Exception as e:
        stdscr.clear()
        stdscr.addstr(0, 0, f"Ошибка сети: {e}. Нажмите любую клавишу...")
        stdscr.getch()
        return

    max_shift = len(ALPHABET) - 1

    while True:
        app.draw_disk()
        try:
            key = stdscr.get_wch()
        except curses.error:
            continue

        if key == curses.KEY_F1:
            app.shift = max_shift if app.shift == 0 else app.shift - 1
        elif key == curses.KEY_F2:
            app.shift = 0 if app.shift == max_shift else app.shift + 1
        elif key == curses.KEY_F3:
            # Отправляем сетевую команду переключения режима
            app.send_toggle_auto()
        elif key in ('\n', '\r'):
            if app.input_buffer.upper() == "EXIT":
                break
            if app.input_buffer:
                app.send_message(app.input_buffer)
                app.input_buffer = ""
        elif key in (curses.KEY_BACKSPACE, '\x7f', '\b'):
            app.input_buffer = app.input_buffer[:-1]
        else:
            if isinstance(key, str):
                char = key.upper()
                if char in ALPHABET:
                    app.input_buffer += char

def main():
    app = AlbertiNetworkCrypto()
    print("=== ЗАПУСК СЕТЕВОГО ШИФРАТОРА ===")
    mode = input("Режим (1 - Сервер, 2 - Клиент): ").strip()
    port = 5555
    host = "127.0.0.1"
    
    if mode == "1":
        p_input = input("Порт (Enter для 5555): ").strip()
        if p_input: port = int(p_input)
    elif mode == "2":
        host = input("IP сервера: ").strip()
        p_input = input("Порт (Enter для 5555): ").strip()
        if p_input: port = int(p_input)
        
    curses.wrapper(curses_main, app, mode, host, port)

if __name__ == "__main__":
    main()
