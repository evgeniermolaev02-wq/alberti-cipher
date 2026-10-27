import os
import random
import math

ALPHABET = "АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"

def get_internal_ring(secret_seed):
    """Создает внутренний диск, завязанный на секретный ключ"""
    char_list = list(ALPHABET)
    # Используем seed для генерации уникальной формы диска
    random.Random(secret_seed).shuffle(char_list)
    return "".join(char_list)

def get_rotated_internal(shift, secret_seed):
    base = get_internal_ring(secret_seed)
    return base[shift:] + base[:shift]

def draw_perfect_circle(shift, secret_seed):
    int_r = get_rotated_internal(shift, secret_seed)
    
    width = 55
    height = 23
    center_x = width // 2
    center_y = height // 2
    
    r_ext_x = 22
    r_ext_y = 10
    r_int_x = 14
    r_int_y = 6
    
    screen = [[" " for _ in range(width)] for _ in range(height)]
    
    def place_ring(alphabet_str, rx, ry):
        for i, char in enumerate(alphabet_str):
            angle = (i * 2 * math.pi / 32) - math.pi / 2
            x = int(center_x + rx * math.cos(angle))
            y = int(center_y + ry * math.sin(angle))
            if 0 <= x < width and 0 <= y < height:
                screen[y][x] = char

    place_ring(ALPHABET, r_ext_x, r_ext_y)
    place_ring(int_r, r_int_x, r_int_y)
    
    info_str = f"СДВИГ:{shift:02d}"
    for i, char in enumerate(info_str):
        screen[center_y][center_x - len(info_str)//2 + i] = char

    print("\033[H\033[J")
    print("=== ДИСК АЛЬБЕРТИ СО СЛУЧАЙНЫМИ ПРЫЖКАМИ ===")
    print("Правила:")
    print("  • После каждой буквы диск прыгает на СЛУЧАЙНЫЙ сдвиг.")
    print("  • Знаки '+' и '-' корректируют текущий случайный сдвиг.")
    print("  • Наберите 'exit' для выхода.\n")
    
    for row in screen:
        print("".join(row))
    print("===========================================================")

def main():
    print("=== НАСТРОЙКА ШИФРАТОРА ===")
    try:
        secret_seed = int(input("Введите цифровой КЛЮЧ для синхронизации дисков (например, 777): "))
    except ValueError:
        print("Нужно ввести целое число! Установлен ключ по умолчанию: 42")
        secret_seed = 42
        
    # Инициализируем отдельный генератор случайных чисел для прыжков диска
    rng = random.Random(secret_seed)
    
    # Стартовый сдвиг тоже выбирается случайно на основе ключа
    shift = rng.randint(0, len(ALPHABET) - 1)
    max_shift = len(ALPHABET) - 1
    
    input_history = ""
    output_history = ""
    
    while True:
        draw_perfect_circle(shift, secret_seed)
        
        if input_history:
            print(f"Обработанный текст: {input_history}")
            print(f"Результат шифра:    {output_history}\n")
            
        user_input = input("Ввод (строка текста): ").upper().strip()
        
        if user_input == "EXIT":
            print("Выход.")
            break
        if user_input == "":
            continue
            
        for char in user_input:
            if char == "+":
                shift = 0 if shift == max_shift else shift + 1
            elif char == "-":
                shift = max_shift if shift == 0 else shift - 1
            elif char in ALPHABET:
                int_r = get_rotated_internal(shift, secret_seed)
                idx = ALPHABET.index(char)
                cipher_char = int_r[idx]
                
                input_history += char
                output_history += cipher_char
                
                # МОДИФИКАЦИЯ: Прыгаем на следующий случайный сдвиг!
                # Поскольку генератор rng завязан на secret_seed, 
                # последовательность прыжков будет строго одинаковой при одинаковом ключе.
                shift = rng.randint(0, max_shift)
            elif char == " ":
                input_history += " "
                output_history += " "

if __name__ == "__main__":
    main()
