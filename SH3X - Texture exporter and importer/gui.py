import os
import struct
import tkinter as tk
from tkinter import *
from tkinter import filedialog
from tkinter import messagebox
from PIL import Image, ImageTk
import image_processing
from image_processing import convert_bgra_to_rgba, convert_rgba_to_bgra, save_images, import_png
import ps2_mode
import pyglet.image.codecs.dds
from typing import List, Tuple
import texture_extraction  # Added import for texture_extraction

global file_path  # Define file_path as a global variable

def import_file(root):
    png_file_path = filedialog.askopenfilename()
    if png_file_path:
        bgra_file_path = os.path.splitext(png_file_path)[0] + ".bgra"
        import_png(png_file_path, bgra_file_path)
        messagebox.showinfo("Import Complete", "File imported successfully!")

def extract_textures(root):
    filename = filedialog.askopenfilename(parent=root, title='Select a .arc file')
    if filename:
        # import the module and extract the textures from the file
        import texture_extraction

        # extract textures from the .arc file
        textures = texture_extraction.extract_textures(filename)

        # create a new directory to store the extracted textures as .png images
        output_dir = os.path.splitext(filename)[0] + "_textures"
        os.makedirs(output_dir, exist_ok=True)

        # convert and save the textures as .png images
        texture_extraction.convert_textures_to_png(textures, output_dir)

        messagebox.showinfo("Extraction Complete", f"{len(textures)} textures extracted and saved as .png images to {output_dir}!")

def reimport_textures(root):
    filename = filedialog.askopenfilename(parent=root, title='Select a .arc file')
    if filename:
        png_dir = filedialog.askdirectory(parent=root, title='Select the directory containing the new PNG-encoded textures')
        if png_dir:
            import reimport
            reimport.import_textures(filename, png_dir)
            messagebox.showinfo("Import Complete", "Textures reimported successfully!")

def analyze_textures(root):
    filename = filedialog.askopenfilename(parent=root, title='Select a file')
    if filename:
        # analyze the textures from the file
        textures = ps2_mode.analyze_textures(filename)

        # display a message box with the analysis results
        num_textures = len(textures)
        messagebox.showinfo("Texture Analysis", f"{num_textures} textures analyzed!")
        
        # For each texture, visualize its palette
        for texture in textures:
            ps2_mode.visualize_palette(texture["palette_data"], mode="RGBA")

        # Display a message box with the results
        num_palettes = len(textures)
        messagebox.showinfo("Palette Visualization", f"{num_palettes} palettes visualized!")
        
        # create a new directory to store the extracted textures as unswizzled images
        output_dir = os.path.splitext(filename)[0] + "_textures"
        os.makedirs(output_dir, exist_ok=True)

        # convert and save the textures as .bmp
        ps2_mode.unswizzle_and_save(textures, output_dir)
        
        #convert greyscale to color
        ps2_mode.apply_palette_to_textures(textures, output_dir)

        messagebox.showinfo("Extraction Complete", f"{len(textures)} textures extracted and saved as unswizzled and colorized data to {output_dir}!")
        
def display_texture(textures, index):
    texture = textures[index]
    img = texture_extraction.convert_texture_to_image(texture)
    window = tk.Toplevel()

    # Create a frame for image display
    image_frame = tk.Frame(window)
    image_frame.pack(fill=tk.BOTH, expand=True)

    img_tk = ImageTk.PhotoImage(img)
    label = tk.Label(image_frame, image=img_tk)
    label.img = img_tk  # Keep a reference to the image to prevent garbage collection
    label.pack(fill=tk.BOTH, expand=True)

    # Display texture name and size
    texture_info = tk.Label(window, text=f"Name: {texture['filename']}, Size: {texture['width']}x{texture['height']}")
    texture_info.pack()

    # Create a frame for buttons
    button_frame = tk.Frame(window)
    button_frame.pack(side=tk.BOTTOM, fill=tk.X)

    def show_next_texture():
        nonlocal index
        index = (index + 1) % len(textures)  # Cycle through textures
        next_texture = textures[index]
        next_img = texture_extraction.convert_texture_to_image(next_texture)
        next_img_tk = ImageTk.PhotoImage(next_img)
        label.config(image=next_img_tk)
        label.img = next_img_tk  # Update the reference to prevent garbage collection
        # Update texture info
        texture_info.config(text=f"Name: {next_texture['filename']}, Size: {next_texture['width']}x{next_texture['height']}")

    def export_texture(format):
        filename = filedialog.asksaveasfilename(defaultextension=f".{format.lower()}", filetypes=[(f"{format} files", f"*.{format.lower()}")])
        if filename:
            texture = textures[index]
            img = texture_extraction.convert_texture_to_image(texture)
            img.save(filename, format=format)
            messagebox.showinfo("Export Complete", f"Texture exported successfully as {format}!")

    def import_texture():
        filename = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.bmp")])
        if filename:
            new_img = Image.open(filename)
            new_rgba_data = new_img.tobytes()
            new_bgra_data = image_processing.convert_rgba_to_bgra(new_rgba_data)
            textures[index]['data'] = new_bgra_data
            # Optionally, refresh the displayed image
            img_tk = ImageTk.PhotoImage(new_img)
            label.config(image=img_tk)
            label.img = img_tk
            messagebox.showinfo("Import Complete", "Texture imported successfully!")

    next_button = tk.Button(button_frame, text="Next", command=show_next_texture)
    next_button.pack(side=tk.LEFT)

    export_png_button = tk.Button(button_frame, text="Export as PNG", command=lambda: export_texture('PNG'))
    export_png_button.pack(side=tk.LEFT)

    export_bmp_button = tk.Button(button_frame, text="Export as BMP", command=lambda: export_texture('BMP'))
    export_bmp_button.pack(side=tk.LEFT)

    import_button = tk.Button(button_frame, text="Import", command=import_texture)
    import_button.pack(side=tk.LEFT)

    window.mainloop()


def view_texture(root):
    filename = filedialog.askopenfilename(parent=root, title='Select a .arc file')
    if filename:
        textures = texture_extraction.extract_textures(filename)
        display_texture(textures, 0)  # Initially display the first texture

def main():
    global file_path  # Use the global file_path variable
    root = Tk()
    root.title("Silent Hill 3 Texture Extractor and Importer")
    root.geometry("640x200")
    file_path = ""

    import_button = Button(root, text="Convert to .bgra", command=lambda: import_file(root))
    import_button.pack(side=LEFT, padx=10, pady=10)

    extract_button = Button(root, text="Batch Extract Textures", command=lambda: extract_textures(root))
    extract_button.pack(side=LEFT, padx=10, pady=10)
    
    # add the reimport button
    reimport_button = Button(root, text="Batch Reimport Textures", command=lambda: reimport_textures(root))
    reimport_button.pack(side=LEFT, padx=10, pady=10)

    # add the ps2_mode button
    analyze_button = Button(root, text="PS2_Mode", command=lambda: analyze_textures(root))
    analyze_button.pack(side=LEFT, padx=10, pady=10)

    # add the view texture button
    view_button = Button(root, text="Texture Viewer", command=lambda: view_texture(root))
    view_button.pack(side=LEFT, padx=10, pady=10)

    root.mainloop()

if __name__ == "__main__":
    main()