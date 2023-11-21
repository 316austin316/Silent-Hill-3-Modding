import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox

def swizzle_32_to_8(p_in_texels, width, height):
    p_swiz_texels = bytearray(width * height)

    for y in range(height):
        for x in range(width):
            block_location = (y & ~0xf) * width + (x & ~0xf) * 2
            swap_selector = (((y + 2) >> 2) & 0x1) * 4
            pos_y = (((y & ~3) >> 1) + (y & 1)) & 0x7
            column_location = pos_y * width * 2 + ((x + swap_selector) & 0x7) * 4

            byte_num = ((y >> 1) & 1) + ((x >> 2) & 2)  # 0, 1, 2, 3

            p_swiz_texels[block_location + column_location + byte_num] = p_in_texels[y * width + x]

    return bytes(p_swiz_texels)

def open_file():
    file_path = filedialog.askopenfilename()
    if file_path:
        file_entry.delete(0, tk.END)
        file_entry.insert(0, file_path)

def save_file(data):
    file_path = filedialog.asksaveasfilename(defaultextension=".bin")
    if file_path:
        with open(file_path, "wb") as f:
            f.write(data)

def run_swizzle():
    try:
        width = int(width_entry.get())
        height = int(height_entry.get())
        file_path = file_entry.get()

        with open(file_path, "rb") as f:
            texels = f.read()

        if len(texels) != width * height:
            messagebox.showerror("Error", "The number of texels does not match the specified width and height.")
            return

        swizzled_texels = swizzle_32_to_8(texels, width, height)
        save_file(swizzled_texels)
        messagebox.showinfo("Success", "The swizzled data has been saved successfully.")
    except ValueError:
        messagebox.showerror("Error", "Invalid input. Please ensure width and height are properly formatted.")
    except FileNotFoundError:
        messagebox.showerror("Error", "File not found. Please ensure the file path is correct.")

root = tk.Tk()
root.title("Reswizzle Tool")

width_label = tk.Label(root, text="Width:")
width_label.grid(row=0, column=0)

width_entry = tk.Entry(root)
width_entry.grid(row=0, column=1)

height_label = tk.Label(root, text="Height:")
height_label.grid(row=1, column=0)

height_entry = tk.Entry(root)
height_entry.grid(row=1, column=1)

file_label = tk.Label(root, text="Select File:")
file_label.grid(row=2, column=0)

file_entry = tk.Entry(root)
file_entry.grid(row=2, column=1, sticky="ew")

browse_button = tk.Button(root, text="Browse", command=open_file)
browse_button.grid(row=2, column=2)

run_button = tk.Button(root, text="Run Swizzle", command=run_swizzle)
run_button.grid(row=3, column=0, columnspan=3)

root.mainloop()