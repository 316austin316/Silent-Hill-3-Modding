import os
import struct
import tkinter as tk
from tkinter import *
from tkinter import filedialog
from tkinter import messagebox
from PIL import Image
import image_processing
from image_processing import convert_bgra_to_rgba, convert_rgba_to_bgra, save_images, import_png
import texture_analysis
import pyglet.image.codecs.dds

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
        textures = texture_analysis.analyze_textures(filename)

        # display a message box with the analysis results
        num_textures = len(textures)
        messagebox.showinfo("Texture Analysis", f"{num_textures} textures analyzed!")
        
        # create a new directory to store the extracted textures as unswizzled images
        output_dir = os.path.splitext(filename)[0] + "_textures"
        os.makedirs(output_dir, exist_ok=True)

        # convert and save the textures as .png images
        texture_analysis.unswizzle_and_save(textures, output_dir)

        messagebox.showinfo("Extraction Complete", f"{len(textures)} textures extracted and saved as unswizzled data to {output_dir}!")

def main():
    global file_path  # Use the global file_path variable
    root = Tk()
    root.title("Silent Hill 3 Texture Extractor and Importer")
    root.geometry("400x200")
    file_path = ""

    import_button = Button(root, text="Import", command=lambda: import_file(root))
    import_button.pack(side=LEFT, padx=10, pady=10)

    extract_button = Button(root, text="Extract Textures", command=lambda: extract_textures(root))
    extract_button.pack(side=LEFT, padx=10, pady=10)
    
    # add the reimport button
    reimport_button = Button(root, text="Reimport Textures", command=lambda: reimport_textures(root))
    reimport_button.pack(side=LEFT, padx=10, pady=10)

    # add the analyze button
    analyze_button = Button(root, text="Analyze Textures", command=lambda: analyze_textures(root))
    analyze_button.pack(side=LEFT, padx=10, pady=10)

    root.mainloop()

if __name__ == "__main__":
    main()
