import os
from pathlib import Path

import resend
from jinja2 import Environment, FileSystemLoader

from app.config import RESEND_API_KEY, RESEND_FROM_EMAIL

# Set up Jinja2 template environment
TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))

# Configure Resend API key
resend.api_key = RESEND_API_KEY


class EmailService:
    """Handles sending transactional emails via Resend using Jinja2 HTML templates."""

    @staticmethod
    def render_template(template_name: str, context: dict) -> str:
        """Render a Jinja2 HTML template with the given context.

        Args:
            template_name: Name of the template file (e.g. 'invoice_listed.html').
            context: Dictionary of variables to inject into the template.

        Returns:
            Rendered HTML string.
        """
        template = jinja_env.get_template(template_name)
        return template.render(**context)

    @staticmethod
    async def send_email(to: str, subject: str, html_body: str) -> None:
        """Send an email via the Resend API.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            html_body: Rendered HTML body content.
        """
        # TODO: Implement Resend API call
        # params = {
        #     "from": RESEND_FROM_EMAIL,
        #     "to": [to],
        #     "subject": subject,
        #     "html": html_body,
        # }
        # resend.Emails.send(params)
        pass
