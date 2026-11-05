from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Custom user model, set up now so profile fields (interests, text size,
    privacy choices, trusted contact; see DESIGN.md section 6.4) can be added
    later without a painful migration away from the built-in User."""
