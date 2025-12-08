from PIL import Image
import os

def update_icons():
    source_file = "图标.jpg"
    
    if not os.path.exists(source_file):
        print(f"Error: {source_file} not found.")
        return

    try:
        img = Image.open(source_file)
        
        # 1. Save as icon.png (overwrite existing)
        img.save("icon.png", format="PNG")
        print("Updated icon.png")
        
        # 2. Save as icon.ico (overwrite existing) with multiple sizes
        # ICO sizes: 256, 128, 64, 48, 32, 16
        img.save("icon.ico", format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
        print("Updated icon.ico")
        
    except Exception as e:
        print(f"Failed to update icons: {e}")

if __name__ == "__main__":
    update_icons()
