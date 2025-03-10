from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, ListAttribute, MapAttribute
from app_config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
from pydantic import BaseModel


class OktaUser(Model):
    """
        defines the table structure in dynamodb.
    """
    class Meta:
        table_name = 'OKta_Users'
        region = 'eu-north-1'
        aws_access_key_id = AWS_ACCESS_KEY_ID
        aws_secret_access_key = AWS_SECRET_ACCESS_KEY

    email = UnicodeAttribute(hash_key=True)
    admin = UnicodeAttribute()
    lastLogin = UnicodeAttribute()
    name = UnicodeAttribute()
    passwordChanged = UnicodeAttribute()
    statusChanged = UnicodeAttribute()
    id = UnicodeAttribute()
    user_events = ListAttribute(of=MapAttribute, default=list)


class ScanRequest(BaseModel):
    s3_link: str
