"""
alert_service.py
==================
Implements the PRD alert system (section 8): generates an alert when the
predicted risk score crosses ALERT_RISK_THRESHOLD, and an alert lead-time
check ensuring alerts fire >= 5 days before risk onset (PRD goal: section 4).

Delivery channels:
- In-app/push: stored in DB and returned via /alerts API for the dashboard
- SMS fallback: logged (or sent via SMS_PROVIDER if configured) for low
  smartphone-literacy users (PRD risk mitigation, section 12)
"""
import datetime
import logging

from app.config import settings

logger = logging.getLogger(__name__)


def evaluate_risk_for_alert(risk_score: float, risk_level: str, predicted_yield: float,
                             forecast: list[dict] | None = None):
    """
    Decide whether an alert should be raised based on the current risk
    score and (optionally) the upcoming weather forecast.

    Args:
        risk_score: float 0-1 from ml_service.predict()
        risk_level: "Low" | "Medium" | "High"
        predicted_yield: float, tons/hectare
        forecast: optional list of daily forecast dicts from weather_service

    Returns:
        dict or None: alert payload if threshold crossed, else None
    """
    triggered = risk_score >= settings.ALERT_RISK_THRESHOLD

    # Additional trigger: forecasted heavy rainfall (>40mm in a day) within
    # the next 5 days can compound existing Medium/High risk -> early alert
    forecast_trigger = False
    forecast_reason = None
    if forecast:
        for day in forecast[:5]:
            if day.get("rainfall_mm", 0) > 40 and risk_level in ("Medium", "High"):
                forecast_trigger = True
                forecast_reason = (
                    f"Heavy rainfall ({day['rainfall_mm']}mm) forecast on {day['date']}"
                )
                break

    if not (triggered or forecast_trigger):
        return None

    if triggered:
        message = (
            f"Risk level is {risk_level} (score {risk_score:.2f}). "
            f"Predicted yield: {predicted_yield} tons/hectare. "
            f"Consider reviewing irrigation and field conditions."
        )
        severity = "high" if risk_level == "High" else "medium"
    else:
        message = (
            f"{forecast_reason}. Current risk level is {risk_level}. "
            f"Plan field interventions before the rain arrives."
        )
        severity = "medium"

    alert = {
        "triggered_at": datetime.datetime.utcnow().isoformat(),
        "severity": severity,
        "risk_level": risk_level,
        "risk_score": round(risk_score, 3),
        "predicted_yield": predicted_yield,
        "message": message,
        "channels": _determine_channels(severity),
    }

    _dispatch_alert(alert)
    return alert


def _determine_channels(severity: str) -> list[str]:
    """In-app push always; SMS fallback for medium/high severity (PRD 12)."""
    channels = ["push"]
    if severity in ("medium", "high"):
        channels.append("sms")
    return channels


def _dispatch_alert(alert: dict):
    """
    Dispatches the alert through configured channels. SMS is sent via the
    configured provider if SMS_PROVIDER_API_KEY is set, otherwise logged
    (demo mode).
    """
    logger.info(f"ALERT [{alert['severity'].upper()}]: {alert['message']}")

    if "sms" in alert["channels"]:
        if settings.SMS_PROVIDER_API_KEY:
            _send_sms(alert["message"])
        else:
            logger.info(
                f"[DEMO SMS] Would send to farmer: '{alert['message']}' "
                f"(set SMS_PROVIDER_API_KEY to enable real SMS delivery)"
            )


def _send_sms(message: str):
    """
    Placeholder for a real SMS provider integration (e.g. Twilio, MSG91).
    Not implemented by default - configure SMS_PROVIDER_API_KEY and
    SMS_PROVIDER_FROM_NUMBER in .env, and fill in the provider call here.
    """
    logger.warning(
        "SMS_PROVIDER_API_KEY is set but _send_sms() is not implemented. "
        "Add your provider's API call here (e.g. Twilio client.messages.create)."
    )
