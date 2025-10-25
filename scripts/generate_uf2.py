"""
Generate UF2 file from .bin for Adafruit Feather M4 CAN
Makes flashing as easy as drag-and-drop!
"""
Import("env")
import os
import struct

def generate_uf2(source, target, env):
    """Convert .bin to UF2 format for SAMD51"""

    firmware_bin = str(target[0])
    firmware_uf2 = firmware_bin.replace('.bin', '.uf2')

    # SAMD51 UF2 parameters
    FAMILY_ID = 0x55114460  # SAMD51
    START_ADDRESS = 0x4000  # App starts at 16KB (after bootloader)
    PAGE_SIZE = 256

    print(f"Generating UF2 file: {firmware_uf2}")

    try:
        # Read binary file
        with open(firmware_bin, 'rb') as f:
            data = f.read()

        # Calculate number of pages
        num_pages = (len(data) + PAGE_SIZE - 1) // PAGE_SIZE

        # UF2 block structure
        uf2_blocks = []

        for page_num in range(num_pages):
            offset = page_num * PAGE_SIZE
            chunk = data[offset:offset + PAGE_SIZE]

            # Pad to PAGE_SIZE
            if len(chunk) < PAGE_SIZE:
                chunk += b'\x00' * (PAGE_SIZE - len(chunk))

            # UF2 block header
            block = struct.pack('<IIIIIIII',
                0x0A324655,  # Magic start 0
                0x9E5D5157,  # Magic start 1
                0x00002000,  # Flags (family ID present)
                START_ADDRESS + offset,  # Target address
                PAGE_SIZE,   # Payload size
                page_num,    # Block number
                num_pages,   # Total blocks
                FAMILY_ID    # Family ID
            )

            # Add payload
            block += chunk

            # Padding to 476 bytes (512 - 32 header - 4 magic end)
            block += b'\x00' * (476 - len(chunk))

            # Magic end
            block += struct.pack('<I', 0x0AB16F30)

            uf2_blocks.append(block)

        # Write UF2 file
        with open(firmware_uf2, 'wb') as f:
            for block in uf2_blocks:
                f.write(block)

        print(f"[OK] UF2 file generated: {firmware_uf2}")
        print(f"  Total blocks: {num_pages}")
        print(f"  Firmware size: {len(data)} bytes")
        print(f"\nTo flash: Drag {os.path.basename(firmware_uf2)} to FTHRCANBOOT drive")

    except Exception as e:
        print(f"ERROR generating UF2: {e}")

# Add post-build action
env.AddPostAction("$BUILD_DIR/${PROGNAME}.bin", generate_uf2)
