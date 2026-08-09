import os
import resend
from tools.tool_registry import ToolInterface

class EmailTool(ToolInterface):
    name = "email"
    description = "Sends an email with an optional attachment or document content to the user's email address."
    parameters = {
        "subject": "string",
        "body": "string", 
        "recipient": "string (optional, defaults to user)"
    }
    required_permissions = ["network_access", "email_access"]

    async def execute(self, subject: str = "", body: str = "", recipient: str = "", **kwargs) -> dict:
        try:
            api_key = os.environ.get("RESEND_API_KEY")
            if not api_key:
                return {"status": "error", "message": "RESEND_API_KEY environment variable is missing."}
            
            resend.api_key = api_key
            
            # Default to the user's email if none is provided by the agent
            to_email = recipient if recipient else "krishna.gusknp2023@ce.du.ac.in"
            
            params = {
                "from": "Synapse OS <onboarding@resend.dev>",
                "to": [to_email],
                "subject": subject or "Synapse OS Document Delivery",
                "html": f"<p>{body.replace(chr(10), '<br>')}</p>",
            }

            email = resend.Emails.send(params)
            
            return {
                "status": "success", 
                "message": f"Email successfully sent to {to_email}",
                "id": email.get("id") if isinstance(email, dict) else getattr(email, "id", None)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
