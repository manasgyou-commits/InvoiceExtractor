
# test_extraction.py - Test OCR without full app
import sys
import os

# Add test image path
test_image = sys.argv[1] if len(sys.argv) > 1 else "test_invoice.jpg"

try:
    from PIL import Image
    import pytesseract

    print(f"Testing OCR on: {test_image}")
    img = Image.open(test_image)
    text = pytesseract.image_to_string(img)
    print("\n" + "="*50)
    print("EXTRACTED TEXT:")
    print("="*50)
    print(text)
    print("="*50)

except Exception as e:
    print(f"Error: {e}")
    print("Make sure tesseract is installed:")
    print("  Android: pkg install tesseract")
    print("  Ubuntu: sudo apt install tesseract-ocr")
    print("  Windows: Download from GitHub releases")
