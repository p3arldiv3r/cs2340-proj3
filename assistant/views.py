import logging
from dataclasses import asdict
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods, require_POST
from .forms import QuestionForm
from .rag import answer_question

logger = logging.getLogger(__name__)

@require_http_methods(['GET', 'POST'])
def chat(request):
    initial = {'question': request.GET.get('question', '')[:1000]}
    form = QuestionForm(request.POST if request.method == 'POST' else None, initial=initial)
    answer = None
    question = ''
    if request.method == 'POST' and form.is_valid():
        question = form.cleaned_data['question']
        try:
            answer = answer_question(question, user=request.user)
        except Exception:
            logger.exception('Question answering failed')
            form.add_error(None, 'We could not answer right now. Please try again shortly.')
    return render(request, 'assistant/chat.html', {
        'title': 'Your assistant', 'form': form, 'answer': answer, 'question': question})


@require_POST
def ask(request):
    """The popup and full-page chat share this stateless, CSRF-protected endpoint."""
    form = QuestionForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'error': 'Enter a question between 1 and 1,000 characters.'}, status=400)
    try:
        answer = answer_question(form.cleaned_data['question'], user=request.user)
    except Exception:
        logger.exception('Question answering failed')
        return JsonResponse({'error': 'We could not answer right now. Please try again shortly.'}, status=503)
    return JsonResponse(asdict(answer))
