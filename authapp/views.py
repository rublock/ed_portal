from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django.http.response import HttpResponseRedirect
from django.urls import reverse_lazy

from authapp import models


class CustomLoginView(LoginView):
    def form_valid(self, form):
        ret = super().form_valid(form)
        #код для вывода сообщения
        message = _("Login success!<br>Hi, %(username)s") % {
            "username": self.request.user.get_full_name()
            if self.request.user.get_full_name()
            else self.request.user.get_username()
        }
        messages.add_message(self.request, messages.INFO, mark_safe(message))
        return ret

    def form_invalid(self, form):
        #код для вывода сообщения
        for _unused, msg in form.error_messages.items():
            messages.add_message(
                self.request,
                messages.WARNING,
                mark_safe(f"Something goes worng:<br>{msg}"),
            )
        return self.render_to_response(self.get_context_data(form=form))


class CustomLogoutView(LogoutView):
    def dispatch(self, request, *args, **kwargs):
        messages.add_message(self.request, messages.INFO, _("See you later!"))
        return super().dispatch(request, *args, **kwargs)


class RegisterView(TemplateView):
    template_name = "registration/register.html"

    def post(self, request, *args, **kwargs):

        # код оборачивается в try/except чтобы код отработал до конца и если что сообщил об ошибке
        # через фреймоворк сообщений
        try:
            if all(
                (
                    request.POST.get("username"),
                    request.POST.get("email"),
                    request.POST.get("password1"),
                    request.POST.get("password1") == request.POST.get("password2"),
                )
            ):
                #если все ок, создаем нового пользователя
                new_user = models.CustomUser.objects.create(
                    username=request.POST.get("username"),
                    first_name=request.POST.get("first_name"),
                    last_name=request.POST.get("last_name"),
                    age=request.POST.get("age") if request.POST.get("age") else 0,
                    avatar=request.FILES.get("avatar"),
                    email=request.POST.get("email"),
                )
                #пароли забираются ввиде хэшсуммы SHA256
                new_user.set_password(request.POST.get("password1"))
                new_user.save()
                # _ - феймворк сообщений, в зависимости от того какой язык включен
                messages.add_message(request, messages.INFO, _("Registration success!"))
                # reverse_lazy - формируется пусть для перенеправления пользователя сразу из пространства имен
                return HttpResponseRedirect(reverse_lazy("authapp:login"))
        except Exception as exp:
            messages.add_message(
                request,
                messages.WARNING,
                mark_safe(f"Something goes worng:<br>{exp}"),
            )
            return HttpResponseRedirect(reverse_lazy("authapp:register"))