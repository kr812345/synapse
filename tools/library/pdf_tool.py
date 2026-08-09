import os
from fpdf import FPDF
from tools.tool_registry import ToolInterface
import uuid

class PDFTool(ToolInterface):
    name = "pdf_generator"
    description = "Generates a PDF document from provided text content."
    parameters = {
        "title": "string",
        "content": "string",
        "filename": "string (optional)"
    }
    required_permissions = ["file_system_write"]

    async def execute(self, title: str = "Document", content: str = "", filename: str = "", **kwargs) -> dict:
        try:
            pdf = FPDF()
            pdf.add_page()
            
            # Title
            pdf.set_font("helvetica", "B", 16)
            pdf.cell(0, 10, title, ln=True, align='C')
            pdf.ln(10)
            
            # Content
            pdf.set_font("helvetica", "", 12)
            
            # Replace unsupported characters for standard helvetica, or just encode nicely
            # fpdf2 handles unicode well with standard fonts if we use utf-8, but just in case
            clean_content = content.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 10, clean_content)
            
            output_dir = os.path.join(os.getcwd(), "artifacts")
            os.makedirs(output_dir, exist_ok=True)
            
            if not filename:
                filename = f"document_{uuid.uuid4().hex[:8]}.pdf"
            if not filename.endswith(".pdf"):
                filename += ".pdf"
                
            file_path = os.path.join(output_dir, filename)
            pdf.output(file_path)
            
            return {
                "status": "success", 
                "message": f"PDF successfully generated.",
                "file_path": file_path
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
