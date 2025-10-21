from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from networkx import reverse
from .models import Course, Video, Enrollment
from .forms import CustomSignUpForm  # ← Import your custom form

from django.http import StreamingHttpResponse, Http404, FileResponse
from wsgiref.util import FileWrapper
import os
import mimetypes

from django.contrib import messages
from django.db.models import Q, Count
from django.db import models
from .forms import CourseForm, VideoFormSet

@login_required
def dashboard(request):
    """
    Dashboard view showing enrolled and available courses with search
    """
    user = request.user
    search_query = request.GET.get('search', '').strip()
    
    # Get enrolled course IDs
    enrolled_course_ids = Enrollment.objects.filter(user=user).values_list('course_id', flat=True)
    
    # Base querysets
    enrolled_courses = Course.objects.filter(id__in=enrolled_course_ids).annotate(
        video_count=Count('videos')
    )
    available_courses = Course.objects.exclude(id__in=enrolled_course_ids).annotate(
        video_count=Count('videos')
    )
    
    # Apply search filter if query exists
    if search_query:
        search_filter = Q(title__icontains=search_query) | Q(description__icontains=search_query) | Q(instructor__username__icontains=search_query)
        enrolled_courses = enrolled_courses.filter(search_filter)
        available_courses = available_courses.filter(search_filter)
    
    context = {
        'enrolled_courses': enrolled_courses,
        'available_courses': available_courses,
        'search_query': search_query,
    }
    
    return render(request, 'LibraryApp/dashboard.html', context)


@login_required
def enroll_course(request, course_id):
    """
    Enroll user in a course
    """
    course = get_object_or_404(Course, id=course_id)
    
    # Check if already enrolled
    if Enrollment.objects.filter(user=request.user, course=course).exists():
        messages.warning(request, f'You are already enrolled in "{course.title}"')
    else:
        # Create enrollment
        Enrollment.objects.create(user=request.user, course=course)
        messages.success(request, f'Successfully enrolled in "{course.title}"!')
    
    return redirect('dashboard')


@login_required
def watch_video(request, course_id, video_order):
    """
    Displays a specific video from a course.
    """
    course = get_object_or_404(Course, id=course_id)
    
    # Check if the user is enrolled in this course or is the instructor
    is_instructor = course.instructor == request.user
    is_enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()
    
    if not (is_instructor or is_enrolled):
        return redirect('dashboard')

    video = get_object_or_404(Video, course=course, order=video_order)
    videos_in_course = course.videos.all().order_by('order')
    
    # Get previous and next videos
    previous_video = videos_in_course.filter(order__lt=video_order).order_by('-order').first()
    next_video = videos_in_course.filter(order__gt=video_order).order_by('order').first()

    context = {
        'video': video,
        'course': course,
        'videos_in_course': videos_in_course,
        'previous_video': previous_video,
        'next_video': next_video,
    }
    return render(request, 'LibraryApp/watch_video.html', context)

@login_required
def edit_video(request, video_id):
    """
    Edit video details (instructor only)
    """
    video = get_object_or_404(Video, id=video_id)
    
    # Check if user is the course instructor
    if video.course.instructor != request.user:
        messages.error(request, 'You do not have permission to edit this video.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        video.title = request.POST.get('title')
        video.description = request.POST.get('description')
        
        # Update video file if provided
        if request.FILES.get('video_file'):
            video.video_file = request.FILES['video_file']
        
        video.save()
        messages.success(request, f'Video "{video.title}" updated successfully!')
        return redirect('watch_video', course_id=video.course.id, video_order=video.order)
    
    return redirect('watch_video', course_id=video.course.id, video_order=video.order)

@login_required
def delete_video(request, video_id):
    """
    Delete a video (instructor only)
    """
    video = get_object_or_404(Video, id=video_id)
    course = video.course
    
    # Check if user is the course instructor
    if course.instructor != request.user:
        messages.error(request, 'You do not have permission to delete this video.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        video_title = video.title
        video.delete()
        
        # Reorder remaining videos
        remaining_videos = Video.objects.filter(course=course).order_by('order')
        for index, v in enumerate(remaining_videos, start=1):
            v.order = index
            v.save()
        
        messages.success(request, f'Video "{video_title}" deleted successfully!')
        
        # Redirect to first video or dashboard
        first_video = remaining_videos.first()
        if first_video:
            return redirect('watch_video', course_id=course.id, video_order=1)
        else:
            return redirect('dashboard')
    
    return redirect('dashboard')

@login_required
def edit_course(request, course_id):
    """
    Edit course details (instructor only)
    """
    course = get_object_or_404(Course, id=course_id)
    
    # Check if user is the course instructor
    if course.instructor != request.user:
        messages.error(request, 'You do not have permission to edit this course.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, f'Course "{course.title}" updated successfully!')
            return redirect('dashboard')
    else:
        form = CourseForm(instance=course)
    
    context = {
        'form': form,
        'course': course,
        'is_edit': True,
    }
    return render(request, 'courses/edit_course.html', context)


@login_required
def reorder_videos(request, course_id):
    """
    Reorder videos in a course (instructor only)
    """
    course = get_object_or_404(Course, id=course_id)
    
    # Check if user is the course instructor
    if course.instructor != request.user:
        messages.error(request, 'You do not have permission to reorder videos.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        import json
        order = json.loads(request.POST.get('order', '[]'))
        
        for index, video_id in enumerate(order, start=1):
            Video.objects.filter(id=video_id, course=course).update(order=index)
        
        messages.success(request, 'Videos reordered successfully!')
        
        # Redirect back to the first video
        return redirect('watch_video', course_id=course.id, video_order=1)
    
    return redirect('dashboard')

def login_view(request):
    """
    Handles user login.
    """
    # Redirect authenticated users to dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'LibraryApp/login.html', {'form': form})

def signup_view(request):
    """
    Handles user registration.
    """
    # Redirect authenticated users to dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CustomSignUpForm(request.POST)  # ← Use CustomSignUpForm
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = CustomSignUpForm()  # ← Use CustomSignUpForm
    return render(request, 'LibraryApp/signup.html', {'form': form})

@login_required
def logout_view(request):
    """
    Handles user logout.
    """
    logout(request)
    return redirect('login')

@login_required
def serve_video(request, video_id):
    """
    Serve video files from the database with streaming support
    Only allows access if user is enrolled in the course
    """
    # Get the video object from database
    video = get_object_or_404(Video, id=video_id)
    
    # Check if user is enrolled in the course or is the instructor
    is_enrolled = Enrollment.objects.filter(
        user=request.user, 
        course=video.course
    ).exists()
    is_instructor = video.course.instructor == request.user
    
    if not (is_enrolled or is_instructor):
        raise Http404("Video not found or access denied")
    
    # Get the video file path
    video_path = video.video_file.path
    
    # Check if file exists
    if not os.path.exists(video_path):
        raise Http404("Video file not found")
    
    # Get file size
    file_size = os.path.getsize(video_path)
    
    # Determine content type
    content_type, _ = mimetypes.guess_type(video_path)
    content_type = content_type or 'video/mp4'
    
    # Handle range requests for video streaming
    range_header = request.META.get('HTTP_RANGE', '').strip()
    range_match = None
    
    if range_header:
        import re
        range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
    
    if range_match:
        # Partial content request (for video seeking)
        start = int(range_match.group(1))
        end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
        
        # Ensure end doesn't exceed file size
        end = min(end, file_size - 1)
        
        # Open file and seek to start position
        video_file = open(video_path, 'rb')
        video_file.seek(start)
        
        # Read only the requested chunk
        chunk_size = end - start + 1
        
        def file_iterator(file_object, chunk_size_limit):
            remaining = chunk_size_limit
            while remaining > 0:
                chunk = file_object.read(min(8192, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk
            file_object.close()
        
        # Create streaming response with partial content
        response = StreamingHttpResponse(
            file_iterator(video_file, chunk_size),
            status=206,
            content_type=content_type
        )
        
        response['Content-Length'] = str(chunk_size)
        response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
        response['Accept-Ranges'] = 'bytes'
        
    else:
        # Full content request
        response = FileResponse(
            open(video_path, 'rb'),
            content_type=content_type
        )
        response['Content-Length'] = str(file_size)
        response['Accept-Ranges'] = 'bytes'
    
    return response
    """
    Serve video files from the database with streaming support
    """
    # Get the video object from database
    video = get_object_or_404(Video, id=video_id)
    
    # Optional: Add permission check to ensure user has access to this course
    # if not video.course.enrolled_users.filter(id=request.user.id).exists():
    #     raise Http404("Video not found")
    
    # Get the video file path
    video_path = video.video_file.path  # Assumes you have a FileField named 'video_file'
    
    # Check if file exists
    if not os.path.exists(video_path):
        raise Http404("Video file not found")
    
    # Get file size
    file_size = os.path.getsize(video_path)
    
    # Determine content type
    content_type, _ = mimetypes.guess_type(video_path)
    content_type = content_type or 'video/mp4'
    
    # Handle range requests for video streaming
    range_header = request.META.get('HTTP_RANGE', '').strip()
    range_match = None
    
    if range_header:
        import re
        range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
    
    if range_match:
        # Partial content request
        start = int(range_match.group(1))
        end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
        
        # Open file and seek to start position
        video_file = open(video_path, 'rb')
        video_file.seek(start)
        
        # Create streaming response
        response = StreamingHttpResponse(
            FileWrapper(video_file, 8192),
            status=206,
            content_type=content_type
        )
        
        response['Content-Length'] = str(end - start + 1)
        response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
        response['Accept-Ranges'] = 'bytes'
        
    else:
        # Full content request
        response = FileResponse(
            open(video_path, 'rb'),
            content_type=content_type
        )
        response['Content-Length'] = str(file_size)
        response['Accept-Ranges'] = 'bytes'
    
    # Optional: Prevent caching for sensitive content
    # response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    
    return response

@login_required(login_url='login')
def add_course(request):
    step = request.GET.get('step', 'course')  # default: course step

    if request.method == 'POST':
        if 'next' in request.POST:
            # Step 1: Course form submitted
            course_form = CourseForm(request.POST, request.FILES)
            if course_form.is_valid():
                # Save only text fields to session, not files
                course_data = {
                    'title': course_form.cleaned_data['title'],
                    'description': course_form.cleaned_data['description'],
                }
                request.session['course_data'] = course_data
                
                # Save the thumbnail file temporarily if it exists
                if course_form.cleaned_data.get('thumbnail'):
                    # Create a temporary course to store the file
                    temp_course = course_form.save(commit=False)
                    temp_course.instructor = request.user
                    temp_course.save()
                    request.session['temp_course_id'] = temp_course.id
                
                return redirect('/add/?step=videos')
            else:
                step = 'course'

        elif 'save_all' in request.POST:
            # Step 2: Save videos and commit everything
            video_formset = VideoFormSet(request.POST, request.FILES, queryset=Video.objects.none())
            course_data = request.session.get('course_data')
            temp_course_id = request.session.get('temp_course_id')

            if course_data and video_formset.is_valid():
                # Check if we have a temporary course (with thumbnail)
                if temp_course_id:
                    course = Course.objects.get(id=temp_course_id)
                    # Update with any changed data
                    course.title = course_data['title']
                    course.description = course_data['description']
                    course.save()
                else:
                    # Create new course without thumbnail
                    course = Course(**course_data)
                    course.instructor = request.user
                    course.save()

                # Save videos
                videos = video_formset.save(commit=False)
                for i, video in enumerate(videos, start=1):
                    video.course = course
                    video.order = i
                    video.save()
                
                # Clean up session
                del request.session['course_data']
                if 'temp_course_id' in request.session:
                    del request.session['temp_course_id']
                
                messages.success(request, f'Course "{course.title}" created successfully!')
                return redirect('dashboard')
            else:
                step = 'videos'
    else:
        course_form = CourseForm()
        video_formset = VideoFormSet(queryset=Video.objects.none())

    context = {
        'step': step,
        'course_form': CourseForm(),
        'video_formset': VideoFormSet(queryset=Video.objects.none())
    }
    return render(request, 'courses/add_course.html', context)


@login_required
def unenroll_course(request, course_id):
    """
    Unenroll user from a course
    """
    if request.method != 'POST':
        return redirect('/dashboard/')
    
    course = get_object_or_404(Course, id=course_id)
    
    # Check if user is enrolled
    enrollment = Enrollment.objects.filter(user=request.user, course=course).first()
    
    if enrollment:
        enrollment.delete()
        messages.success(request, f'Successfully unenrolled from "{course.title}"')
    else:
        messages.warning(request, f'You are not enrolled in "{course.title}"')
    
    return redirect('/dashboard/')


@login_required
def add_videos_to_course(request, course_id):
    """
    Add more videos to an existing course (instructor only)
    """
    course = get_object_or_404(Course, id=course_id)
    
    # Check if user is the course instructor
    if course.instructor != request.user:
        messages.error(request, 'You do not have permission to add videos to this course.')
        return redirect('watch_video')
    
    if request.method == 'POST':
        video_formset = VideoFormSet(request.POST, request.FILES, queryset=Video.objects.none())
        
        if video_formset.is_valid():
            # Get the highest order number
            max_order = Video.objects.filter(course=course).aggregate(models.Max('order'))['order__max'] or 0
            
            videos = video_formset.save(commit=False)
            
            if len(videos) == 0:
                messages.warning(request, 'No videos were added. Please fill in at least one video form.')
                return redirect('add_videos', course_id=course.id)
            
            for i, video in enumerate(videos, start=max_order + 1):
                video.course = course
                video.order = i
                video.save()
            
            messages.success(request, f'{len(videos)} video(s) added to "{course.title}"!')
            return redirect('dashboard')
        else:
            # Show formset errors
            messages.error(request, 'There were errors in your form. Please check the fields below.')
            print("Formset errors:", video_formset.errors)  # Debug print
            print("Non-form errors:", video_formset.non_form_errors())  # Debug print
    else:
        video_formset = VideoFormSet(queryset=Video.objects.none())
    
    context = {
        'course': course,
        'video_formset': video_formset,
    }
    return render(request, 'courses/add_videos.html', context)