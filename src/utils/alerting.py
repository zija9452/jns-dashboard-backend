"""
Alerting utilities for the Regal POS Backend
Implements alerting mechanisms for critical failures
"""
import logging
import smtplib
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import requests
from dataclasses import dataclass
from enum import Enum
import os
from ..config.settings import settings


class AlertSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(Enum):
    SYSTEM_ERROR = "system_error"
    PERFORMANCE_ISSUE = "performance_issue"
    SECURITY_EVENT = "security_event"
    DATABASE_ERROR = "database_error"
    API_ERROR = "api_error"
    INFRASTRUCTURE = "infrastructure"


@dataclass
class Alert:
    title: str
    message: str
    severity: AlertSeverity
    alert_type: AlertType
    service: str = "regal-pos-backend"
    environment: str = os.getenv("ENVIRONMENT", "production")
    timestamp: datetime = None
    details: Dict[str, Any] = None
    recipients: List[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.details is None:
            self.details = {}
        if self.recipients is None:
            self.recipients = []


class AlertManager:
    """
    Manager class for handling alerting
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        self.smtp_server = os.getenv("SMTP_SERVER")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.alert_email_recipients = os.getenv("ALERT_EMAIL_RECIPIENTS", "").split(",")

    def send_alert(self, alert: Alert):
        """
        Send an alert through all configured channels
        """
        try:
            # Log the alert
            self._log_alert(alert)

            # Send Slack notification if configured
            if self.slack_webhook_url:
                self._send_slack_notification(alert)

            # Send email notification if configured
            if self.smtp_server and self.alert_email_recipients:
                self._send_email_notification(alert)

            # Send to any webhook endpoints
            self._send_webhook_notifications(alert)

            self.logger.info(f"Alert sent successfully: {alert.title}")
        except Exception as e:
            self.logger.error(f"Failed to send alert: {str(e)}")

    def _log_alert(self, alert: Alert):
        """
        Log the alert to the application logs
        """
        log_message = f"ALERT [{alert.severity.value.upper()}] - {alert.title}: {alert.message}"

        extra = {
            'event_type': 'alert',
            'severity': alert.severity.value,
            'alert_type': alert.alert_type.value,
            'service': alert.service,
            'environment': alert.environment,
            'details': alert.details
        }

        if alert.severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]:
            self.logger.error(log_message, extra=extra)
        elif alert.severity == AlertSeverity.MEDIUM:
            self.logger.warning(log_message, extra=extra)
        else:
            self.logger.info(log_message, extra=extra)

    def _send_slack_notification(self, alert: Alert):
        """
        Send alert to Slack using webhook
        """
        try:
            color_map = {
                AlertSeverity.LOW: "#657b83",      # Gray
                AlertSeverity.MEDIUM: "#cb4b16",   # Orange
                AlertSeverity.HIGH: "#dc322f",     # Red
                AlertSeverity.CRITICAL: "#ff0000"  # Bright Red
            }

            slack_message = {
                "attachments": [
                    {
                        "color": color_map.get(alert.severity, "#657b83"),
                        "title": f"{alert.severity.value.upper()} - {alert.title}",
                        "text": alert.message,
                        "fields": [
                            {
                                "title": "Service",
                                "value": alert.service,
                                "short": True
                            },
                            {
                                "title": "Environment",
                                "value": alert.environment,
                                "short": True
                            },
                            {
                                "title": "Type",
                                "value": alert.alert_type.value,
                                "short": True
                            },
                            {
                                "title": "Timestamp",
                                "value": alert.timestamp.isoformat(),
                                "short": True
                            }
                        ],
                        "footer": "Regal POS Backend Alert System",
                        "ts": int(alert.timestamp.timestamp())
                    }
                ]
            }

            if alert.details:
                # Add details as a code block
                details_text = "```json\n" + json.dumps(alert.details, indent=2, default=str) + "\n```"
                slack_message["attachments"][0]["text"] += f"\n\n*Details:*\n{details_text}"

            response = requests.post(
                self.slack_webhook_url,
                json=slack_message,
                headers={"Content-Type": "application/json"},
                timeout=10
            )

            if response.status_code != 200:
                self.logger.error(f"Failed to send Slack notification: {response.status_code} - {response.text}")

        except Exception as e:
            self.logger.error(f"Error sending Slack notification: {str(e)}")

    def _send_email_notification(self, alert: Alert):
        """
        Send alert via email
        """
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = ", ".join(alert.recipients or self.alert_email_recipients)
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.service} - {alert.title}"

            # Create email body
            body = f"""
            <html>
                <body>
                    <h2 style="color: {'red' if alert.severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL] else 'orange'};">
                        {alert.severity.value.upper()} ALERT - {alert.title}
                    </h2>
                    <p><strong>Message:</strong> {alert.message}</p>
                    <p><strong>Service:</strong> {alert.service}</p>
                    <p><strong>Environment:</strong> {alert.environment}</p>
                    <p><strong>Type:</strong> {alert.alert_type.value}</p>
                    <p><strong>Timestamp:</strong> {alert.timestamp.isoformat()}</p>

                    {f'<h3>Details:</h3><pre>{json.dumps(alert.details, indent=2, default=str)}</pre>' if alert.details else ''}
                </body>
            </html>
            """

            msg.attach(MIMEText(body, 'html'))

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

        except Exception as e:
            self.logger.error(f"Error sending email notification: {str(e)}")

    def _send_webhook_notifications(self, alert: Alert):
        """
        Send alert to configured webhook endpoints
        """
        webhook_urls = os.getenv("ALERT_WEBHOOK_URLS", "").split(",")
        for webhook_url in webhook_urls:
            if webhook_url.strip():
                try:
                    payload = {
                        "title": alert.title,
                        "message": alert.message,
                        "severity": alert.severity.value,
                        "type": alert.alert_type.value,
                        "service": alert.service,
                        "environment": alert.environment,
                        "timestamp": alert.timestamp.isoformat(),
                        "details": alert.details
                    }

                    response = requests.post(
                        webhook_url.strip(),
                        json=payload,
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    )

                    if response.status_code != 200:
                        self.logger.error(f"Failed to send webhook notification to {webhook_url}: {response.status_code}")
                except Exception as e:
                    self.logger.error(f"Error sending webhook notification to {webhook_url}: {str(e)}")

    def create_system_error_alert(self, error: Exception, context: str = "") -> Alert:
        """
        Create a system error alert
        """
        return Alert(
            title="System Error",
            message=f"A system error occurred: {str(error)}",
            severity=AlertSeverity.HIGH,
            alert_type=AlertType.SYSTEM_ERROR,
            details={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context,
                "traceback": getattr(error, '__traceback__', None)
            }
        )

    def create_performance_alert(self, metric_name: str, value: float, threshold: float) -> Alert:
        """
        Create a performance alert
        """
        return Alert(
            title=f"Performance Issue: {metric_name}",
            message=f"Metric {metric_name} exceeded threshold: {value} > {threshold}",
            severity=AlertSeverity.MEDIUM,
            alert_type=AlertType.PERFORMANCE_ISSUE,
            details={
                "metric_name": metric_name,
                "current_value": value,
                "threshold": threshold,
                "exceeded_by": value - threshold
            }
        )

    def create_database_error_alert(self, error: Exception) -> Alert:
        """
        Create a database error alert
        """
        return Alert(
            title="Database Error",
            message=f"A database error occurred: {str(error)}",
            severity=AlertSeverity.CRITICAL,
            alert_type=AlertType.DATABASE_ERROR,
            details={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "connection_info": "Database connection failed"
            }
        )

    def create_security_alert(self, event: str, user_id: str = None) -> Alert:
        """
        Create a security alert
        """
        return Alert(
            title="Security Event",
            message=f"Security event detected: {event}",
            severity=AlertSeverity.HIGH,
            alert_type=AlertType.SECURITY_EVENT,
            details={
                "event": event,
                "user_id": user_id
            }
        )


# Global alert manager instance
alert_manager = AlertManager()


def send_critical_alert(title: str, message: str, details: Dict[str, Any] = None):
    """
    Convenience function to send a critical alert
    """
    alert = Alert(
        title=title,
        message=message,
        severity=AlertSeverity.CRITICAL,
        alert_type=AlertType.SYSTEM_ERROR,
        details=details or {}
    )
    alert_manager.send_alert(alert)


def send_error_alert(title: str, message: str, details: Dict[str, Any] = None):
    """
    Convenience function to send an error alert
    """
    alert = Alert(
        title=title,
        message=message,
        severity=AlertSeverity.HIGH,
        alert_type=AlertType.SYSTEM_ERROR,
        details=details or {}
    )
    alert_manager.send_alert(alert)


def send_warning_alert(title: str, message: str, details: Dict[str, Any] = None):
    """
    Convenience function to send a warning alert
    """
    alert = Alert(
        title=title,
        message=message,
        severity=AlertSeverity.MEDIUM,
        alert_type=AlertType.SYSTEM_ERROR,
        details=details or {}
    )
    alert_manager.send_alert(alert)


# Example usage
if __name__ == "__main__":
    # Example of sending different types of alerts
    alert = Alert(
        title="Test Alert",
        message="This is a test alert to verify the alerting system is working",
        severity=AlertSeverity.LOW,
        alert_type=AlertType.SYSTEM_ERROR,
        details={"test_field": "test_value"}
    )

    alert_manager.send_alert(alert)