""" Generate a password to use in the apikeys """
import secrets
import string


def generate_password(pwlength=32):
    """return a random string password of pwlength"""
    alphabet = string.ascii_letters + string.digits
    password = "".join(secrets.choice(alphabet) for i in range(pwlength))
    return password
