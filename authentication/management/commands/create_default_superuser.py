from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os

User = get_user_model()


class Command(BaseCommand):
    help = "Create a default superuser if it does not already exist"

    def handle(self, *args, **options):
        moodle_id = os.getenv("DJANGO_SUPERUSER_MOODLEID")
        email = os.getenv("DJANGO_SUPERUSER_EMAIL")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD")

        if not moodle_id or not password:
            self.stdout.write(
                self.style.WARNING(
                    "Superuser not created. Required environment variables missing."
                )
            )
            return

        if User.objects.filter(moodleID=moodle_id).exists():
            self.stdout.write(
                self.style.SUCCESS("Superuser already exists. Skipping creation.")
            )
            return

        User.objects.create_superuser(
            moodleID=moodle_id,
            email=email,
            password=password
        )

        self.stdout.write(
            self.style.SUCCESS("Superuser created successfully.")
        )
