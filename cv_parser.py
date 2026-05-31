import pdfplumber
import io


def extract_cv_text(uploaded_file) -> str:
    """Extract text from uploaded PDF file."""
    try:
        file_bytes = uploaded_file.read()
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages_text = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)
            full_text = "\n".join(pages_text)

        if not full_text.strip():
            raise ValueError("No text could be extracted from the PDF.")

        return full_text

    except Exception as e:
        raise RuntimeError(f"Failed to parse CV: {str(e)}")
