"""Promote (or demote) a user's is_staff flag by email."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()


class Command(BaseCommand):
    help = "Toggle a user's is_staff flag by email. Use --demote to revoke."

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument("--demote", action="store_true", help="Set is_staff=False instead of True")

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        target = not options["demote"]
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist as e:
            raise CommandError(f"No user found with email {email}") from e

        if user.is_staff == target:
            self.stdout.write(self.style.WARNING(f"{user.email} already has is_staff={target}"))
            return

        user.is_staff = target
        user.save(update_fields=["is_staff"])
        verb = "promoted" if target else "demoted"
        self.stdout.write(self.style.SUCCESS(f"{verb} {user.email} (is_staff={target})"))
