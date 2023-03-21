def unswizzle_data(data, width, height):
    unswizzled_data = bytearray(len(data))

    for y in range(height):
        for x in range(width):
            block_location = (y & (~0xf)) * width + (x & (~0xf)) * 2
            swap_selector = (((y + 2) >> 2) & 0x1) * 4
            posY = (((y & (~3)) >> 1) + (y & 1)) & 0x7
            column_location = posY * width * 2 + ((x + swap_selector) & 0x7) * 4

            byte_num = ((y >> 1) & 1) + ((x >> 2) & 2)  # 0,1,2,3

            index = block_location + column_location + byte_num

            if 0 <= index < len(data):  # Add this check
                unswizzled_data[(y * width) + x] = data[index]
            else:
                print(f"Invalid index: {index}, data length: {len(data)}")

    return bytes(unswizzled_data)

def apply_palette(data, width, height, palette_data, num_palettes):
    if len(palette_data) % (4 * num_palettes) != 0:
        raise ValueError("Invalid palette data length")

    # Convert palette data from bytes to tuples of RGBA values
    palettes = [
        [
            (palette_data[i * 4 + j * 4 * num_palettes], palette_data[i * 4 + j * 4 * num_palettes + 1],
             palette_data[i * 4 + j * 4 * num_palettes + 2], palette_data[i * 4 + j * 4 * num_palettes + 3])
            for i in range(num_palettes)
        ]
        for j in range(len(palette_data) // (4 * num_palettes))
    ]

    # Apply the palette to the texture data
    rgba_data = bytearray(width * height * 4)
    for y in range(height):
        for x in range(width):
            index = data[y * width + x]
            palette_index = (x // num_palettes) % len(palettes)
            color = palettes[palette_index][index % num_palettes]
            offset = (y * width + x) * 4
            rgba_data[offset:offset + 4] = color

    return bytes(rgba_data)

def unswizzle_and_save(textures, output_dir):
    for texture in textures:
        texture_data = texture["data"]
        width = texture["width"]
        height = texture["height"]
        filename = texture["filename"]
        palette_data = texture["palette_data"]
        num_palettes = texture["num_palettes"]

        # Unswizzle the texture data
        unswizzled_data = unswizzle_data(texture_data, width, height)

        # Apply the palette
        rgba_data = apply_palette(unswizzled_data, width, height, palette_data, num_palettes)

        # Save the RGBA data as a DDS file
        output_path = os.path.join(output_dir, f"output_{filename}.dds")
        image = Image.frombytes("RGBA", (width, height), bytes(rgba_data))
        image.save(output_path, format="DDS")

    print(f"All textures unswizzled, palette applied, and saved to: {output_dir}")




