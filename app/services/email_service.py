import asyncio
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import settings


def _build_message(
    to_email: str,
    original_filename: str,
    output_path: str,
    warnings: list[str],
) -> MIMEMultipart:
    """Build a MIME multipart email with the formatted document attached."""
    msg = MIMEMultipart()
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg["Subject"] = "Your formatted manuscript is ready"

    body_lines = [
        f"Your manuscript \"{original_filename}\" has been formatted and is attached to this email.",
    ]
    if warnings:
        body_lines.append("")
        body_lines.append("The following warnings were generated during formatting:")
        for warning in warnings:
            body_lines.append(f"  - {warning}")

    msg.attach(MIMEText("\n".join(body_lines), "plain"))

    basename = os.path.basename(output_path)
    with open(output_path, "rb") as f:
        attachment = MIMEApplication(f.read(), Name=basename)
    attachment["Content-Disposition"] = f'attachment; filename="{basename}"'
    msg.attach(attachment)

    return msg


def _send_smtp(msg: MIMEMultipart, to_email: str) -> None:
    """Send the message via SMTP with STARTTLS."""
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.smtp_from, to_email, msg.as_string())


async def send_formatted_document(
    to_email: str,
    original_filename: str,
    output_path: str,
    warnings: list[str],
) -> None:
    """Send an email with the formatted document as an attachment.

    The email includes the original filename and any formatting warnings.
    SMTP operations are run in an executor to avoid blocking the event loop.
    Raises HTTPException(500) on any failure.
    """
    msg = _build_message(to_email, original_filename, output_path, warnings)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _send_smtp, msg, to_email)
