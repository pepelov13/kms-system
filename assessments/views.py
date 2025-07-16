import random
from django.shortcuts import render, redirect, get_object_or_404
from django.forms import inlineformset_factory, formset_factory
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.contrib.auth import get_user_model
from django.contrib import messages
from functools import wraps
from datetime import timedelta

from assessments.models import Assessment, Question, Answer, Assignment
from assessments.forms import AssessmentForm, QuestionForm, AnswerForm, AssignmentForm

from results.models import AssessmentResult, UserAnswer
from results.forms import UserAnswerForm

from django.db import IntegrityError  # just in case for logging/debugging

User = get_user_model()

# --- Inline formsets ---
QuestionFormSet = inlineformset_factory(
    Assessment, Question, form=QuestionForm,
    extra=1, can_delete=True
)

AnswerFormSet = inlineformset_factory(
    Question, Answer, form=AnswerForm,
    extra=2, can_delete=True
)

# --- Restrict functionalities to managers and admins ---
def is_manager_or_admin(user):
    return user.is_superuser or user.groups.filter(name='Manager').exists()

def manager_required(view_func):
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not is_manager_or_admin(request.user):
            return render(request, "access_denied.html", status=403)
        return view_func(request, *args, **kwargs)
    return login_required(wrapped_view)

# --- Assessment creation/editing ---
# STEP 1: Create the assessment
@login_required
@manager_required
def create_assessment(request):
    if request.method == 'POST':
        form = AssessmentForm(request.POST)
        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.created_by = request.user
            assessment.save()
            # Redirect to add first question (step=1)
            return redirect('assessments:add_question', assessment_id=assessment.id, step=1)
    else:
        form = AssessmentForm()
    return render(request, 'assessments/create_assessment.html', {'form': form})


# STEP 2: Add/edit a single question with its answers
@login_required
@manager_required
def add_question(request, assessment_id, step):
    # Fetch the assessment or 404
    assessment = get_object_or_404(Assessment, id=assessment_id)

    # Get all questions for this assessment, ordered by ID
    questions = assessment.questions.order_by('id')
    
    # Since step is 1-based, convert to zero-based index
    question_index = step - 1
    
    # Try to get the question at the step; if it doesn't exist, question = None to create new
    try:
        question = questions[question_index]
    except IndexError:
        question = None

    # Instantiate forms for existing question or new question
    if question:
        question_form = QuestionForm(request.POST or None, instance=question)
        answer_formset = AnswerFormSet(request.POST or None, instance=question, prefix='answers')
    else:
        question_form = QuestionForm(request.POST or None)
        answer_formset = AnswerFormSet(request.POST or None, prefix='answers')

    if request.method == 'POST':
        if question_form.is_valid() and answer_formset.is_valid():
            # Save or update the question, linking it to the assessment
            q = question_form.save(commit=False)
            q.assessment = assessment
            q.save()
            
            # Save related answers with the correct question instance
            answer_formset.instance = q
            answer_formset.save()

            if 'next' in request.POST:
                # Redirect to the next step/question page (step + 1)
                return redirect('assessments:add_question', assessment_id=assessment.id, step=step + 1)
            else:
                # Otherwise, redirect to overview page of this assessment
                return redirect('assessments:assessment_overview', assessment_id=assessment.id)

    # Render the question form and answer formset template
    return render(request, 'assessments/add_question.html', {
        'assessment': assessment,
        'question_form': question_form,
        'answer_formset': answer_formset,
        'is_editing': question is not None,
        'step': step,
    })

#edit the assessment
@login_required
@manager_required
def edit_assessment(request, assessment_id):
    # Example for now: just redirect to overview
    return redirect('assessments:assessment_overview', assessment_id=assessment_id)

# STEP 3: Overview of assessment (list of questions/answers)
@login_required
@manager_required
def assessment_overview(request, assessment_id):
    assessment = get_object_or_404(Assessment, id=assessment_id)
    questions = assessment.questions.prefetch_related('answers').all()

    if request.method == 'POST':
        # Finalize assessment or redirect as needed
        return redirect('assessments:assessment_dashboard')

    return render(request, 'assessments/assessment_overview.html', {
        'assessment': assessment,
        'questions': questions,
    })

# EDIT individual question from overview
def edit_question(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    AnswerFormSet = inlineformset_factory(Question, Answer, form=AnswerForm, extra=0, can_delete=True)

    if request.method == 'POST':
        question_form = QuestionForm(request.POST, instance=question)
        answer_formset = AnswerFormSet(request.POST, instance=question)
        if question_form.is_valid() and answer_formset.is_valid():
            question_form.save()
            answer_formset.save()
            return redirect('assessment_overview', assessment_id=question.assessment.id)
    else:
        question_form = QuestionForm(instance=question)
        answer_formset = AnswerFormSet(instance=question)

    return render(request, 'assessments/edit_question.html', {
        'question_form': question_form,
        'answer_formset': answer_formset,
        'question': question
    })


# DELETE individual question from overview
@login_required
@manager_required
def delete_question(request, assessment_id, question_id):
    question = get_object_or_404(Question, id=question_id, assessment_id=assessment_id)
    question.delete()
    return redirect('assessments:assessment_overview', assessment_id=assessment_id)


@login_required
def take_assessment(request, assessment_id):
    assessment = get_object_or_404(Assessment, pk=assessment_id)
    questions = Question.objects.filter(assessment=assessment).prefetch_related('answers')
    employee_assessment = AssessmentResult.objects.filter(user=request.user, assessment=assessment).first()

    if employee_assessment and employee_assessment.status == 'Completed':
        if not assessment.allow_retake:
            return redirect('results:assessment_complete', assessment_id=assessment.id)
        else:
            employee_assessment.delete()
            UserAnswer.objects.filter(user=request.user, assessment=assessment).delete()
            employee_assessment = None

    if not employee_assessment:
        employee_assessment = AssessmentResult.objects.create(
            user=request.user,
            assessment=assessment,
            status='In Progress',
            start_time=timezone.now()
        )

    # 🕒 Timer logic
    now = timezone.now()
    duration_seconds = assessment.time_limit * 60
    elapsed = (now - employee_assessment.start_time).total_seconds()
    remaining_seconds = max(0, int(duration_seconds - elapsed))

    if remaining_seconds == 0:
        return redirect('results:submit_assessment', result_id=employee_assessment.id)

    if employee_assessment.status == 'Completed':
        return redirect('results:assessment_complete', assessment_id=assessment.id)

    question_forms = []

    if request.method == 'POST':
        all_valid = True
        UserAnswer.objects.filter(user=request.user, assessment=assessment).delete()

        for question in questions:
            prefix = str(question.id)
            if any(key.startswith(f"{prefix}-") for key in request.POST):
                form = UserAnswerForm(request.POST, question=question, prefix=prefix)
                if form.is_valid():
                    selected_answers = form.cleaned_data.get('selected_answers')
                    for answer in selected_answers:
                        UserAnswer.objects.create(
                            user=request.user,
                            assessment=assessment,
                            question=question,
                            selected_answer=answer
                        )
                else:
                    all_valid = False
                question_forms.append((question, form))
            else:
                question_forms.append((question, UserAnswerForm(question=question, prefix=prefix)))

        if all_valid:
            total_questions = assessment.questions.count()
            correct_answers = UserAnswer.objects.filter(
                user=request.user,
                assessment=assessment,
                selected_answer__is_correct=True
            ).values('question').distinct().count()

            score = (correct_answers / total_questions) * 100 if total_questions else 0

            employee_assessment.status = 'Completed'
            employee_assessment.score = round(score, 2)
            employee_assessment.submitted_at = timezone.now()
            employee_assessment.save()

            return redirect('results:assessment_complete', assessment_id=assessment.id)

    else:
        for question in questions:
            form = UserAnswerForm(question=question, prefix=str(question.id))
            question_forms.append((question, form))

    return render(request, 'assessments/take_assessment.html', {
        'assessment': assessment,
        'question_forms': question_forms,
        'remaining_seconds': remaining_seconds
    })



#assessment dashboard
@login_required
@manager_required
def assessment_dashboard(request):
    assessments = Assessment.objects.all()
    return render(request, 'assessments/assessment_dashboard.html', {'assessments': assessments})

@login_required
@manager_required
def assessment_detail(request, assessment_id):
    assessment = get_object_or_404(Assessment, pk=assessment_id)
    return render(request, 'assessments/assessment_detail.html', {'assessment': assessment})

@login_required
@manager_required
def delete_assessment(request, assessment_id):
    assessment = get_object_or_404(Assessment, id=assessment_id)
    if assessment.created_by == request.user:
        assessment.delete()
        return redirect('assessments:assessment_dashboard')
    else:
        return redirect('assessments:assessment_dashboard')  # Or show a "permission denied" page
    


@login_required
def start_assessment(request, assessment_id):
    assessment = get_object_or_404(Assessment, id=assessment_id)

    # 🚫 Restrict access to assigned assessments for employees
    if request.user.is_employee:
        is_assigned = Assignment.objects.filter(
            assessment=assessment,
            employee=request.user
        ).exists()
        if not is_assigned:
            messages.error(request, "You are not assigned to this assessment.")
            return redirect('employee_dashboard')

    result, created = AssessmentResult.objects.get_or_create(assessment=assessment, user=request.user)

    if result.status == 'Completed':
        return redirect('employee_dashboard')

    # ⏱ Start time logic
    if not result.start_time:
        result.start_time = timezone.now()
        result.save()

    duration_minutes = assessment.duration_minutes if assessment.duration_minutes else 15
    end_time = result.start_time + timedelta(minutes=duration_minutes)
    remaining_seconds = max(0, int((end_time - timezone.now()).total_seconds()))

    # 🎲 Randomize question order once per attempt using session
    session_key = f'assessment_{assessment_id}_question_order'
    if session_key not in request.session:
        question_ids = list(assessment.questions.values_list('id', flat=True))
        random.shuffle(question_ids)
        request.session[session_key] = question_ids
        request.session.modified = True
    else:
        question_ids = request.session[session_key]

    total_questions = len(question_ids)
    current_index = int(request.GET.get('q', 0))

    if current_index >= total_questions:
        del request.session[session_key]  # cleanup
        return redirect('results:submit_assessment', assessment_id=assessment.id)

    question_id = question_ids[current_index]
    question = get_object_or_404(Question, id=question_id)
    answers = question.answers.all()

    if request.method == 'POST':
        selected_answer_ids = request.POST.getlist('answers')
        if selected_answer_ids:
            for answer_id in selected_answer_ids:
                selected_answer = get_object_or_404(Answer, id=answer_id)

                # Prevent duplicate answers
                UserAnswer.objects.update_or_create(
                    user=request.user,
                    assessment=assessment,
                    question=question,
                    defaults={'selected_answer': selected_answer}
                )

        result.status = 'In Progress'
        result.save()

        if current_index + 1 < total_questions:
            return redirect(f'{request.path}?q={current_index + 1}')
        else:
            del request.session[session_key]  # final cleanup
            return redirect('results:submit_assessment', assessment_id=assessment.id)

    return render(request, 'assessments/start_assessment.html', {
        'assessment': assessment,
        'question': question,
        'answers': answers,
        'current_index': current_index,
        'total_questions': total_questions,
        'remaining_seconds': remaining_seconds,
    })



@login_required
@manager_required
def assign_assessment(request):
    if request.method == "POST":
        form = AssignmentForm(request.POST)
        if form.is_valid():
            assessment = form.cleaned_data['assessment']
            employees = form.cleaned_data['employees']
            assigned_count = 0
            for employee in employees:
                print(f"Assigning {assessment} to {employee.username}")  # DEBUG
                obj, created = Assignment.objects.get_or_create(
                    assessment=assessment,
                    employee=employee
                )
                print(f"Created: {created}")  # DEBUG
                if created:
                    assigned_count += 1
            messages.success(request, f"Assessment assigned to {assigned_count} employee(s).")
            return redirect('assessments:assign_assessment')
        else:
            print(form.errors)  # DEBUG if invalid
    else:
        form = AssignmentForm()
    return render(request, 'assessments/assign_assessment.html', {'form': form})


@login_required
@manager_required
def manager_results(request):
    # Placeholder logic for now
    return render(request, 'assessments/manager_results.html', {})


def continue_assessment(request, assessment_id):
    """
    Placeholder for continuing an in-progress assessment.
    Currently just redirects to take_assessment.
    """
    return redirect('assessments:take_assessment', assessment_id=assessment_id)