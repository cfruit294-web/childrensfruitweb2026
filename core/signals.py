from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings

from .models import PartnershipRequest


@receiver(post_save, sender=PartnershipRequest)
def notify_admin_on_partnership_request(sender, instance, created, **kwargs):
    if not created:
        return
    admin_email = (
        settings.ADMINS[0][1] if getattr(settings, 'ADMINS', None)
        else getattr(settings, 'DEFAULT_FROM_EMAIL', 'admin@childrensfruit.org')
    )
    send_mail(
        subject=f"[Children's Fruit] Nouvelle demande : {instance.organization_name}",
        message=(
            f"Une nouvelle demande de partenariat a été soumise.\n\n"
            f"Organisation : {instance.organization_name}\n"
            f"Contact      : {instance.contact_name}\n"
            f"Email        : {instance.contact_email}\n\n"
            f"Message :\n{instance.message}\n\n"
            f"Connectez-vous à l'admin pour traiter cette demande."
        ),
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@childrensfruit.org'),
        recipient_list=[admin_email],
        fail_silently=True,
    )
