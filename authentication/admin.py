from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import Student

class StudentAdmin(UserAdmin):
    model = Student
    list_display = ('moodleID', 'username', 'email', 'display_profile_image', 'phone_number',
                   'is_prohibited', 'is_staff', 'is_superuser', 'is_active', 'date_joined')
    list_filter = ('is_prohibited', 'is_active', 'is_staff', 'is_superuser', 'branch')
    search_fields = ('username', 'email', 'phone_number', 'first_name', 'last_name', 'moodleID')
    ordering = ('username',)
    list_per_page = 20

    def display_profile_image(self, obj):
        if obj.profile_image:
            return format_html('<img src="{}" width="50" height="50" style="border-radius: 50%;" />', 
                             obj.profile_image.url)
        return "No image"
    display_profile_image.short_description = 'Profile Image'

    fieldsets = (
        (None, {'fields': ('moodleID', 'username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone_number', 'profile_image')}),
        ('Access Control', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_prohibited', 'is_managing')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Groups', {'fields': ('groups',)}),
        ('User Permissions', {'fields': ('user_permissions',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('moodleID', 'username', 'password1', 'password2', 'email', 'is_staff', 'is_active')}
        ),
    )

    readonly_fields = ('date_joined', 'last_login')
    filter_horizontal = ('groups', 'user_permissions')

admin.site.register(Student, StudentAdmin)