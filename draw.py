from PIL import Image, ImageDraw, ImageFont
import os

def create_text_watermark(text, output_path="wm.png", width=1280, height=150):
    """Create a watermark image with text"""
    try:
        # Create a new image with transparent background
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Try to use the existing font, fallback to default if not found
        try:
            if os.path.exists("font2.otf"):
                font = ImageFont.truetype("font2.otf", 60)
            else:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
            
        # Calculate text size and position to center it
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        # Draw text with semi-transparent white color
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 180))
        
        # Save the image
        image.save(output_path, "PNG")
        return output_path
    except Exception as e:
        print(f"Error creating watermark: {str(e)}")
        return None


# For direct testing (optional)
if __name__ == "__main__":
    create_text_watermark("UG BOTS")
