from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class CleanUserCreationForm(UserCreationForm):

    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Remove ALL help texts
        for field in self.fields.values():
            field.help_text = None