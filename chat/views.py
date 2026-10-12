from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .forms import AskForm
from .gateway import GatewayError, ask, list_models


@require_http_methods(["GET", "POST"])
def index(request):
    answer, error = None, None
    try:
        models = list_models()
    except GatewayError as exc:
        models, error = [], str(exc)
    form = AskForm(request.POST if request.method == "POST" else None, model_names=models)
    if request.method == "POST" and not error and form.is_valid():
        try:
            answer = ask(form.cleaned_data["model"], form.cleaned_data["question"])
        except GatewayError as exc:
            error = str(exc)
    return render(request, "chat/index.html", {"form": form, "answer": answer, "error": error})
