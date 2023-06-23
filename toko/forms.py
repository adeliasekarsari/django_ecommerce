from django import forms
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget
from .models import Comment

PILIHAN_PEMBAYARAN = (
    ('P', 'Paypal'),
    ('S', 'Stripe'),
)
class SearchForm(forms.Form):
    q = forms.CharField(label = 'Search', max_length=50)

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('name', 'email', 'body')

class CheckoutForm(forms.Form):
    alamat_1 = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Your Address', 'class': 'textinput form-control'}))
    alamat_2 = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Apartement, House, others (opsional)', 'class': 'textinput form-control'}))
    negara = CountryField(blank_label='(Select State)').formfield(widget=CountrySelectWidget(attrs={'class': 'countryselectwidget form-select'}))
    kode_pos = forms.CharField(widget=forms.TextInput(attrs={'class': 'textinput form-outline', 'placeholder': 'Postal Code'}))
    simpan_info_alamat = forms.BooleanField(widget=forms.CheckboxInput(), required=False)
    opsi_pembayaran = forms.ChoiceField(widget=forms.RadioSelect(), choices=PILIHAN_PEMBAYARAN)

class ContactForm(forms.Form):
    name = forms.CharField(label='Name', max_length=100,widget=forms.TextInput(attrs={'placeholder': 'Your Name', 'class': 'textinput form-control'}))
    email = forms.EmailField(label='email', max_length=100,widget=forms.TextInput(attrs={'placeholder': 'email', 'class': 'textinput form-control'}))
    subject = forms.CharField(label='subject', max_length=100,widget=forms.TextInput(attrs={'placeholder': 'Subject', 'class': 'textinput form-control'}))
    message = forms.CharField(label='Message', widget=forms.Textarea(attrs={'placeholder': 'Message', 'class': 'textinput form-control'}))
