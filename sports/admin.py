from django.contrib import admin
from .models import Sport, Registration, Team, TeamRequest, Results

@admin.register(Sport)
class SportAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_team_sport', 'primary_coordinator', 'get_secondary_count')
    list_filter = ('team',)
    search_fields = ('name', 'description')
    filter_horizontal = ('secondary',)

    def is_team_sport(self, obj):
        return obj.isTeamBased
    is_team_sport.short_description = 'Team Sport'
    is_team_sport.boolean = True  # This will display a nice checkmark icon

    def primary_coordinator(self, obj):
        return str(obj.primary)
    primary_coordinator.short_description = 'Primary Coordinator'
    
    def get_secondary_count(self, obj):
        return obj.secondary.count()
    get_secondary_count.short_description = 'Secondary Coordinators'

@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ('student__first_name','student__last_name', 'sport', 'year', 'branch', 'registered_on')
    list_filter = ('year', 'branch', 'sport', 'registered_on')
    search_fields = ('student__username', 'student__email', 'sport__name')
    # date_hierarchy = 'registered_on'
    readonly_fields = ('registered_on', 'registration_modified')

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'sport', 'branch', 'get_members_count')
    list_filter = ('branch', 'sport')
    search_fields = ('name', 'sport__name', 'members__username')
    filter_horizontal = ('members',)

    def get_members_count(self, obj):
        return obj.members.count()
    get_members_count.short_description = 'Team Members'

admin.site.register(TeamRequest)
admin.site.register(Results)