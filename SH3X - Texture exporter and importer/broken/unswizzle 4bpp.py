import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
import struct
import os



# this function works for the following resolutions
# Width:       any multiple of 16 smaller then or equal to 4096
# Height:      any multiple of 4 smaller then or equal to 4096

# the texels must be uploaded as a 32bit texture
# width_32bit = width_8bit / 2
# height_32bit = height_8bit / 2
# remember to adjust the mapping coordinates when
# using a dimension which is not a power of two
def unswizzle8(buf, width, height):
    out = bytearray(width * height)
    for y in range(height):
        for x in range(width):
            block_location = (y & (~0xf)) * width + (x & (~0xf)) * 2
            swap_selector = (((y + 2) >> 2) & 0x1) * 4
            posY = (((y & (~3)) >> 1) + (y & 1)) & 0x7
            column_location = posY * width * 2 + ((x + swap_selector) & 0x7) * 4
            byte_num = ((y >> 1) & 1) + ((x >> 2) & 2)
            swizzleid = block_location + column_location + byte_num
            out[y * width + x] = buf[swizzleid]
    return out


# For 4BPP Type 1
# Porting and modifying the Sparky's code
# https://ps2linux.no-ip.info/playstation2-linux.com/docs/howto/display_docef7c.html?docid=75

# this function works for the following resolutions
# Width:       32, 64, 96, 128, any multiple of 128 smaller then or equal to 4096
# Height:      16, 32, 48, 64, 80, 96, 112, 128, any multiple of 128 smaller then or equal to 4096

# the texels must be uploaded as a 32bit texture
# width_32bit = height_4bit / 2
# height_32bit = width_4bit / 4
# remember to adjust the mapping coordinates when
# using a dimension which is not a power of two
def unswizzle4bpp(pInTexels, width, height):

    pSwizTexels = bytearray(width * height // 2)
    for y in range(height):
        for x in range(width):

            index = y*width+x
            # unswizzle
            pageX = x & (~0x7f)
            pageY = y & (~0x7f)

            pages_horz = (width+127) // 128
            pages_vert = (height+127) // 128

            page_number = (pageY//128)*pages_horz + (pageX//128)

            page32Y = (page_number // pages_vert) * 32
            page32X = (page_number % pages_vert) * 64

            page_location = page32Y * height * 2 + page32X * 4

            locX = x & 0x7f
            locY = y & 0x7f

            block_location = ((locX & (~0x1f)) >> 1) * height + (locY & (~0xf)) * 2
            swap_selector = (((y + 2) >> 2) & 0x1)*4
            posY = (((y & (~3)) >> 1) + (y & 1)) & 0x7

            column_location = posY * height * 2 + ((x+swap_selector) & 0x7)*4

            byte_num = (x >> 3) & 3     # 0,1,2,3
            bits_set = (y >> 1) & 1     # 0,1            (lower/upper 4 bits)
            pos = page_location + block_location + column_location + byte_num
            # get the pen
            if bits_set & 1:
                uPen = (pInTexels[pos] >> 4) & 0xf
                pix = pSwizTexels[index >> 1]
                if index & 1:
                    pSwizTexels[index >> 1] = ((uPen << 4) & 0xf0) | (pix & 0xf)
                else:
                    pSwizTexels[index >> 1] = (pix & 0xf0) | (uPen & 0xf)
            else:
                uPen = pInTexels[pos] & 0xf
                pix = pSwizTexels[index >> 1]
                if index & 1:
                    pSwizTexels[index >> 1] = ((uPen << 4) & 0xf0) | (pix & 0xf)
                else:
                    pSwizTexels[index >> 1] = (pix & 0xf0) | (uPen & 0xf)
    return pSwizTexels


# For 4BPP Type 2
def unswizzle4(buffer, width, height):
    pixels = bytearray(width * height)
    for i in range(width * height // 2):
        index = buffer[i]
        id2 = (index >> 4) & 0xf
        id1 = index & 0xf
        pixels[i * 2] = id1
        pixels[i * 2 + 1] = id2
    newPixels = unswizzle8(pixels, width, height)
    result = bytearray(width * height)
    for i in range(width * height // 2):
        idx1 = newPixels[i * 2 + 0]
        idx2 = newPixels[i * 2 + 1]
        idx = ((idx2 << 4) | idx1) & 0xff
        result[i] = idx
    return result


# Only for 32bpp
def unswizzlePalette(palBuffer):
    newPal = bytearray(1024)
    for p in range(256):
        pos = ((p & 231) + ((p & 8) << 1) + ((p & 16) >> 1))
        newPal[pos * 4: pos * 4 + 4] = palBuffer[p * 4: p * 4 + 4]
    return newPal


# Support 32bpp and 16bpp
def unswizzleCLUT(clutBuffer, bitsPerPiexl):
    bytesPerPixel = bitsPerPiexl // 8
    width = 16
    height = 16
    tileW = 8
    tileH = 2
    tileLineSize = tileW * bytesPerPixel
    numTileW = width // tileW
    numTileH = height // tileH
    newClutBuffer = bytearray(width * height * bytesPerPixel)
    offset = 0
    for y in range(numTileH):
        for x in range(numTileW):
            for ty in range(tileH):
                curHeight = y * tileH + ty
                curWidth = x * tileW
                dstPos = (curHeight * width + curWidth) * bytesPerPixel
                newClutBuffer[dstPos: dstPos + tileLineSize] = clutBuffer[offset: offset + tileLineSize]
                offset += tileLineSize
    return newClutBuffer


# Convert 4bpp indexed to 8bpp indexed
def convert4bppto8bpp(buffer, width, height):
    pixels = bytearray(width * height)
    for i in range(width * height // 2):
        index = buffer[i]
        id2 = (index >> 4) & 0xf
        id1 = index & 0xf
        pixels[i * 2] = id1
        pixels[i * 2 + 1] = id2
    return pixels


# Read PS2 palette 32bit color
def readRGBA32(rawPixel):
    t = bytearray(4)
    t[0] = rawPixel & 0xFF
    t[1] = (rawPixel >> 8) & 0xFF
    t[2] = (rawPixel >> 16) & 0xFF
    t[3] = min(((rawPixel >> 24) & 0xFF) * 2, 255)
    return t
    
    
    
    
    
    
# Function to open a file dialog and read a file
def open_file():
    file_path = filedialog.askopenfilename()
    if file_path:
        with open(file_path, 'rb') as file:
            buffer = file.read()
            width = int(entry_width.get())
            height = int(entry_height.get())
            bpp_option = bpp_var.get()
            
            # Call the appropriate function based on the selection
            if bpp_option == '8bpp':
                output = unswizzle8(buffer, width, height)
            elif bpp_option == '4bpp Type 1':
                output = unswizzle4bpp(buffer, width, height)
            elif bpp_option == '4bpp Type 2':
                output = unswizzle4(buffer, width, height)
            elif bpp_option == 'Convert 4bpp to 8bpp':
                output = convert4bppto8bpp(buffer, width, height)
            else:
                messagebox.showerror("Error", "Invalid BPP option selected.")
                return
            
            save_file(output)

# Function to save a file after processing
def save_file(data):
    file_path = filedialog.asksaveasfilename(defaultextension=".bin")
    if file_path:
        with open(file_path, 'wb') as file:
            file.write(data)
        messagebox.showinfo("Success", "The file was saved successfully!")

# Main GUI class
class SwizzleGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Swizzle Tool GUI')
        
        # BPP Options Dropdown
        tk.Label(self, text="BPP Option:").grid(row=0, column=0)
        global bpp_var
        bpp_var = tk.StringVar(self)
        bpp_var.set('8bpp')  # set the default option
        bpp_options = ['8bpp', '4bpp Type 1', '4bpp Type 2', 'Convert 4bpp to 8bpp']
        bpp_menu = tk.OptionMenu(self, bpp_var, *bpp_options)
        bpp_menu.grid(row=0, column=1)

        # Width Entry
        tk.Label(self, text="Width:").grid(row=1, column=0)
        global entry_width
        entry_width = tk.Entry(self)
        entry_width.grid(row=1, column=1)

        # Height Entry
        tk.Label(self, text="Height:").grid(row=2, column=0)
        global entry_height
        entry_height = tk.Entry(self)
        entry_height.grid(row=2, column=1)

        # Process Button
        process_button = tk.Button(self, text="Unswizzle and Save", command=open_file)
        process_button.grid(row=3, column=0, columnspan=2)

if __name__ == "__main__":
    app = SwizzleGUI()
    app.mainloop()