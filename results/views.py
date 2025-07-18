from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.timezone import localtime
from assessments.models import Assessment, Question, Answer, Assignment
from results.models import AssessmentResult, UserAnswer
import csv
from django.http import HttpResponse
from django.http import FileResponse
from datetime import timedelta
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

User = get_user_model()

@login_required
def employee_results(request):
    user = request.user
    results = AssessmentResult.objects.filter(user=user).select_related('assessment')
    return render(request, 'results/employee_results.html', {
        'results': results,
    })


@login_required
def manager_results(request):
    return render(request, 'results/manager_view.html')


@login_required
def view_employee_results(request, employee_id, assessment_id):
    employee = get_object_or_404(User, id=employee_id)
    assessment = get_object_or_404(Assessment, id=assessment_id)
    result = get_object_or_404(AssessmentResult, user=employee, assessment=assessment)
    user_answers = UserAnswer.objects.filter(user=employee, assessment=assessment).select_related('question', 'selected_answer')

    # Correct answer lookup dictionary
    correct_answers_dict = {
        question.id: question.answers.filter(is_correct=True)
        for question in assessment.questions.all()
    }

    correct_answers = 0
    for ua in user_answers:
        ua.correct_answers = correct_answers_dict.get(ua.question.id, [])
        if ua.selected_answer and ua.selected_answer.is_correct:
            correct_answers += 1

    total_answers = user_answers.count()

    return render(request, 'results/view_employee_results.html', {
        'employee': employee,
        'assessment': assessment,
        'result': result,
        'user_answers': user_answers,
        'correct_answers': correct_answers,
        'total_answers': total_answers,
    })


@login_required
def submit_assessment(request, assessment_id):
    assessment = get_object_or_404(Assessment, id=assessment_id)
    result, _ = AssessmentResult.objects.get_or_create(user=request.user, assessment=assessment)

    # Score calculation based on saved answers
    user_answers = UserAnswer.objects.filter(user=request.user, assessment=assessment)
    total_questions = assessment.questions.count()
    correct_answers = sum(1 for ua in user_answers if ua.selected_answer.is_correct)

    score = int((correct_answers / total_questions) * 100) if total_questions > 0 else 0

    result.score = score
    result.status = 'Completed'
    result.submitted_at = timezone.now()
    result.save()

    messages.success(request, f"You scored {score}%")
    return redirect('results:assessment_complete', assessment_id=assessment.id)


@login_required
def assessment_complete(request, assessment_id):
    assessment = get_object_or_404(Assessment, id=assessment_id)
    result = get_object_or_404(AssessmentResult, assessment=assessment, user=request.user)

    user_answers = UserAnswer.objects.filter(user=request.user, assessment=assessment)
    total_questions = assessment.questions.count()
    incorrect_questions = []

    correct_count = 0

    for question in assessment.questions.all():
        correct_answers = set(question.answers.filter(is_correct=True).values_list('id', flat=True))
        selected_ids = set(user_answers.filter(question=question).values_list('selected_answer_id', flat=True))

        if selected_ids == correct_answers:
            correct_count += 1
        else:
            incorrect_questions.append({
                'question': question,
                'selected_answer_ids': list(selected_ids),
            })

    score = (correct_count / total_questions) * 100
    passing_score = assessment.passing_score
    passed = score >= passing_score

    # Time calculations
    time_taken = None
    over_time_limit = False
    if result.start_time and result.submitted_at:
        # Format time_taken as HH:MM:SS
        time_taken_raw = result.submitted_at - result.start_time
        seconds = int(time_taken_raw.total_seconds())
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        time_taken_str = f"{hours}h {minutes}m {seconds}s"

    result.score = score
    result.status = 'Completed'
    result.submitted_at = timezone.now()
    result.save()

    return render(request, 'results/assessment_complete.html', {
        'assessment': assessment,
        'score': round(score, 2),
        'passing_score': passing_score,
        'passed': passed,
        'incorrect_answers': incorrect_questions,
        'result_id': result.id,
        'time_taken': time_taken_str,
        'time_limit': assessment.time_limit,
        'over_time_limit': over_time_limit,
    })


@login_required
def export_results_csv(request):
    if not request.user.is_manager:
        return HttpResponse(status=403)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="assessment_results.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Employee ID', 'Full Name', 'Email', 'Role',
        'Assessment Title', 'Assessment ID',
        'Time Limit (mins)', 'Max Retakes Allowed', 'Attempt Number', 'Retakes Used',
        'Time Started', 'Submitted At', 'Time Taken (hh:mm:ss)', 'Time Left (mins)',
        'Total Score (%)', 'Raw Score', 'Status', 'Passing Score (%)',
        'Number of Questions', 'Number of Correct', 'Number of Incorrect',
        'Feedback', 'Late Submission?', 'Notes/Flags'
    ])

    results = AssessmentResult.objects.select_related('user', 'assessment').all()

    for result in results:
        user = result.user
        assessment = result.assessment

        # Time calculations
        submitted_at = localtime(result.submitted_at) if result.submitted_at else None
        time_started = localtime(result.start_time) if hasattr(result, 'start_time') and result.start_time else None
        time_limit = assessment.time_limit or 0

        time_taken = ''
        time_left = ''
        late_submission = ''
        if time_started and submitted_at:
            delta = submitted_at - time_started
            time_taken = str(delta).split('.')[0]
            time_taken_minutes = delta.total_seconds() // 60
            time_left_minutes = max(time_limit - time_taken_minutes, 0) if time_limit > 0 else ''
            time_left = int(time_left_minutes) if isinstance(time_left_minutes, (int, float)) else ''
            late_submission = 'Yes' if time_limit > 0 and time_taken_minutes > time_limit else 'No'

        # Retake info
        try:
            assignment = Assignment.objects.get(employee=user, assessment=assessment)
            max_retakes = assessment.max_retakes or 0
        except Assignment.DoesNotExist:
            max_retakes = ''

        attempt_number = getattr(result, 'attempt_number', 1)
        retakes_used = attempt_number - 1

        total_questions = getattr(result, 'total_questions', 0)
        correct_answers = getattr(result, 'correct_answers', 0)
        incorrect_answers = total_questions - correct_answers
        raw_score = f"{correct_answers}/{total_questions}"

        writer.writerow([
            user.id,
            user.get_full_name() or user.username,
            user.email,
            'Employee',
            assessment.title,
            assessment.id,
            time_limit,
            max_retakes,
            attempt_number,
            retakes_used,
            time_started.strftime('%Y-%m-%d %H:%M:%S') if time_started else '',
            submitted_at.strftime('%Y-%m-%d %H:%M:%S') if submitted_at else '',
            time_taken,
            time_left,
            result.score,
            raw_score,
            result.status,
            assessment.passing_score,
            total_questions,
            correct_answers,
            incorrect_answers,
            getattr(result, 'feedback', ''),
            late_submission,
            '',  # Notes/flags placeholder
        ])

    return response


@login_required
def generate_certificate_pdf(request, result_id):
    result = get_object_or_404(AssessmentResult, id=result_id, user=request.user)

    if result.status != 'Completed' or (result.score or 0) < result.assessment.passing_score:
        return HttpResponse("Certificate not available. You must complete and pass the assessment.", status=403)

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Certificate design (simple)
    p.setFont("Helvetica-Bold", 28)
    p.drawCentredString(width / 2, height - 100, "Certificate of Achievement")

    p.setFont("Helvetica", 18)
    p.drawCentredString(width / 2, height - 160, f"This is to certify that")

    p.setFont("Helvetica-Bold", 22)
    p.drawCentredString(width / 2, height - 200, request.user.get_full_name() or request.user.username)

    p.setFont("Helvetica", 18)
    p.drawCentredString(width / 2, height - 240, "has successfully completed the assessment")

    p.setFont("Helvetica-Bold", 20)
    p.drawCentredString(width / 2, height - 280, f"{result.assessment.title}")

    p.setFont("Helvetica", 16)
    p.drawCentredString(width / 2, height - 330, f"Score: {result.score}%")
    p.drawCentredString(width / 2, height - 360, f"Date: {result.submitted_at.strftime('%B %d, %Y')}")

    p.setFont("Helvetica-Oblique", 12)
    p.drawCentredString(width / 2, 100, "Generated by KMS System")

    p.showPage()
    p.save()

    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename='certificate.pdf')