from django.contrib.auth.forms import (PasswordChangeForm, PasswordResetForm,
                                       SetPasswordForm)
from django.contrib.auth.views import (PasswordChangeView,
                                       PasswordResetConfirmView,
                                       PasswordResetView)
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import CreationForm


class SignUp(CreateView):
    form_class = CreationForm
    success_url = reverse_lazy('posts:index')
    template_name = 'users/signup.html'


class ChangePassword(PasswordChangeView):
    form_class = PasswordChangeForm
    success_url = reverse_lazy('users/password_change_done.html')
    template_name = 'users/password_change_form.html'


class PasswordReset(PasswordResetView):
    form_class = PasswordResetForm
    success_url = reverse_lazy('users/password_reset_done.html')
    template_name = 'users/password_reset_form.html'


class PasswordResetConfirm(PasswordResetConfirmView):
    form_class = SetPasswordForm
    success_url = reverse_lazy('users/password_reset_complete.html')
    template_name = 'users/password_reset_confirm.html'
