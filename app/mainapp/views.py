import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.core.cache import cache
from django.http import FileResponse, JsonResponse
from django.http.response import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView, View

from mainapp import forms as mainapp_forms
from mainapp import models as mainapp_models
from mainapp import tasks as mainapp_tasks

logger = logging.getLogger(__name__)


class MainPageView(TemplateView):
    """Главная страница"""
    template_name = "mainapp/index.html"


class NewsListView(ListView):
    """Список новостей"""
    model = mainapp_models.News
    paginate_by = 5

    def get_queryset(self):
        return super().get_queryset().filter(deleted=False)


class NewsCreateView(PermissionRequiredMixin, CreateView):
    """Представление создания новости"""
    model = mainapp_models.News
    fields = "__all__"
    success_url = reverse_lazy("mainapp:news")
    permission_required = ("mainapp.add_news",)

    def form_valid(self, form):
        logger.info(f"New news created: {form.instance}")
        return super().form_valid(form)

class NewsDetailView(DetailView):
    """Представление новости"""
    model = mainapp_models.News


class NewsUpdateView(PermissionRequiredMixin, UpdateView):
    """Представление редактирования новости"""
    model = mainapp_models.News
    fields = "__all__"
    success_url = reverse_lazy("mainapp:news")
    permission_required = ("mainapp.change_news",)


class NewsDeleteView(PermissionRequiredMixin, DeleteView):
    """Представление удаления новости"""
    model = mainapp_models.News
    success_url = reverse_lazy("mainapp:news")
    permission_required = ("mainapp.delete_news",)


class CoursesListView(TemplateView):
    """Представление списка курсов"""
    template_name = "mainapp/courses_list.html"

    def get_context_data(self, **kwargs):
        context = super(CoursesListView, self).get_context_data(**kwargs)
        context["objects"] = mainapp_models.Courses.objects.all()
        return context


class CoursesDetailView(TemplateView):
    """Представление курса"""
    template_name = "mainapp/courses_detail.html"

    def get_context_data(self, pk=None, **kwargs):
        context = super(CoursesDetailView, self).get_context_data(**kwargs)
        context["course_object"] = get_object_or_404(mainapp_models.Courses, pk=pk)
        context["lessons"] = mainapp_models.Lesson.objects.filter(course=context["course_object"])
        context["teachers"] = mainapp_models.CourseTeachers.objects.filter(course=context["course_object"])
        if not self.request.user.is_anonymous:
            if not mainapp_models.CourseFeedback.objects.filter(
                course=context["course_object"], user=self.request.user
            ).count():
                context["feedback_form"] = mainapp_forms.CourseFeedbackForm(
                    course=context["course_object"], user=self.request.user
                )

        cached_feedback = cache.get(f"feedback_list_{pk}")
        if not cached_feedback:
            context["feedback_list"] = (
                mainapp_models.CourseFeedback.objects.filter(course=context["course_object"])
                .order_by("-created", "-rating")
                .select_related()
            )
            cache.set(f"feedback_list_{pk}", context["feedback_list"], timeout=300)
        else:
            context["feedback_list"] = cached_feedback

        return context


class CourseFeedbackFormProcessView(LoginRequiredMixin, CreateView):
    """Представления отзыва о курсе"""
    model = mainapp_models.CourseFeedback
    form_class = mainapp_forms.CourseFeedbackForm

    def form_valid(self, form):
        self.object = form.save()
        rendered_card = render_to_string("mainapp/includes/feedback_card.html", context={"item": self.object})
        return JsonResponse({"card": rendered_card})


class ContactsPageView(TemplateView):
    """Представление страницы контактов"""
    template_name = "mainapp/contacts.html"

    def get_context_data(self, **kwargs):
        context = super(ContactsPageView, self).get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context["form"] = mainapp_forms.MailFeedbackForm(user=self.request.user)
        return context

    def post(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            cache_lock_flag = cache.get(f"mail_feedback_lock_{self.request.user.pk}")
            if not cache_lock_flag:
                cache.set(
                    f"mail_feedback_lock_{self.request.user.pk}",
                    "lock",
                    timeout=3,
                )
                messages.add_message(self.request, messages.INFO, _("Message sended"))
                pk = self.request.POST.get("user_id")
                model = get_user_model()
                user_message = self.request.POST.get("message")
                mainapp_tasks.send_feedback_mail.delay(user_message)
            else:
                messages.add_message(
                    self.request,
                    messages.WARNING,
                    _("You can send only one message per 3 seconds"),
                )
        return HttpResponseRedirect(reverse_lazy("mainapp:contacts"))


class DocSitePageView(TemplateView):
    """Представление документации по сайту"""
    template_name = "mainapp/doc_site.html"


class LogView(TemplateView):
    """Представление логов"""
    template_name = "mainapp/log_view.html"

    def get_context_data(self, **kwargs):
        context = super(LogView, self).get_context_data(**kwargs)
        log_slice = []
        with open(settings.LOG_FILE, "r") as log_file:
            for i, line in enumerate(log_file):
                if i == 1000000:
                    break
                log_slice.insert(0, line)
            context["log"] = "".join(log_slice)
        return context


class LogDownloadView(UserPassesTestMixin, View):
    """Кнопка скачать логи"""
    def test_func(self):
        return self.request.user.is_superuser

    def get(self, *args, **kwargs):
        return FileResponse(open(settings.LOG_FILE, "rb"))
