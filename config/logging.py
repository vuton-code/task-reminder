import logging
import re

class SensitiveFilter(logging.Filter):
    def filter(self, record):
        message = record.getMessage()
        message = re.sub(r"(/accounts/(?:verify|reset)/|/invitations/)[^\s?\"']+", r"\1[redacted]", message)
        message = re.sub(r"([?&](?:code|state|token|credential)=)[^&\s\"']+", r"\1[redacted]", message)
        record.msg = message
        record.args = ()
        return True
