import os
from PIL import Image, ImageDraw

def create_pwa_icon(size: int, output_path: str):
    # Create image with transparent background
    img = Image.new("RGBA", (size, size), (10, 15, 36, 255))
    draw = ImageDraw.Draw(img)

    # Padding
    pad = int(size * 0.1)
    rect_box = [pad, pad, size - pad, size - pad]
    radius = int(size * 0.2)

    # Rounded rectangle background with vibrant gradient-like color
    draw.rounded_rectangle(rect_box, radius=radius, fill=(37, 99, 235, 255), outline=(6, 182, 212, 255), width=int(size * 0.02))

    # Lightning bolt polygon scaled to size
    # Normalized coords from 0 to 1 based on SVG:
    # (0.575, 0.225), (0.325, 0.55), (0.5, 0.55), (0.425, 0.775), (0.675, 0.45), (0.5, 0.45)
    bolt_coords = [
        (int(size * 0.58), int(size * 0.22)),
        (int(size * 0.32), int(size * 0.55)),
        (int(size * 0.50), int(size * 0.55)),
        (int(size * 0.42), int(size * 0.78)),
        (int(size * 0.68), int(size * 0.45)),
        (int(size * 0.50), int(size * 0.45)),
    ]
    draw.polygon(bolt_coords, fill=(255, 255, 255, 255))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG")
    print(f"Generated: {output_path} ({size}x{size})")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    img_dir = os.path.join(base_dir, "static", "images")
    create_pwa_icon(192, os.path.join(img_dir, "icon-192.png"))
    create_pwa_icon(512, os.path.join(img_dir, "icon-512.png"))
