"""Envoi de l'email de notification via SMTP Gmail (App Password)."""

from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from typing import Any

log = logging.getLogger("revue.email")

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465  # SSL


def _build_body_html(meta: dict[str, Any], archive_url: str | None) -> str:
    """Compose le corps HTML de l'email (top-3 + tableau compteurs + CTA)."""
    date_fr = meta["date_fr"]
    n = meta["n_articles"]
    n_cat = meta["n_categories"]
    reading = meta["reading_time"]
    top = meta["top_articles"]

    # Top-3 block
    top_html_parts: list[str] = []
    for art in top:
        title_fr = art.title_fr or art.title
        teaser = (art.summary_fr.get("implication")
                  or art.summary_fr.get("results")
                  or art.summary_fr.get("context")
                  or "")
        teaser = teaser[:180] + ("..." if len(teaser) > 180 else "")
        stars = "⭐" * art.relevance_score
        top_html_parts.append(
            f"""
            <div style="margin-bottom:14px;padding:12px 14px;background:#f6f8fa;
                        border-left:3px solid #2b7cb8;border-radius:4px;">
              <div style="font-size:14px;font-weight:600;color:#1a1f26;margin-bottom:4px;">
                {stars} {title_fr}
              </div>
              <div style="font-size:13px;color:#4a5864;">{teaser}</div>
            </div>
            """
        )
    top_html = "".join(top_html_parts) if top_html_parts else \
        "<p style='color:#6b7887;font-style:italic;'>Aucun article 3 étoiles aujourd'hui.</p>"

    # Tableau compteurs
    rows = []
    for cat in meta["active_categories"]:
        rows.append(
            f"<tr>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #e1e4e8;'>"
            f"{cat['emoji']} {cat['label']}</td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #e1e4e8;"
            f"text-align:right;font-variant-numeric:tabular-nums;'>"
            f"{meta['counts'][cat['id']]}</td>"
            f"</tr>"
        )
    counts_table = (
        "<table style='border-collapse:collapse;width:100%;font-size:14px;"
        "margin:16px 0;'>"
        "<thead><tr>"
        "<th style='padding:6px 10px;text-align:left;color:#6b7887;"
        "font-size:12px;text-transform:uppercase;letter-spacing:0.05em;'>Rubrique</th>"
        "<th style='padding:6px 10px;text-align:right;color:#6b7887;"
        "font-size:12px;text-transform:uppercase;letter-spacing:0.05em;'>Articles</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )

    cta_html = ""
    if archive_url:
        cta_html = f"""
        <div style="text-align:center;margin:28px 0 20px;">
          <a href="{archive_url}" style="display:inline-block;padding:12px 28px;
             background:#2b7cb8;color:#ffffff;text-decoration:none;
             border-radius:8px;font-weight:600;font-size:15px;">
            Ouvrir la revue complète
          </a>
          <div style="font-size:12px;color:#6b7887;margin-top:8px;">
            (HTML également joint à cet email)
          </div>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0;padding:20px;background:#f0f2f5;
                 font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
      <div style="max-width:600px;margin:0 auto;background:#ffffff;
                  border-radius:10px;padding:28px 32px;
                  box-shadow:0 2px 8px rgba(0,0,0,0.06);">
        <h1 style="margin:0 0 6px;font-size:20px;color:#1a1f26;">
          🔬 Revue MN du {date_fr}
        </h1>
        <p style="margin:0 0 20px;color:#4a5864;font-size:14px;">
          Bonjour, voici la synthèse bibliographique de la journée :
          <strong>{n} articles</strong> répartis en <strong>{n_cat} rubriques</strong>,
          ~<strong>{reading} min</strong> de lecture.
        </p>

        <h2 style="font-size:14px;color:#6b7887;text-transform:uppercase;
                   letter-spacing:0.08em;margin:24px 0 10px;">
          Top articles du jour
        </h2>
        {top_html}

        <h2 style="font-size:14px;color:#6b7887;text-transform:uppercase;
                   letter-spacing:0.08em;margin:24px 0 4px;">
          Répartition par rubrique
        </h2>
        {counts_table}

        {cta_html}

        <p style="font-size:13px;color:#6b7887;margin-top:24px;
                  padding-top:16px;border-top:1px solid #e1e4e8;">
          💡 <em>Pense à parcourir la revue avant demain matin.</em>
        </p>
        <p style="font-size:11px;color:#9aa8b5;margin-top:12px;">
          Généré automatiquement par nuclear-med-review.
        </p>
      </div>
    </body>
    </html>
    """


def send_email(
    meta: dict[str, Any],
    html_path: Path,
    archive_url: str | None = None,
) -> None:
    """Envoie l'email de notification avec le HTML en piece jointe."""
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    recipient = os.environ.get("RECIPIENT_EMAIL")

    if not (smtp_user and smtp_password and recipient):
        raise RuntimeError(
            "SMTP_USER / SMTP_PASSWORD / RECIPIENT_EMAIL doivent etre definis"
        )

    subject = (
        f"🔬 Revue MN du {meta['date_fr']} — "
        f"{meta['n_articles']} articles | {meta['n_categories']} rubriques actives"
    )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = recipient
    msg.set_content(
        f"Revue MN du {meta['date_fr']} - {meta['n_articles']} articles.\n"
        f"Ouvrez le HTML en piece jointe pour consulter la revue."
    )
    msg.add_alternative(
        _build_body_html(meta, archive_url),
        subtype="html",
    )

    # Piece jointe HTML
    with html_path.open("rb") as f:
        data = f.read()
    msg.add_attachment(
        data,
        maintype="text",
        subtype="html",
        filename=html_path.name,
    )

    log.info("Envoi email vers %s (sujet='%s', PJ=%s, %d octets)",
             recipient, subject, html_path.name, len(data))
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx, timeout=60) as smtp:
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(msg)
    log.info("Email envoye avec succes")
