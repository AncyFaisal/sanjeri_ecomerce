from django import forms
from django.contrib.auth import get_user_model
from ..models import WalletTransaction,wallet

User = get_user_model()


class WalletPaymentForm(forms.Form):
    use_wallet = forms.BooleanField(required=False, initial=False)
    wallet_amount = forms.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=False,
        min_value=0
    )


class ReturnRequestForm(forms.Form):
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Please specify the reason for return...'
        }),
        max_length=500
    )