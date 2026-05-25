from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, PartnershipRequest, VolunteerTask, DonationRecord


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="Email",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'votre@email.com'})
    )
    first_name = forms.CharField(
        max_length=50, required=True, label="Prénom",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Prénom'})
    )
    last_name = forms.CharField(
        max_length=50, required=True, label="Nom",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom de famille'})
    )
    role = forms.ChoiceField(
        choices=CustomUser.ROLE_CHOICES,
        initial='visitor',
        label="Rôle",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    country = forms.CharField(
        max_length=100, required=True, label="Pays d'origine",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Ex : Côte d'Ivoire, France, Sénégal…"})
    )
    phone = forms.CharField(
        max_length=20, required=False, label='Téléphone (optionnel)',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+225 07 12 34 56 78'})
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'email', 'country', 'phone', 'role', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        bootstrap_fields = ('username', 'password1', 'password2')
        placeholders = {
            'username': "Nom d'utilisateur",
            'password1': 'Mot de passe',
            'password2': 'Confirmer le mot de passe',
        }
        for name in bootstrap_fields:
            self.fields[name].widget.attrs['class'] = 'form-control'
            if name in placeholders:
                self.fields[name].widget.attrs['placeholder'] = placeholders[name]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.role = self.cleaned_data['role']
        user.country = self.cleaned_data['country']
        user.phone = self.cleaned_data.get('phone', '')
        user.is_approved = False  # toujours False à la création
        if commit:
            user.save()
        return user


class PartnershipRequestForm(forms.ModelForm):
    class Meta:
        model = PartnershipRequest
        fields = ('organization_name', 'contact_name', 'contact_email', 'message')
        widgets = {
            'organization_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': "Nom de l'organisation"
            }),
            'contact_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Votre nom complet'
            }),
            'contact_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'contact@organisation.com'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Décrivez votre intérêt pour un partenariat avec Children\'s Fruit…'
            }),
        }
        labels = {
            'organization_name': "Organisation",
            'contact_name': "Nom du contact",
            'contact_email': "Adresse email",
            'message': "Message",
        }


class DonationForm(forms.ModelForm):
    class Meta:
        model = DonationRecord
        fields = ('name', 'email', 'phone', 'amount', 'payment_method', 'message')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Votre nom complet'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'votre@email.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+225 XX XX XX XX XX'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Montant en FCFA', 'min': '100'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Message optionnel…'}),
        }
        labels = {
            'name': 'Nom complet',
            'email': 'Email (optionnel)',
            'phone': 'Numéro de téléphone',
            'amount': 'Montant du don (FCFA)',
            'payment_method': 'Méthode de paiement',
            'message': 'Message (optionnel)',
        }


class PhoneLoginForm(forms.Form):
    phone = forms.CharField(
        max_length=20, label='Numéro de téléphone',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+225 07 12 34 56 78',
            'inputmode': 'tel',
            'autocomplete': 'tel',
        })
    )


class PhoneCodeForm(forms.Form):
    code = forms.CharField(
        max_length=6, min_length=6, label='Code reçu par SMS',
        widget=forms.TextInput(attrs={
            'class': 'form-control text-center fw-bold',
            'placeholder': '000000',
            'maxlength': '6',
            'inputmode': 'numeric',
            'autocomplete': 'one-time-code',
            'style': 'font-size:1.8rem;letter-spacing:.5rem;',
        })
    )


class VolunteerApplicationForm(forms.Form):
    task = forms.ModelChoiceField(
        queryset=VolunteerTask.objects.filter(status='open'),
        label="Tâche souhaitée",
        empty_label="— Choisissez une tâche —",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    motivation = forms.CharField(
        label="Motivation",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Pourquoi souhaitez-vous contribuer à cette tâche?'
        })
    )
