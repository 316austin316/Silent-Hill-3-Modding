import struct
import os
from PIL import Image

def convert_bgra_to_rgba(bgra_data):
    # Convert BGRA to RGBA
    rgba_data = b""
    for i in range(0, len(bgra_data), 4):
        b = bgra_data[i]
        g = bgra_data[i + 1]
        r = bgra_data[i + 2]
        a = bgra_data[i + 3]
        rgba_data += struct.pack("<4B", r, g, b, a)
    return rgba_data


def convert_rgba_to_bgra(rgba_data):
    # Convert RGBA to BGRA
    bgra_data = b""
    for i in range(0, len(rgba_data), 4):
        r = rgba_data[i]
        g = rgba_data[i + 1]
        b = rgba_data[i + 2]
        a = rgba_data[i + 3]
        bgra_data += struct.pack("<4B", b, g, r, a)
    return bgra_data

def save_images(file_path, data, width, height):
    # Create a new directory to store extracted data
    output_dir = os.path.splitext(file_path)[0] + "_data"
    os.makedirs(output_dir, exist_ok=True)

    # Extract and save images of different sizes
    for size in [(256, 256), (512, 512), (512, 1024)]:
        w, h = size
        img_size = w * h * 4  # 4 bytes per pixel (RGBA)

        # Convert extracted data to RGBA
        rgba_data = convert_bgra_to_rgba(data)

        # Convert RGBA data to PNG image
        img = Image.frombytes("RGBA", (width, height), rgba_data)
        img_path = os.path.join(output_dir, f"extracted_data_{w}x{h}.png")
        img.save(img_path)

        # Resize the image and save
        img_resized = img.resize(size)
        img_path_resized = os.path.join(output_dir, f"extracted_data_{w}x{h}_resized.png")
        img_resized.save(img_path_resized)

        print(f"Image saved to: {img_path_resized}")

    # Convert extracted data to RGBA
    rgba_data = convert_bgra_to_rgba(data)

    # Convert RGBA data to PNG image
    img_path = os.path.join(output_dir, "extracted_data.png")
    img_size = w * h * 4  # 4 bytes per pixel (RGBA)
    img = Image.frombytes("RGBA", (w, h), rgba_data)
    img.save(img_path)
    print(f"Image saved to: {img_path}")

    # Write extracted data to file
    output_path = os.path.join(output_dir, "extracted_data.bin")
    with open(output_path, "wb") as f:
        f.write(data)

    print(f"Data extracted to: {output_dir}")

def import_png(file_path, output_path):
    # Load PNG image as RGBA data
    img = Image.open(file_path)
    rgba_data = img.tobytes()

    # Convert RGBA data to BGRA
    bgra_data = convert_rgba_to_bgra(rgba_data)

    # Write BGRA data to file
    with open(output_path, "wb") as f:
        f.write(bgra_data)

    print(f"PNG image imported and saved to: {output_path}")
