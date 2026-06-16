import random
import string

def generate_random_code(prefix, length=6):
    """
    Generates a code with standard random alphanumeric format.
    E.g. WH-A3B9CD
    """
    chars = string.ascii_uppercase + string.digits
    rand_part = ''.join(random.choices(chars, k=length))
    return f"{prefix}-{rand_part}"
