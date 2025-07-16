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

    # Completed assessments
    completed_results = AssessmentResult.objects.filter(user=user, status='Completed').select_related('assessment')
    completed_ids = [r.assessment.id for r in completed_results]

    # Pending = Assigned but not completed
    pending_assessments = Assessment.objects.filter(id__in=assigned_ids).exclude(id__in=completed_ids)
    completed_assessments = Assessment.objects.filter(id__in=completed_ids).prefetch_related('user_answers')

    # Add retake info to each completed assessment
    completed_assessment_data = []
    for assessment in completed_assessments:
        result = AssessmentResult.objects.filter(user=user, assessment=assessment).first()
        completed_assessment_data.append({
            'assessment': assessment,
            'score': result.score if result else None,
            'allow_retake': assessment.allow_retake,
            'time_limit': assessment.time_limit,
        })

    # Add time_limit and retake info to pending assessments too
    pending_assessment_data = []
    for assessment in pending_assessments:
        pending_assessment_data.append({
            'assessment': assessment,
            'allow_retake': assessment.allow_retake,
            'time_limit': assessment.time_limit,
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