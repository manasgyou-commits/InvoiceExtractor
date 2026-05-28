
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.progressbar import ProgressBar
from kivy.properties import StringProperty, ListProperty, ObjectProperty
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import platform
from kivy.graphics import Color, Rectangle

import os
import re
import csv
import json
import threading
from datetime import datetime

# OCR imports
try:
    from PIL import Image
    PIL_AVAILABLE = True
except:
    PIL_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except:
    TESSERACT_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except:
    CV2_AVAILABLE = False

# PDF support
try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except:
    PDF2IMAGE_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except:
    PYMUPDF_AVAILABLE = False


class StyledButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0.2, 0.6, 0.9, 1)
        self.color = (1, 1, 1, 1)
        self.font_size = '16sp'
        self.size_hint_y = None
        self.height = 50


class StyledLabel(Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.color = (0.2, 0.2, 0.2, 1)
        self.font_size = '14sp'
        self.text_size = (None, None)
        self.halign = 'left'
        self.valign = 'middle'


class InvoiceItem(BoxLayout):
    def __init__(self, item_data, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = 40
        self.padding = [5, 2]

        # Alternate row colors
        with self.canvas.before:
            Color(0.95, 0.95, 0.95, 1)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_rect, size=self._update_rect)

        # Fields
        fields = ['s_no', 'material_no', 'item_name', 'hsn', 'qty', 'unit', 
                  'price', 'gst', 'gst_rate', 'amount']
        for field in fields:
            lbl = Label(
                text=str(item_data.get(field, '')),
                size_hint_x=None,
                width=80 if field in ['s_no', 'qty', 'price', 'gst', 'amount'] else 150,
                font_size='12sp',
                color=(0.1, 0.1, 0.1, 1)
            )
            self.add_widget(lbl)

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size


class InvoiceExtractorApp(App):
    extracted_items = ListProperty([])
    current_file = StringProperty('')
    status_text = StringProperty('Ready')

    def build(self):
        Window.clearcolor = (0.98, 0.98, 0.98, 1)
        self.title = 'Invoice Extractor Pro'

        # Main layout
        root = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Header
        header = BoxLayout(size_hint_y=None, height=60, spacing=10)
        header.add_widget(Label(
            text='[b]INVOICE EXTRACTOR[/b]',
            markup=True,
            font_size='24sp',
            color=(0.1, 0.4, 0.7, 1),
            size_hint_x=0.7
        ))
        self.status_label = Label(
            text=self.status_text,
            font_size='12sp',
            color=(0.5, 0.5, 0.5, 1),
            size_hint_x=0.3
        )
        header.add_widget(self.status_label)
        root.add_widget(header)

        # Button bar
        btn_bar = GridLayout(cols=4, size_hint_y=None, height=50, spacing=5)

        self.btn_pick = StyledButton(text='📁 Pick Files')
        self.btn_pick.bind(on_press=self.show_file_chooser)
        btn_bar.add_widget(self.btn_pick)

        self.btn_process = StyledButton(text='▶️ Extract', background_color=(0.2, 0.7, 0.3, 1))
        self.btn_process.bind(on_press=self.start_processing)
        btn_bar.add_widget(self.btn_process)

        self.btn_save = StyledButton(text='💾 Save CSV', background_color=(0.9, 0.5, 0.2, 1))
        self.btn_save.bind(on_press=self.save_csv)
        btn_bar.add_widget(self.btn_save)

        self.btn_clear = StyledButton(text='🗑️ Clear', background_color=(0.8, 0.2, 0.2, 1))
        self.btn_clear.bind(on_press=self.clear_all)
        btn_bar.add_widget(self.btn_clear)

        root.add_widget(btn_bar)

        # Progress bar
        self.progress = ProgressBar(max=100, value=0, size_hint_y=None, height=20)
        root.add_widget(self.progress)

        # File list
        self.file_list_label = Label(
            text='No files selected',
            font_size='12sp',
            color=(0.5, 0.5, 0.5, 1),
            size_hint_y=None,
            height=30
        )
        root.add_widget(self.file_list_label)

        # Results header
        results_header = BoxLayout(size_hint_y=None, height=35, spacing=2)
        headers = ['S.No', 'Material', 'Item Name', 'HSN', 'Qty', 'Unit', 'Price', 'GST', 'Rate', 'Amount']
        widths = [50, 100, 200, 80, 50, 60, 80, 80, 60, 90]
        for h, w in zip(headers, widths):
            lbl = Label(
                text=f'[b]{h}[/b]',
                markup=True,
                size_hint_x=None,
                width=w,
                font_size='11sp',
                color=(0.1, 0.3, 0.6, 1)
            )
            results_header.add_widget(lbl)
        root.add_widget(results_header)

        # Scrollable results
        scroll = ScrollView()
        self.results_grid = GridLayout(cols=1, spacing=2, size_hint_y=None)
        self.results_grid.bind(minimum_height=self.results_grid.setter('height'))
        scroll.add_widget(self.results_grid)
        root.add_widget(scroll)

        # Summary bar
        self.summary_label = Label(
            text='Total Items: 0 | Total Amount: ₹0.00',
            font_size='14sp',
            color=(0.2, 0.5, 0.2, 1),
            size_hint_y=None,
            height=40
        )
        root.add_widget(self.summary_label)

        # Bind properties
        self.bind(status_text=self.update_status)

        self.selected_files = []
        self.processed_count = 0

        return root

    def update_status(self, instance, value):
        self.status_label.text = value

    def show_file_chooser(self, instance):
        content = BoxLayout(orientation='vertical')

        # Determine starting path based on platform
        if platform == 'android':
            start_path = '/storage/emulated/0/'
        else:
            start_path = os.path.expanduser('~')

        self.file_chooser = FileChooserListView(
            path=start_path,
            filters=['*.jpg', '*.jpeg', '*.png', '*.pdf', '*.bmp'],
            multiselect=True
        )
        content.add_widget(self.file_chooser)

        btn_box = BoxLayout(size_hint_y=None, height=50, spacing=5)

        select_btn = Button(text='Select', background_color=(0.2, 0.7, 0.3, 1))
        select_btn.bind(on_press=self.on_file_select)
        btn_box.add_widget(select_btn)

        cancel_btn = Button(text='Cancel', background_color=(0.8, 0.2, 0.2, 1))
        cancel_btn.bind(on_press=lambda x: self.popup.dismiss())
        btn_box.add_widget(cancel_btn)

        content.add_widget(btn_box)

        self.popup = Popup(
            title='Select Invoice Files',
            content=content,
            size_hint=(0.9, 0.9)
        )
        self.popup.open()

    def on_file_select(self, instance):
        selection = self.file_chooser.selection
        if selection:
            self.selected_files = selection
            self.file_list_label.text = f'Selected: {len(selection)} files'
            self.status_text = f'{len(selection)} files ready'
        self.popup.dismiss()

    def start_processing(self, instance):
        if not self.selected_files:
            self.show_error('No files selected!')
            return

        if not TESSERACT_AVAILABLE:
            self.show_error('Tesseract OCR not available! Install it first.')
            return

        self.btn_process.disabled = True
        self.progress.value = 0
        self.extracted_items = []
        self.results_grid.clear_widgets()

        # Start processing in background thread
        thread = threading.Thread(target=self.process_files_thread)
        thread.daemon = True
        thread.start()

    def process_files_thread(self):
        total = len(self.selected_files)
        for i, filepath in enumerate(self.selected_files):
            self.current_file = os.path.basename(filepath)

            # Update UI
            Clock.schedule_once(lambda dt, msg=f'Processing {i+1}/{total}: {self.current_file}': 
                self.update_progress(msg, (i/total)*100), 0)

            # Process file
            try:
                items = self.process_single_file(filepath)
                if items:
                    Clock.schedule_once(lambda dt, data=items: self.add_items_to_ui(data), 0)
            except Exception as e:
                print(f"Error processing {filepath}: {e}")

        Clock.schedule_once(lambda dt: self.processing_complete(), 0)

    def update_progress(self, message, value):
        self.status_text = message
        self.progress.value = value

    def process_single_file(self, filepath):
        """Process a single invoice file (image or PDF)"""
        items = []

        # Check if PDF
        if filepath.lower().endswith('.pdf'):
            images = self.pdf_to_images(filepath)
        else:
            images = [filepath]

        for img_path in images:
            # Preprocess image
            processed_path = self.preprocess_image(img_path)

            # OCR
            text = self.extract_text(processed_path)

            # Parse invoice items
            file_items = self.parse_asian_paints_invoice(text)

            # Add source file info
            for item in file_items:
                item['source_file'] = os.path.basename(filepath)

            items.extend(file_items)

            # Cleanup temp file
            if processed_path != img_path and os.path.exists(processed_path):
                os.remove(processed_path)

        return items

    def pdf_to_images(self, pdf_path):
        """Convert PDF to images"""
        images = []
        temp_dir = os.path.join(os.path.dirname(pdf_path), '.temp_pdf')
        os.makedirs(temp_dir, exist_ok=True)

        try:
            if PYMUPDF_AVAILABLE:
                # Use PyMuPDF
                doc = fitz.open(pdf_path)
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
                    img_path = os.path.join(temp_dir, f'page_{page_num}.png')
                    pix.save(img_path)
                    images.append(img_path)
                doc.close()
            elif PDF2IMAGE_AVAILABLE:
                # Use pdf2image
                pages = convert_from_path(pdf_path, dpi=300)
                for i, page in enumerate(pages):
                    img_path = os.path.join(temp_dir, f'page_{i}.png')
                    page.save(img_path, 'PNG')
                    images.append(img_path)
        except Exception as e:
            print(f"PDF conversion error: {e}")

        return images if images else [pdf_path]  # Return original if conversion fails

    def preprocess_image(self, image_path):
        """Preprocess image for better OCR"""
        if not CV2_AVAILABLE:
            return image_path

        try:
            img = cv2.imread(image_path)
            if img is None:
                return image_path

            # Resize if too small
            height, width = img.shape[:2]
            min_height = 1500
            if height < min_height:
                scale = min_height / height
                img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Denoise
            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

            # Adaptive threshold
            _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # Save processed
            temp_path = image_path + '_processed.png'
            cv2.imwrite(temp_path, binary)
            return temp_path

        except Exception as e:
            print(f"Preprocess error: {e}")
            return image_path

    def extract_text(self, image_path):
        """Extract text using Tesseract OCR"""
        try:
            if PIL_AVAILABLE:
                img = Image.open(image_path)
                # Tesseract config for invoices
                custom_config = r'--oem 3 --psm 6'
                text = pytesseract.image_to_string(img, config=custom_config)
                return text
        except Exception as e:
            print(f"OCR error: {e}")
        return ""

    def parse_asian_paints_invoice(self, text):
        """Parse Asian Paints invoice text"""
        items = []
        lines = text.split('\n')

        # Pattern for Asian Paints line items
        # Format: MaterialNo Description HSN Qty Packs Volume Rate Value Disc Taxable Tax Total

        # Multi-line pattern matching
        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Look for material number pattern (00010112210, 00110935210, etc.)
            material_match = re.search(r'(00\d{8,9}[A-Z]?)', line)

            if material_match:
                material_no = material_match.group(1)

                # Extract description (may span multiple lines)
                description = ""
                desc_lines = []
                j = i
                while j < len(lines) and j < i + 5:
                    desc_line = lines[j].strip()
                    if any(x in desc_line for x in ['AP ', 'APCO', 'APEX', 'EMULSION', 'PAINT', 'STNRS', 'GLS', 'MGS']):
                        desc_lines.append(desc_line)
                    j += 1

                description = ' '.join(desc_lines)
                description = re.sub(r'IN:\s*Central GST OP|IN:\s*State GST OP', '', description)
                description = description.strip()

                # Look for numbers in surrounding lines
                combined_text = ' '.join(lines[i:min(i+8, len(lines))])

                # Extract HSN (6 digits)
                hsn_match = re.search(r'\b(320\d{3}|321\d{3})\b', combined_text)
                hsn = hsn_match.group(1) if hsn_match else ""

                # Extract quantity
                qty_match = re.search(r'\b(\d+)\s+(?:CAR|DRM|PCS|LT|ML)\b', combined_text)
                qty = qty_match.group(1) if qty_match else "1"

                # Extract unit
                unit_match = re.search(r'\b\d+\s+(CAR|DRM|PCS|LT|ML)\b', combined_text)
                unit = unit_match.group(1) if unit_match else "CAR"

                # Extract rate
                rate_match = re.search(r'(\d+\.\d{2})\s+(?:9\.00|INR)', combined_text)
                if not rate_match:
                    rate_match = re.search(r'Rate.*?([\d.]+)', combined_text, re.IGNORECASE)
                rate = float(rate_match.group(1)) if rate_match else 0.0

                # Extract value and total
                numbers = re.findall(r'\d+\.\d{2}', combined_text)
                if len(numbers) >= 3:
                    try:
                        value = float(numbers[-3])
                        taxable = float(numbers[-2])
                        total = float(numbers[-1])
                    except:
                        value = taxable = total = 0.0
                else:
                    value = taxable = total = 0.0

                # Calculate GST
                gst = round(total - taxable, 2)
                gst_rate = "18%"

                # Cash discount
                disc_match = re.search(r'(\d+\.\d{2})-', combined_text)
                cash_disc = float(disc_match.group(1)) if disc_match else 0.0

                item = {
                    's_no': len(items) + 1,
                    'material_no': material_no,
                    'item_name': description[:60],  # Truncate for display
                    'hsn': hsn,
                    'qty': qty,
                    'unit': unit,
                    'price': rate,
                    'gst': gst,
                    'gst_rate': gst_rate,
                    'amount': total,
                    'value': value,
                    'taxable': taxable,
                    'cash_disc': cash_disc
                }
                items.append(item)
                i = j  # Skip processed lines
            else:
                i += 1

        return items

    def add_items_to_ui(self, items):
        """Add extracted items to the UI"""
        for item in items:
            self.extracted_items.append(item)
            row = InvoiceItem(item)
            self.results_grid.add_widget(row)

        self.update_summary()

    def update_summary(self):
        """Update summary statistics"""
        total_items = len(self.extracted_items)
        total_amount = sum(item['amount'] for item in self.extracted_items)
        self.summary_label.text = f'Total Items: {total_items} | Total Amount: ₹{total_amount:,.2f}'

    def processing_complete(self):
        """Called when all files are processed"""
        self.btn_process.disabled = False
        self.progress.value = 100
        self.status_text = f'Complete! Extracted {len(self.extracted_items)} items'
        self.update_summary()

    def save_csv(self, instance):
        """Save extracted data to CSV"""
        if not self.extracted_items:
            self.show_error('No data to save!')
            return

        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if platform == 'android':
            save_dir = '/storage/emulated/0/Download'
        else:
            save_dir = os.path.expanduser('~')

        filename = f'Invoices_Extracted_{timestamp}.csv'
        filepath = os.path.join(save_dir, filename)

        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Header
                writer.writerow([
                    'S.No', 'Material No.', 'Item Name', 'HSN/SAC', 'Quantity',
                    'Unit', 'Price/Unit (Rs)', 'GST (Rs)', 'GST Rate', 'Amount (Rs)',
                    'Source File'
                ])
                # Data
                for item in self.extracted_items:
                    writer.writerow([
                        item['s_no'],
                        item['material_no'],
                        item['item_name'],
                        item['hsn'],
                        item['qty'],
                        item['unit'],
                        item['price'],
                        item['gst'],
                        item['gst_rate'],
                        item['amount'],
                        item.get('source_file', '')
                    ])

            self.status_text = f'Saved: {filename}'
            self.show_success(f'CSV saved to:
{filepath}')

        except Exception as e:
            self.show_error(f'Save failed: {str(e)}')

    def clear_all(self, instance):
        """Clear all data"""
        self.extracted_items = []
        self.selected_files = []
        self.results_grid.clear_widgets()
        self.file_list_label.text = 'No files selected'
        self.summary_label.text = 'Total Items: 0 | Total Amount: ₹0.00'
        self.progress.value = 0
        self.status_text = 'Ready'

    def show_error(self, message):
        """Show error popup"""
        popup = Popup(
            title='Error',
            content=Label(text=message, color=(0.8, 0.2, 0.2, 1)),
            size_hint=(0.7, 0.3)
        )
        popup.open()

    def show_success(self, message):
        """Show success popup"""
        popup = Popup(
            title='Success',
            content=Label(text=message, color=(0.2, 0.7, 0.3, 1)),
            size_hint=(0.8, 0.3)
        )
        popup.open()


if __name__ == '__main__':
    InvoiceExtractorApp().run()
