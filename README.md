
# Invoice Extractor Pro - Android App

## Features
- ✅ Pick multiple invoice images/PDFs at once
- ✅ Offline OCR using Tesseract
- ✅ Automatic Asian Paints invoice parsing
- ✅ Export to CSV
- ✅ Batch process 300+ files
- ✅ Works completely offline

## Installation

### Method 1: Build with Buildozer (Recommended)

1. **Install dependencies:**
   ```bash
   pip install buildozer cython
   ```

2. **Install Android SDK/NDK:**
   ```bash
   buildozer android debug
   ```
   (First run will download SDK automatically)

3. **Build APK:**
   ```bash
   buildozer android debug deploy run
   ```

### Method 2: Using Pydroid 3 (Quick Test)

1. Install **Pydroid 3** from Play Store
2. Install these libraries in Pydroid 3:
   ```
   pip install kivy pillow pytesseract opencv-python-headless PyMuPDF
   ```
3. Copy `main.py` to your phone
4. Run in Pydroid 3

### Method 3: Termux (Advanced)

```bash
pkg update
pkg install python opencv-python tesseract
pip install kivy pillow pytesseract PyMuPDF
python main.py
```

## Tesseract OCR Data

You need to download language data files:

1. Download `eng.traineddata` from:
   https://github.com/tesseract-ocr/tessdata

2. Place in:
   - Android: `/storage/emulated/0/tessdata/`
   - Or modify path in code

## Usage

1. **Pick Files**: Tap "📁 Pick Files" and select invoice images/PDFs
2. **Extract**: Tap "▶️ Extract" to process all files
3. **Review**: Check extracted items in the scrollable list
4. **Save CSV**: Tap "💾 Save CSV" to export
5. **Clear**: Tap "🗑️ Clear" to start fresh

## File Locations

- **Input**: Any folder on your phone (Downloads, Documents, etc.)
- **Output CSV**: `/storage/emulated/0/Download/Invoices_Extracted_YYYYMMDD_HHMMSS.csv`

## Troubleshooting

| Problem | Solution |
|---------|----------|
| OCR not working | Install Tesseract data files |
| App crashes | Check permissions (Storage) |
| PDF not processing | Install PyMuPDF |
| Slow processing | Reduce image resolution |
| Wrong data | Use clearer images, better lighting |

## For 300+ Files

The app processes files sequentially. For best results:
- Use clear, well-lit images
- Ensure text is readable
- Process in batches of 50 if memory issues
- Keep phone plugged in (OCR is CPU intensive)
