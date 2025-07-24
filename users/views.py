from django.contrib.auth.views import LoginView
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model

from assessments.models import Assessment, Assignment
from results.models import AssessmentResult
from assessments.forms import AssessmentForm

User = get_user_model()


class RoleBasedLoginView(LoginView):
    template_name = 'registration/login.html'

    def get_success_url(self):
        user = self.request.user

        if user.is_superuser:
            return reverse('admin:index')  # Django admin dashboard

        if user.groups.filter(name='Manager').exists():
            return reverse('manager_dashboard')

        if user.groups.filter(name='Employee').exists():
            return reverse('employee_dashboard')

        return reverse('employee_dashboard')  # Safe fallback


@login_required
def employee_dashboard(request):
    user = request.user

    # Assigned assessments
    assigned_assessments = Assignment.objects.filter(employee=user).select_related('assessment')
    assigned_ids = [a.assessment.id for a in assigned_assessments]

    # ✅ Fetch all results (not just Completed), to count all attempts
    all_results = AssessmentResult.objects.filter(user=user, assessment__id__in=assigned_ids)

    # ✅ Determine which assessments have at least one completed attempt
    completed_ids = all_results.filter(status='Completed').values_list('assessment_id', flat=True).distinct()
    pending_assessments = Assessment.objects.filter(id__in=assigned_ids).exclude(id__in=completed_ids)
    completed_assessments = Assessment.objects.filter(id__in=completed_ids)

    # ✅ Group all results by assessment for reuse
    results_by_assessment = {}
    for result in all_results:
        results_by_assessment.setdefault(result.assessment_id, []).append(result)

    # Build completed assessment data
    completed_assessment_data = []
    for assessment in completed_assessments:
        all_attempts = AssessmentResult.objects.filter(user=user, assessment=assessment, status='Completed')
    
        # ✅ Use latest attempt
        latest_result = all_attempts.order_by('-submitted_at').first()

        # ✅ Use retake_count from model (fix)
        retake_count = latest_result.retake_count if latest_result else 0

        allow_retake = False
        if assessment.allow_retake:
            if assessment.max_retakes is None or retake_count < assessment.max_retakes:
                allow_retake = True

        completed_assessment_data.append({
            'assessment': assessment,
            'score': latest_result.score if latest_result else None,
            'allow_retake': allow_retake,
            'retake_count': retake_count,
            'max_retakes': assessment.max_retakes,
            'time_limit': assessment.time_limit,
        })


    # Build pending assessment data
    pending_assessment_data = []
    for assessment in pending_assessments:
        pending_assessment_data.append({
            'assessment': assessment,
            'allow_retake': assessment.allow_retake,
            'time_limit': assessment.time_limit,
            'retake_count': 0,
            'max_retakes': assessment.max_retakes,
        })

    return render(request, 'users/employee_dashboard.html', {
        'pending_assessments': pending_assessment_data,
        'completed_assessments': completed_assessment_data,
    })





@login_required
def manager_dashboard(request):
    try:
        employee_group = Group.objects.get(name='Employees')
    except Group.DoesNotExist:
        employee_group = None

    employees = User.objects.filter(groups=employee_group) if employee_group else User.objects.none()
    results = AssessmentResult.objects.select_related('assessment', 'user').filter(user__in=employees)

    # Group results by employee
    employee_results = {}
    for result in results:
        employee_results.setdefault(result.user, []).append(result)

    if request.method == 'POST':
        form = AssessmentForm(request.POST)
        selected_employee_ids = request.POST.getlist('assigned_to')
        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.created_by = request.user
            assessment.save()

            for emp_id in selected_employee_ids:
                try:
                    user = User.objects.get(id=emp_id)
                    Assignment.objects.get_or_create(assessment=assessment, employee=user)
                except User.DoesNotExist:
                    continue

            return redirect('manager_dashboard')
    else:
        form = AssessmentForm()

    # ✅ Updated template path
    return render(request, 'users/manager_dashboard.html', {
        'employees': employees,
        'employee_results': employee_results,
        'form': form,
    })