from django.core.exceptions import ValidationError


def validate_file_size(file):
    # Check if it's a Cloudinary resource (already uploaded)
    if hasattr(file, 'public_id'):
        return

    # For regular file uploads
    max_size_kb = 500
    if hasattr(file, 'size') and file.size > max_size_kb * 1024:
        raise ValidationError(f'Files cannot be larger than {max_size_kb}KB')