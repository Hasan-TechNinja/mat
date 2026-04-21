from django.core.management.base import BaseCommand
from django.utils import timezone
from authentication.models import AccountDeletionRequest
from django.db import transaction

class Command(BaseCommand):
    help = 'Processes pending account deletion requests and deletes users after the 30-day grace period.'

    def handle(self, *args, **options):
        now = timezone.now()
        pending_requests = AccountDeletionRequest.objects.filter(
            status='pending',
            scheduled_deletion_date__lte=now
        )

        count = pending_requests.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No pending deletion requests to process.'))
            return

        self.stdout.write(f'Found {count} pending deletion requests to process.')

        for request in pending_requests:
            user = request.user
            email = user.email
            
            try:
                with transaction.atomic():
                    # Update status first (though user delete will cascade if not handled, 
                    # but it's good for logging/completeness if we had soft delete)
                    request.status = 'completed'
                    request.save()
                    
                    # Log the deletion
                    self.stdout.write(f'Deleting user: {email} (ID: {user.id})')
                    
                    # Delete the user. This will cascade to Profile and AccountDeletionRequest 
                    # because they are OneToOneField(User, on_delete=models.CASCADE)
                    user.delete()
                    
                self.stdout.write(self.style.SUCCESS(f'Successfully deleted user {email}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error deleting user {email}: {str(e)}'))

        self.stdout.write(self.style.SUCCESS(f'Finished processing {count} deletion requests.'))
