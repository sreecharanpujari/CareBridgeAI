import io
from pypdf import PdfReader
from PIL import Image

MAX_FILE_SIZE_MB = 10
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}

def validate_uploaded_file(uploaded_file):
    """
    Validates file type and file size.
    Returns: (is_valid: bool, message: str)
    """
    if uploaded_file is None:
        return False, "No file uploaded."
    
    # 1. Check extension
    filename = uploaded_file.name.lower()
    file_ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
    if file_ext not in ALLOWED_EXTENSIONS:
        return False, f"Unsupported file type (.{file_ext}). Please upload a PDF, PNG, JPG, or JPEG."
    
    # 2. Check file size (in MB)
    file_size_mb = uploaded_file.size / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        return False, f"File is too large ({file_size_mb:.1f} MB). Maximum allowed size is {MAX_FILE_SIZE_MB} MB."
    
    return True, f"File valid: {uploaded_file.name} ({file_size_mb:.2f} MB)"

def extract_text_from_pdf(pdf_bytes):
    """
    Extracts embedded text from a PDF file.
    Returns: (text: str, success: bool, message: str)
    """
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        if len(reader.pages) == 0:
            return "", False, "The uploaded PDF is empty."
        
        extracted_pages = []
        for idx, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            if page_text.strip():
                extracted_pages.append(f"--- Page {idx + 1} ---\n{page_text.strip()}")
        
        full_text = "\n\n".join(extracted_pages).strip()
        if not full_text:
            return "", False, "No readable digital text found in this PDF. It may be a scanned image."
        
        return full_text, True, "Successfully extracted text from PDF."
    except Exception as e:
        return "", False, f"Error reading PDF: {str(e)}"

def extract_text_from_image(image_bytes):
    """
    Extracts text from an image using OCR (Tesseract).
    Handles missing OCR engine gracefully.
    Returns: (text: str, success: bool, message: str)
    """
    try:
        import pytesseract
        image = Image.open(io.BytesIO(image_bytes))
        
        try:
            text = pytesseract.image_to_string(image).strip()
            if not text:
                return "", False, "OCR completed, but no text could be recognized in this image."
            return text, True, "Successfully extracted text using OCR."
        except (pytesseract.TesseractNotFoundError, FileNotFoundError):
            return "", False, (
                "Tesseract OCR engine is not installed on this system. "
                "You can still view the image and type or paste the text directly into the editor below."
            )
        except Exception as ocr_err:
            return "", False, f"OCR processing failed: {str(ocr_err)}"
    except Exception as img_err:
        return "", False, f"Invalid or unreadable image file: {str(img_err)}"

