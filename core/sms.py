import random
import logging

logger = logging.getLogger(__name__)


def generate_otp() -> str:
    return f"{random.randint(0, 999999):06d}"


def send_sms(phone: str, message: str) -> None:
    """
    Backend SMS console pour le développement.
    En production, remplacez le corps par l'appel à votre fournisseur :
      - Africa's Talking : africastalking SDK
      - Twilio           : twilio.rest.Client
      - Orange SMS CI    : API REST Orange
    Le code OTP s'affiche dans le terminal Django (runserver).
    """
    bar = '─' * 52
    print(f"\n{bar}")
    print(f"  [SMS → {phone}]")
    print(f"  {message}")
    print(f"{bar}\n")
    logger.info("SMS envoyé à %s : %s", phone, message)
